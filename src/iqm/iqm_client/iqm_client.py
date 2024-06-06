# Copyright 2021-2024 IQM client developers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
r"""
Client for connecting to the IQM quantum computer server interface.
"""

from __future__ import annotations

from datetime import datetime
from importlib.metadata import version
import json
import os
import platform
from posixpath import join
import time
from typing import Any, Callable, Optional
from uuid import UUID
import warnings

import requests

from iqm.iqm_client.authentication import TokenManager
from iqm.iqm_client.errors import (
    APITimeoutError,
    CircuitExecutionError,
    CircuitValidationError,
    ClientAuthenticationError,
    ClientConfigurationError,
    JobAbortionError,
)
from iqm.iqm_client.models import (
    SUPPORTED_INSTRUCTIONS,
    CircuitBatch,
    HeraldingMode,
    Instruction,
    QuantumArchitecture,
    QuantumArchitectureSpecification,
    RunRequest,
    RunResult,
    RunStatus,
    Status,
    serialize_qubit_mapping,
    validate_circuit,
)

REQUESTS_TIMEOUT = float(os.environ.get('IQM_CLIENT_REQUESTS_TIMEOUT', 60.0))
DEFAULT_TIMEOUT_SECONDS = 900
SECONDS_BETWEEN_CALLS = float(os.environ.get('IQM_CLIENT_SECONDS_BETWEEN_CALLS', 1.0))


class IQMClient:
    """Provides access to IQM quantum computers.

    Args:
        url: Endpoint for accessing the server. Has to start with http or https.
        client_signature: String that IQMClient adds to User-Agent header of requests
            it sends to the server. The signature is appended to IQMClients own version
            information and is intended to carry additional version information,
            for example the version information of the caller.
        token: Long-lived IQM token in plain text format.
            If ``token`` is given no other user authentication parameters should be given.
        tokens_file: Path to a tokens file used for authentication.
            If ``tokens_file`` is given no other user authentication parameters should be given.
        auth_server_url: Base URL of the authentication server.
            If ``auth_server_url`` is given also ``username`` and ``password`` must be given.
        username: Username to log in to authentication server.
        password: Password to log in to authentication server.

    Alternatively, the user authentication related keyword arguments can also be given in
    environment variables ``IQM_TOKEN``, ``IQM_TOKENS_FILE``, ``IQM_AUTH_SERVER``,
    ``IQM_AUTH_USERNAME`` and ``IQM_AUTH_PASSWORD``. All parameters must be given either
    as keyword arguments or as environment variables. Same combination restrictions apply
    for values given as environment variables as for keyword arguments.
    """

    def __init__(
        self,
        url: str,
        *,
        client_signature: Optional[str] = None,
        token: Optional[str] = None,
        tokens_file: Optional[str] = None,
        auth_server_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        if not url.startswith(('http:', 'https:')):
            raise ClientConfigurationError(f'The URL schema has to be http or https. Incorrect schema in URL: {url}')
        self._token_manager: Optional[TokenManager] = TokenManager(
            token,
            tokens_file,
            auth_server_url,
            username,
            password,
        )
        self._base_url = url
        self._signature = f'{platform.platform(terse=True)}'
        self._signature += f', python {platform.python_version()}'
        self._signature += f', iqm-client {version("iqm-client")}'
        if client_signature:
            self._signature += f', {client_signature}'
        self._architecture: QuantumArchitectureSpecification | None = None

    def __del__(self):
        try:
            # try our best to close the auth session, doesn't matter if it fails,
            self.close_auth_session()
        except Exception:  # pylint: disable=broad-except
            pass

    def _retry_request_on_error(self, request: Callable[[], requests.Response]) -> requests.Response:
        """This is a temporary workaround for 502 errors.
        The current implementation of the server side can run out of network connections
        and silently drop incoming connections making IQM Client to fail with 502 errors."""

        while True:
            result = request()
            if result.status_code == 502:
                time.sleep(SECONDS_BETWEEN_CALLS)
                continue
            break

        return result

    # pylint: disable=too-many-locals
    def submit_circuits(
        self,
        circuits: CircuitBatch,
        *,
        qubit_mapping: Optional[dict[str, str]] = None,
        custom_settings: Optional[dict[str, Any]] = None,
        calibration_set_id: Optional[UUID] = None,
        shots: int = 1,
        max_circuit_duration_over_t2: Optional[float] = None,
        heralding_mode: HeraldingMode = HeraldingMode.NONE,
    ) -> UUID:
        """Submits a batch of quantum circuits for execution on a quantum computer.

        Args:
            circuits: list of circuits to be executed
            qubit_mapping: Mapping of logical qubit names to physical qubit names.
                Can be set to ``None`` if all ``circuits`` already use physical qubit names.
                Note that the ``qubit_mapping`` is used for all ``circuits``.
            custom_settings: Custom settings to override default settings and calibration data.
                Note: This field should always be ``None`` in normal use.
            calibration_set_id: ID of the calibration set to use, or ``None`` to use the latest one
            shots: number of times ``circuits`` are executed, value must be greater than zero
            max_circuit_duration_over_t2: Circuits are disqualified on the server if they are longer than this ratio
                of the T2 time of the qubits. Setting this value to ``0.0`` turns off circuit duration checking.
                The default value ``None`` instructs server to use server's default value in the checking.
            heralding_mode: Heralding mode to use during the execution.

        Returns:
            ID for the created job. This ID is needed to query the job status and the execution results.
        """

        if shots < 1:
            raise ValueError('Number of shots must be greater than zero.')

        for i, circuit in enumerate(circuits):
            try:
                validate_circuit(circuit)
            except ValueError as e:
                raise CircuitValidationError(f'The circuit at index {i} failed the validation').with_traceback(
                    e.__traceback__
                )

        architecture = self.get_quantum_architecture()

        self._validate_qubit_mapping(architecture, circuits, qubit_mapping)
        serialized_qubit_mapping = serialize_qubit_mapping(qubit_mapping) if qubit_mapping else None

        self._validate_circuit_instructions(architecture, circuits, qubit_mapping)

        data = RunRequest(
            qubit_mapping=serialized_qubit_mapping,
            circuits=circuits,
            custom_settings=custom_settings,
            calibration_set_id=calibration_set_id,
            shots=shots,
            max_circuit_duration_over_t2=max_circuit_duration_over_t2,
            heralding_mode=heralding_mode,
        )

        headers = {'Expect': '100-Continue', **self._default_headers()}

        try:
            # check if someone is trying to profile us with OpenTelemetry
            # pylint: disable=import-outside-toplevel
            # pylint: disable=import-error
            from opentelemetry import propagate

            propagate.inject(headers)
        except ImportError as _:
            # no OpenTelemetry, no problem
            pass

        result = self._retry_request_on_error(
            lambda: requests.post(
                join(self._base_url, 'jobs'),
                json=json.loads(data.model_dump_json(exclude_none=True)),
                headers=headers,
                timeout=REQUESTS_TIMEOUT,
            )
        )

        if result.status_code == 401:
            raise ClientAuthenticationError(f'Authentication failed: {result.text}')

        if 400 <= result.status_code < 500:
            raise ClientConfigurationError(f'Client configuration error: {result.text}')

        result.raise_for_status()

        try:
            job_id = UUID(result.json()['id'])
            return job_id
        except (json.decoder.JSONDecodeError, KeyError) as e:
            raise CircuitExecutionError(f'Invalid response: {result.text}, {e}') from e

    @staticmethod
    def _validate_qubit_mapping(
        architecture: QuantumArchitectureSpecification,
        circuits: CircuitBatch,
        qubit_mapping: Optional[dict[str, str]] = None,
    ):
        """Validates the given qubit mapping, if defined.

        Args:
          architecture: the quantum architecture to check against
          circuits: list of circuits to be checked
          qubit_mapping: Mapping of logical qubit names to physical qubit names.
              Can be set to ``None`` if all ``circuits`` already use physical qubit names.
              Note that the ``qubit_mapping`` is used for all ``circuits``.

        Raises:
            CircuitExecutionError: IQM server specific exceptions
        """
        if qubit_mapping is None:
            return

        # check if qubit mapping is injective
        target_qubits = set(qubit_mapping.values())
        if not len(target_qubits) == len(qubit_mapping):
            raise ValueError('Multiple logical qubits map to the same physical qubit.')

        # check if qubit mapping covers all qubits in the circuits
        for i, circuit in enumerate(circuits):
            diff = circuit.all_qubits() - set(qubit_mapping)
            if diff:
                raise ValueError(
                    f"The qubits {diff} in circuit '{circuit.name}' at index {i} "
                    f'are not found in the provided qubit mapping.'
                )

        # check that each mapped qubit is defined in the quantum architecture
        for _logical, physical in qubit_mapping.items():
            if physical not in architecture.qubits:
                raise CircuitExecutionError(f'Qubit {physical} not present in quantum architecture')

    @staticmethod
    def _validate_circuit_instructions(
        architecture: QuantumArchitectureSpecification,
        circuits: CircuitBatch,
        qubit_mapping: Optional[dict[str, str]] = None,
    ):
        """Validates that the instructions target correct qubits in the given circuits.

        Args:
          architecture: the quantum architecture to check against
          circuits: list of circuits to be checked
          qubit_mapping: Mapping of logical qubit names to physical qubit names.
              Can be set to ``None`` if all ``circuits`` already use physical qubit names.
              Note that the ``qubit_mapping`` is used for all ``circuits``.

        Raises:
            CircuitExecutionError: IQM server specific exceptions
        """
        for circuit in circuits:
            for instr in circuit.instructions:
                IQMClient._validate_instruction(architecture, instr, qubit_mapping)

    @staticmethod
    def _validate_instruction(
        architecture: QuantumArchitectureSpecification,
        instruction: Instruction,
        qubit_mapping: Optional[dict[str, str]] = None,
    ):
        """Validates that the instruction targets correct qubits in the given architecture.

        Args:
          architecture: the quantum architecture to check against
          instruction: the instruction to check
          qubit_mapping: Mapping of logical qubit names to physical qubit names.
              Can be set to ``None`` if all ``circuits`` already use physical qubit names.
              Note that the ``qubit_mapping`` is used for all ``circuits``.

        Raises:
            CircuitExecutionError: IQM server specific exceptions
        """
        if instruction.name not in architecture.operations:
            raise ValueError(f"Instruction '{instruction.name}' is not supported by the quantum architecture.")
        allowed_loci = architecture.operations[instruction.name]
        qubits = [qubit_mapping[q] for q in instruction.qubits] if qubit_mapping else list(instruction.qubits)
        info = SUPPORTED_INSTRUCTIONS[instruction.name]
        check_locus = info['check_locus'] if 'check_locus' in info else None
        if check_locus is False:
            # Should skip locus check (e.g. for barrier)
            return
        if check_locus == 'any_combination':
            # Check that all qubits in the locus are allowed by the architecture
            allowed_qubits = set(q for locus in allowed_loci for q in locus)
            for q in instruction.qubits:
                mapped_q = qubit_mapping[q] if qubit_mapping else q
                if mapped_q not in allowed_qubits:
                    raise CircuitExecutionError(
                        f'Qubit {q} = {mapped_q} is not allowed as locus for {instruction.name}'
                        if qubit_mapping
                        else f'Qubit {q} is not allowed as locus for {instruction.name}'
                    )
            return

        # Check that locus matches one of the loci defined in architecture
        is_directed = 'directed' in info and info['directed'] is True
        all_loci = allowed_loci if is_directed else [qs for pair in allowed_loci for qs in [pair, pair[::-1]]]
        if qubits not in all_loci:
            raise CircuitExecutionError(
                f'{instruction.qubits} = {tuple(qubits)} not allowed as locus for {instruction.name}'
                if qubit_mapping
                else f'{instruction.qubits} not allowed as locus for {instruction.name}'
            )

    def get_run(self, job_id: UUID, *, timeout_secs: float = REQUESTS_TIMEOUT) -> RunResult:
        """Query the status and results of a submitted job.

        Args:
            job_id: id of the job to query
            timeout_secs: network request timeout

        Returns:
            result of the job (can be pending)

        Raises:
            CircuitExecutionError: IQM server specific exceptions
            HTTPException: HTTP exceptions
        """
        result = self._retry_request_on_error(
            lambda: requests.get(
                join(self._base_url, 'jobs', str(job_id)),
                headers=self._default_headers(),
                timeout=timeout_secs,
            )
        )

        result.raise_for_status()
        try:
            run_result = RunResult.from_dict(result.json())
        except (json.decoder.JSONDecodeError, KeyError) as e:
            raise CircuitExecutionError(f'Invalid response: {result.text}, {e}') from e

        if run_result.warnings:
            for warning in run_result.warnings:
                warnings.warn(warning)
        if run_result.status == Status.FAILED:
            raise CircuitExecutionError(run_result.message)
        return run_result

    def get_run_status(self, job_id: UUID, *, timeout_secs: float = REQUESTS_TIMEOUT) -> RunStatus:
        """Query the status of a submitted job.

        Args:
            job_id: id of the job to query
            timeout_secs: network request timeout

        Returns:
            status of the job

        Raises:
            CircuitExecutionError: IQM server specific exceptions
            HTTPException: HTTP exceptions
        """
        result = self._retry_request_on_error(
            lambda: requests.get(
                join(self._base_url, 'jobs', str(job_id), 'status'),
                headers=self._default_headers(),
                timeout=timeout_secs,
            )
        )

        result.raise_for_status()
        try:
            run_result = RunStatus.from_dict(result.json())
        except (json.decoder.JSONDecodeError, KeyError) as e:
            raise CircuitExecutionError(f'Invalid response: {result.text}, {e}') from e

        if run_result.warnings:
            for warning in run_result.warnings:
                warnings.warn(warning)
        return run_result

    def wait_for_compilation(self, job_id: UUID, timeout_secs: float = DEFAULT_TIMEOUT_SECONDS) -> RunResult:
        """Poll results until a job is either pending execution, ready, failed, aborted, or timed out.

        Args:
            job_id: id of the job to wait for
            timeout_secs: how long to wait for a response before raising an APITimeoutError

        Returns:
            job result

        Raises:
            APITimeoutError: time exceeded the set timeout
        """
        start_time = datetime.now()
        while (datetime.now() - start_time).total_seconds() < timeout_secs:
            status = self.get_run_status(job_id).status
            if status != Status.PENDING_COMPILATION:
                return self.get_run(job_id)
            time.sleep(SECONDS_BETWEEN_CALLS)
        raise APITimeoutError(f"The job compilation didn't finish in {timeout_secs} seconds.")

    def wait_for_results(self, job_id: UUID, timeout_secs: float = DEFAULT_TIMEOUT_SECONDS) -> RunResult:
        """Poll results until a job is either ready, failed, aborted, or timed out.
           Note, that jobs handling on the server side is async and if we try to request the results
           right after submitting the job (which is usually the case)
           we will find the job is still pending at least for the first query.

        Args:
            job_id: id of the job to wait for
            timeout_secs: how long to wait for a response before raising an APITimeoutError

        Returns:
            job result

        Raises:
            APITimeoutError: time exceeded the set timeout
        """
        start_time = datetime.now()
        while (datetime.now() - start_time).total_seconds() < timeout_secs:
            status = self.get_run_status(job_id).status
            if status not in (Status.PENDING_COMPILATION, Status.PENDING_EXECUTION):
                return self.get_run(job_id)
            time.sleep(SECONDS_BETWEEN_CALLS)
        raise APITimeoutError(f"The job didn't finish in {timeout_secs} seconds.")

    def abort_job(self, job_id: UUID, *, timeout_secs: float = REQUESTS_TIMEOUT) -> None:
        """Abort a job that was submitted for execution.

        Args:
            job_id: id of the job to be aborted
            timeout_secs: network request timeout

        Raises:
            HTTPException: HTTP exceptions
            JobAbortionError: if aborting the job failed
        """
        result = requests.post(
            join(self._base_url, 'jobs', str(job_id), 'abort'),
            headers=self._default_headers(),
            timeout=timeout_secs,
        )
        if result.status_code != 200:
            raise JobAbortionError(result.text)

    def get_quantum_architecture(self, *, timeout_secs: float = REQUESTS_TIMEOUT) -> QuantumArchitectureSpecification:
        """Retrieve quantum architecture from server.
        Caches the result and returns the same result on later invocations.

        Args:
            timeout_secs: network request timeout

        Returns:
            quantum architecture

        Raises:
            APITimeoutError: time exceeded the set timeout
            ClientConfigurationError: if no valid authentication is provided
            HTTPException: HTTP exceptions
        """
        if self._architecture:
            return self._architecture

        result = requests.get(
            join(self._base_url, 'quantum-architecture'),
            headers=self._default_headers(),
            timeout=timeout_secs,
        )

        # /quantum_architecture is not a strictly authenticated endpoint,
        # so we need to handle 302 redirects to the auth server login page
        if result.history and any(
            response.status_code == 302 for response in result.history
        ):  # pragma: no cover (generators are broken in coverage)
            raise ClientConfigurationError('Authentication is required.')
        if result.status_code == 401:
            raise ClientAuthenticationError(f'Authentication failed: {result.text}')

        result.raise_for_status()
        try:
            qa = QuantumArchitecture(**result.json()).quantum_architecture
        except (json.decoder.JSONDecodeError, KeyError) as e:
            raise CircuitExecutionError(f'Invalid response: {result.text}, {e}') from e
        # Cache architecture so that later invocations do not need to query it again
        self._architecture = qa
        return qa

    def close_auth_session(self) -> bool:
        """Terminate session with authentication server if there was one created.

        Returns:
            True iff session was successfully closed

        Raises:
            ClientAuthenticationError: if logout failed
            ClientAuthenticationError: if asked to close externally managed authentication session
        """
        if self._token_manager is None:
            return False
        return self._token_manager.close()

    def _default_headers(self) -> dict[str, str]:
        headers = {'User-Agent': self._signature}
        if self._token_manager is not None:
            bearer_token = self._token_manager.get_bearer_token()
            if bearer_token:
                headers['Authorization'] = bearer_token
        return headers
