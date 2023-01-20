# Copyright 2021-2022 IQM client developers
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

The :class:`Circuit` class represents quantum circuits to be executed, consisting of
native quantum operations, each represented by an instance of the :class:`Instruction` class.
Different Instruction types are distinguished by their :attr:`~Instruction.name`.
Each Instruction type acts on a number of :attr:`~Instruction.qubits`, and expects certain
:attr:`~Instruction.args`.


Instructions
============

We currently support the following native instruction types:

================ =========== ====================================== ===========
name             # of qubits args                                   description
================ =========== ====================================== ===========
measurement      >= 1        ``key: str``                           Measurement in the Z basis.
phased_rx        1           ``angle_t: float``, ``phase_t: float`` Phased x-rotation gate.
cz               2                                                  Controlled-Z gate.
barrier          >= 2                                               Execution barrier.
================ =========== ====================================== ===========

Instructions can be further specified by adding an ``implementation`` field with
a name for the implementation of the instruction. The default value for this field is
an empty string which selects the default implementation.
Support for multiple implementations is currently experimental and in normal use the
field should be omitted. This selects the default implementation for the instruction.

Measurement
-----------

Measurement in the computational (Z) basis. The measurement results are the output of the circuit.
Takes one string argument, ``key``, denoting the measurement key the results are labeled with.
All the measurement keys in a circuit must be unique.
Each qubit may only be measured once.
The measurement must be the last operation on each qubit, i.e. it cannot be followed by gates.

.. code-block:: python
   :caption: Example

   Instruction(name='measurement', qubits=('alice', 'bob', 'charlie'), args={'key': 'm1'})


Phased Rx
---------

Phased x-rotation gate, i.e. an x-rotation conjugated by a z-rotation.
Takes two arguments, the rotation angle ``angle_t`` and the phase angle ``phase_t``,
both measured in units of full turns (:math:`2\pi` radians).
The gate is represented in the standard computational basis by the matrix

.. math::
    R(\theta, \phi) = \exp(-i (X \cos (2 \pi \; \phi) + Y \sin (2 \pi \; \phi)) \: \pi \; \theta)
    = R_z(\phi) R_x(\theta) R_z^\dagger(\phi),

where :math:`\theta` = ``angle_t``, :math:`\phi` = ``phase_t``,
and :math:`X` and :math:`Y` are Pauli matrices.

.. code-block:: python
   :caption: Example

   Instruction(name='phased_rx', qubits=('bob',), args={'angle_t': 0.7, 'phase_t': 0.25})


CZ
--

Controlled-Z gate. Represented in the standard computational basis by the matrix

.. math:: \text{CZ} = \text{diag}(1, 1, 1, -1).

It is symmetric wrt. the qubits it's acting on, and takes no arguments.

.. code-block:: python
   :caption: Example

   Instruction(name='cz', qubits=('alice', 'bob'), args={})


Barrier
-------

A barrier instruction affects the physical execution order of the instructions elsewhere in the
circuit that act on qubits spanned by the barrier.
It ensures that any such instructions that succeed the barrier are only executed after
all such instructions that precede the barrier have been completed.
Hence it can be used to guarantee a specific causal order for the other instructions.
It takes no arguments, and has no other effect.

.. code-block:: python
   :caption: Example

   Instruction(name='barrier', qubits=('alice', 'bob'), args={})


Circuit output
==============

The :class:`RunResult` class represents the results of the quantum circuit execution job.
If the job succeeded, :attr:`RunResult.measurements` contains the output of the batch of circuits,
consisting of the results of the measurement operations in each circuit.
It is a list of dictionaries, where each dict maps each measurement key to a 2D array of measurement
results, represented as a nested list.
``RunResult.measurements[circuit_index][key][shot][qubit_index]`` is the result of measuring the
``qubit_index``'th qubit in measurement operation ``key`` in the shot ``shot`` in the
``circuit_index``'th circuit of the batch.

The results are non-negative integers representing the computational basis state (for qubits, 0 or 1)
that was the measurement outcome.

----
"""
from __future__ import annotations

from base64 import b64decode
from datetime import datetime
from enum import Enum
import json
import os
from posixpath import join
import time
from typing import Any, Callable, Optional, Union
from uuid import UUID
import warnings

from pydantic import BaseModel, Field
import requests

REQUESTS_TIMEOUT = 60

DEFAULT_TIMEOUT_SECONDS = 900
SECONDS_BETWEEN_CALLS = float(os.environ.get('IQM_CLIENT_SECONDS_BETWEEN_CALLS', 1.0))
REFRESH_MARGIN_SECONDS = REQUESTS_TIMEOUT

AUTH_CLIENT_ID = 'iqm_client'
AUTH_REALM = 'cortex'


class ClientConfigurationError(RuntimeError):
    """Wrong configuration provided."""


class ClientAuthenticationError(RuntimeError):
    """Something went wrong with user authentication."""


class CircuitExecutionError(RuntimeError):
    """Something went wrong on the server."""


class APITimeoutError(CircuitExecutionError):
    """Exception for when executing a job on the server takes too long."""


class Status(str, Enum):
    """
    Status of a job.
    """

    PENDING = 'pending'
    READY = 'ready'
    FAILED = 'failed'


class Instruction(BaseModel):
    """An instruction in a quantum circuit."""

    name: str = Field(..., example='measurement')
    """name of the quantum operation"""
    implementation: Optional[str] = Field(None)
    """name of the implementation, for experimental use only"""
    qubits: tuple[str, ...] = Field(..., example=('alice',))
    """names of the logical qubits the operation acts on"""
    args: dict[str, Any] = Field(..., example={'key': 'm'})
    """arguments for the operation"""


class Circuit(BaseModel):
    """Quantum circuit to be executed."""

    name: str = Field(..., example='test circuit')
    """name of the circuit"""
    instructions: tuple[Instruction, ...] = Field(...)
    """instructions comprising the circuit"""
    metadata: Optional[dict[str, Any]] = Field(None)
    """arbitrary metadata associated with the circuit"""

    def all_qubits(self) -> set[str]:
        """Return the names of all qubits in the circuit."""
        qubits: set[str] = set()
        for instruction in self.instructions:
            qubits.update(instruction.qubits)
        return qubits


CircuitBatch = list[Circuit]
"""Type that represents a list of quantum circuits to be executed together in a single batch."""


class SingleQubitMapping(BaseModel):
    """Mapping of a logical qubit name to a physical qubit name."""

    logical_name: str = Field(..., example='alice')
    """logical qubit name"""
    physical_name: str = Field(..., example='QB1')
    """physical qubit name"""


QubitMapping = list[SingleQubitMapping]
"""Type that represents a qubit mapping for a circuit, i.e. a list of single qubit mappings
for all qubits in the circuit."""


def serialize_qubit_mapping(qubit_mapping: dict[str, str]) -> list[SingleQubitMapping]:
    """Serializes a qubit mapping dict into the corresponding IQM data transfer format.

    Args:
        qubit_mapping: mapping from logical to physical qubit names

    Returns:
        data transfer object representing the mapping
    """
    return [SingleQubitMapping(logical_name=k, physical_name=v) for k, v in qubit_mapping.items()]


class RunRequest(BaseModel):
    """Request for an IQM quantum computer to run a job that executes a batch of quantum circuits.

    Note: all circuits in a batch must measure the same qubits otherwise batch execution fails.
    """

    circuits: CircuitBatch = Field(...)
    """batch of quantum circuit(s) to execute"""
    custom_settings: dict[str, Any] = Field(None)
    """Custom settings to override default IQM hardware settings and calibration data.
Note: This field should be always None in normal use."""
    calibration_set_id: Optional[UUID] = Field(None)
    """ID of the calibration set to use, or None to use the latest calibration set"""
    qubit_mapping: Optional[list[SingleQubitMapping]] = Field(None)
    """mapping of logical qubit names to physical qubit names, or None if using physical qubit names"""
    shots: int = Field(...)
    """how many times to execute each circuit in the batch"""


CircuitMeasurementResults = dict[str, list[list[int]]]
"""Measurement results from a single circuit. For each measurement operation in the circuit,
maps the measurement key to the corresponding results. The outer list elements correspond to shots,
and the inner list elements to the qubits measured in the measurement operation."""


CircuitMeasurementResultsBatch = list[CircuitMeasurementResults]
"""Type that represents measurement results for a batch of circuits."""


class Metadata(BaseModel):
    """Metadata describing a circuit execution job."""

    calibration_set_id: Optional[UUID] = Field(None)
    """ID of the calibration set used"""
    request: RunRequest = Field(...)
    """copy of the original RunRequest sent to the server"""


class RunResult(BaseModel):
    """Results of a circuit execution job.

    * ``measurements`` is present iff the status is ``'ready'``.
    * ``message`` carries additional information for the ``'failed'`` status.
    * If the status is ``'pending'``, ``measurements`` and ``message`` are ``None``.
    """

    status: Status = Field(...)
    """current status of the job, in ``{'pending', 'ready', 'failed'}``"""
    measurements: Optional[CircuitMeasurementResultsBatch] = Field(None)
    """if the job has finished successfully, the measurement results for the circuit(s)"""
    message: Optional[str] = Field(None)
    """if the job failed, an error message"""
    metadata: Metadata = Field(...)
    """metadata about the job"""
    warnings: Optional[list[str]] = Field(None)
    """list of warning messages"""

    @staticmethod
    def from_dict(inp: dict[str, Union[str, dict]]) -> RunResult:
        """Parses the result from a dict.

        Args:
            inp: value to parse, has to map to RunResult

        Returns:
            parsed job result

        """
        input_copy = inp.copy()
        return RunResult(status=Status(input_copy.pop('status')), **input_copy)


class RunStatus(BaseModel):
    """Status of a circuit execution job."""

    status: Status = Field(...)
    """current status of the job, in ``{'pending', 'ready', 'failed'}``"""
    message: Optional[str] = Field(None)
    """if the job failed, an error message"""
    warnings: Optional[list[str]] = Field(None)
    """list of warning messages"""

    @staticmethod
    def from_dict(inp: dict[str, Union[str, dict]]) -> RunStatus:
        """Parses the result from a dict.

        Args:
            inp: value to parse, has to map to RunResult

        Returns:
            parsed job status

        """
        input_copy = inp.copy()
        return RunStatus(status=Status(input_copy.pop('status')), **input_copy)


class QuantumArchitectureSpecification(BaseModel):
    """Quantum architecture specification."""

    name: str = Field(...)
    """name of the quantum architecture"""
    operations: list[str] = Field(...)
    """list of operations supported by this quantum architecture"""
    qubits: list[str] = Field(...)
    """list of qubits of this quantum architecture"""
    qubit_connectivity: list[list[str]] = Field(...)
    """qubit connectivity of this quantum architecture"""


class QuantumArchitecture(BaseModel):
    """Quantum architecture as returned by Cortex."""

    quantum_architecture: QuantumArchitectureSpecification = Field(...)
    """details about the quantum architecture"""


class GrantType(str, Enum):
    """
    Type of token request.
    """

    PASSWORD = 'password'
    REFRESH = 'refresh_token'


class AuthRequest(BaseModel):
    """Request sent to authentication server for access token and refresh token, or for terminating the session.

    * Token request with grant type ``'password'`` starts a new session in the authentication server.
      It uses fields ``client_id``, ``grant_type``, ``username`` and ``password``.
    * Token request with grant type ``'refresh_token'`` is used for maintaining an existing session.
      It uses field ``client_id``, ``grant_type``, ``refresh_token``.
    * Logout request uses only fields ``client_id`` and ``refresh_token``.

    """

    client_id: str = Field(...)
    """name of the client for all request types"""
    grant_type: Optional[GrantType] = Field(None)
    """type of token request, in ``{'password', 'refresh_token'}``"""
    username: Optional[str] = Field(None)
    """username for grant type ``'password'``"""
    password: Optional[str] = Field(None)
    """password for grant type ``'password'``"""
    refresh_token: Optional[str] = Field(None)
    """refresh token for grant type ``'refresh_token'`` and logout request"""


class Credentials(BaseModel):
    """Credentials and tokens for maintaining a session with the authentication server.

    * Fields ``auth_server_url``, ``username`` and ``password`` are provided by the user.
    * Fields ``access_token`` and ``refresh_token`` are loaded from the authentication server and
      refreshed periodically.
    """

    auth_server_url: str = Field(...)
    """Base URL of the authentication server"""
    username: str = Field(...)
    """username for logging in to the server"""
    password: str = Field(...)
    """password for logging in to the server"""
    access_token: Optional[str] = Field(None)
    """current access token of the session"""
    refresh_token: Optional[str] = Field(None)
    """current refresh token of the session"""


class ExternalToken(BaseModel):
    """Externally managed token for maintaining a session with the authentication server.

    * Fields ``auth_server_url`` and ``access_token`` are loaded from an
      external resource, e.g. file generated by Cortex CLI's token manager.
    """

    auth_server_url: str = Field(...)
    """Base URL of the authentication server"""
    access_token: str = Field(None)
    """current access token of the session"""


def _get_credentials(credentials: dict[str, str]) -> Optional[Credentials]:
    """Try to obtain credentials, first from arguments, then from environment variables.

    Args:
        credentials: dict of credentials provided as arguments

    Returns:
        Credentials with token fields cleared, or None if ``auth_server_url`` was not set.
    """
    auth_server_url = credentials.get('auth_server_url') or os.environ.get('IQM_AUTH_SERVER')
    username = credentials.get('username') or os.environ.get('IQM_AUTH_USERNAME')
    password = credentials.get('password') or os.environ.get('IQM_AUTH_PASSWORD')
    if not auth_server_url:
        return None
    if not username or not password:
        raise ClientConfigurationError('Auth server URL is set but no username or password')
    return Credentials(auth_server_url=auth_server_url, username=username, password=password)


def _get_external_token(tokens_file: Optional[str] = None) -> Optional[ExternalToken]:
    """Try to obtain external token from a file, first by path provided, then by path from
    environment variable.

    Args:
        tokens_file: path to a JSON file containing tokens

    Returns:
        ExternalToken with non-empty auth_server_url and access_token fields,
        or None if ``tokens_file`` was not provided.
    """

    filepath = tokens_file or os.environ.get('IQM_TOKENS_FILE')

    if not filepath:
        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            raw_data = file.read()
    except FileNotFoundError as error:
        raise ClientConfigurationError(f'File not found: {filepath}') from error

    try:
        json_data = json.loads(raw_data)
    except json.decoder.JSONDecodeError as error:
        raise ClientConfigurationError(f'Decoding JSON has failed, {error}') from error

    auth_server_url = json_data['auth_server_url']
    access_token = json_data['access_token']

    return ExternalToken(auth_server_url=auth_server_url, access_token=access_token)


def _time_left_seconds(token: str) -> int:
    """Check how much time is left until the token expires.

    Returns:
        Time left on token in seconds.
    """
    _, body, _ = token.split('.', 2)
    # Add padding to adjust body length to a multiple of 4 chars as required by base64 decoding
    body += '=' * (-len(body) % 4)
    exp_time = int(json.loads(b64decode(body)).get('exp', '0'))
    return max(0, exp_time - int(time.time()))


class IQMClient:
    """Provides access to IQM quantum computers.

    Args:
        url: Endpoint for accessing the server. Has to start with http or https.
        tokens_file: Optional path to a tokens file used for authentication.
            This can also be set in the IQM_TOKENS_FILE environment variable.
            If tokens_file is set, auth_server_url, username and password
            must not be set.

    Keyword Args:
        auth_server_url (str): Optional base URL of the authentication server.
            This can also be set in the IQM_AUTH_SERVER environment variable.
            If unset, requests will be sent unauthenticated.
        username (str): Optional username to log in to authentication server.
            This can also be set in the IQM_AUTH_USERNAME environment variable.
            Username must be set if ``auth_server_url`` is set.
        password (str): Optional password to log in to authentication server.
            This can also be set in the IQM_AUTH_PASSWORD environment variable.
            Password must be set if ``auth_server_url`` is set.
    """

    def __init__(
        self, url: str, tokens_file: Optional[str] = None, **credentials  # contains auth_server_url, username, password
    ):
        if not url.startswith(('http:', 'https:')):
            raise ClientConfigurationError(f'The URL schema has to be http or https. Incorrect schema in URL: {url}')
        if tokens_file and credentials:
            raise ClientConfigurationError('Either external token or credentials must be provided. Both were provided.')
        self._base_url = url
        self._tokens_file = tokens_file
        self._external_token = _get_external_token(tokens_file)
        if not self._external_token:
            self._credentials = _get_credentials(credentials)
            self._update_tokens()

    def __del__(self):
        try:
            # try our best to close the auth session, doesn't matter if it fails,
            # refresh token will be re-issued for the same credentials or eventually expire
            if not self._external_token:
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
            shots: number of times ``circuits`` are executed

        Returns:
            ID for the created job. This ID is needed to query the job status and the execution results.
        """
        serialized_qubit_mapping: Optional[list[SingleQubitMapping]] = None
        if qubit_mapping is not None:
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

            serialized_qubit_mapping = serialize_qubit_mapping(qubit_mapping)

        # ``bearer_token`` can be ``None`` if cocos we're connecting does not use authentication
        bearer_token = self._get_bearer_token()

        data = RunRequest(
            qubit_mapping=serialized_qubit_mapping,
            circuits=circuits,
            custom_settings=custom_settings,
            calibration_set_id=calibration_set_id,
            shots=shots,
        )

        headers = {'Expect': '100-Continue'}
        if bearer_token:
            headers['Authorization'] = bearer_token

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
                json=json.loads(data.json(exclude_none=True)),
                headers=headers,
                timeout=REQUESTS_TIMEOUT,
            )
        )

        if result.status_code == 401:
            raise ClientAuthenticationError(f'Authentication failed: {result.text}')

        result.raise_for_status()
        return UUID(result.json()['id'])

    def get_run(self, job_id: UUID) -> RunResult:
        """Query the status and results of a submitted job.

        Args:
            job_id: id of the job to query

        Returns:
            result of the job (can be pending)

        Raises:
            HTTPException: http exceptions
            CircuitExecutionError: IQM server specific exceptions
        """
        bearer_token = self._get_bearer_token()

        result = self._retry_request_on_error(
            lambda: requests.get(
                join(self._base_url, 'jobs/', str(job_id)),
                headers=None if not bearer_token else {'Authorization': bearer_token},
                timeout=REQUESTS_TIMEOUT,
            )
        )

        result.raise_for_status()
        run_result = RunResult.from_dict(result.json())
        if run_result.warnings:
            for warning in run_result.warnings:
                warnings.warn(warning)
        if run_result.status == Status.FAILED:
            raise CircuitExecutionError(run_result.message)
        return run_result

    def get_run_status(self, job_id: UUID) -> RunStatus:
        """Query the status of a submitted job.

        Args:
            job_id: id of the job to query

        Returns:
            status of the job

        Raises:
            HTTPException: http exceptions
            CircuitExecutionError: IQM server specific exceptions
        """
        bearer_token = self._get_bearer_token()

        result = self._retry_request_on_error(
            lambda: requests.get(
                join(self._base_url, 'jobs/', str(job_id), 'status'),
                headers=None if not bearer_token else {'Authorization': bearer_token},
                timeout=REQUESTS_TIMEOUT,
            )
        )

        result.raise_for_status()
        run_result = RunStatus.from_dict(result.json())
        if run_result.warnings:
            for warning in run_result.warnings:
                warnings.warn(warning)
        return run_result

    def wait_for_results(self, job_id: UUID, timeout_secs: float = DEFAULT_TIMEOUT_SECONDS) -> RunResult:
        """Poll results until a job is either ready, failed, or timed out.
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
            results = self.get_run(job_id)
            if results.status != Status.PENDING:
                return results
            time.sleep(SECONDS_BETWEEN_CALLS)
        raise APITimeoutError(f"The job didn't finish in {timeout_secs} seconds.")

    def get_quantum_architecture(self) -> QuantumArchitectureSpecification:
        """Retrieve quantum architecture from Cortex.

        Returns:
            quantum architecture

        Raises:
            APITimeoutError: time exceeded the set timeout
            ClientConfigurationError: if no valid authentication is provided
        """
        bearer_token = self._get_bearer_token()
        result = requests.get(
            join(self._base_url, 'quantum-architecture'),
            headers=None if not bearer_token else {'Authorization': bearer_token},
            timeout=REQUESTS_TIMEOUT,
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
        return QuantumArchitecture(**result.json()).quantum_architecture

    def close_auth_session(self) -> bool:
        """Terminate session with authentication server if there was one created.

        Returns:
            True iff session was successfully closed

        Raises:
            ClientAuthenticationError: if logout failed
            ClientAuthenticationError: if asked to close externally managed authentication session
        """
        # auth session is managed externally, unable to close it here
        if self._external_token:
            raise ClientAuthenticationError('Unable to close externally managed auth session')

        # no auth, nothing to close
        if self._credentials is None:
            return False

        # auth session wasn't started, nothing to close
        if not self._credentials.refresh_token:
            return False

        url = f'{self._credentials.auth_server_url}/realms/{AUTH_REALM}/protocol/openid-connect/logout'
        data = AuthRequest(client_id=AUTH_CLIENT_ID, refresh_token=self._credentials.refresh_token)
        result = requests.post(url, data=data.dict(exclude_none=True), timeout=REQUESTS_TIMEOUT)
        if result.status_code not in [200, 204]:
            raise ClientAuthenticationError(f'Logout failed, {result.text}')
        self._credentials.access_token = None
        self._credentials.refresh_token = None
        return True

    def _get_bearer_token(self, retries: int = 1) -> Optional[str]:
        """Make a bearer token for Authorization header. If access token is about to expire refresh it first.

        Args:
            retries: number of times to try updating the tokens

        Returns:
            Bearer token, i.e. string containing prefix 'Bearer ' and the access token, or None if access token
            is not available.
        """
        if self._external_token:
            # If access token obtained from external tokens file expires soon, get updated token from the tokens file
            if _time_left_seconds(self._external_token.access_token) < REFRESH_MARGIN_SECONDS:
                self._external_token = _get_external_token(self._tokens_file)
                if not self._external_token:
                    return None
            return f'Bearer {self._external_token.access_token}'
        if self._credentials is None or not self._credentials.access_token:
            return None
        if _time_left_seconds(self._credentials.access_token) > REFRESH_MARGIN_SECONDS:
            # Access token is still valid, no need to refresh
            return f'Bearer {self._credentials.access_token}'
        if retries < 1:
            return None
        self._update_tokens()
        return self._get_bearer_token(retries - 1)

    def _update_tokens(self):
        """Update access token and refresh token.

        Uses refresh token to request new tokens from authentication server.  If the refresh token has expired or
        is about to expire, starts a new session by requesting the tokens using username and password.

        Updated tokens are stored in ``self._credentials``.

        Raises:
            ClientAuthenticationError: updating the tokens failed
        """
        if self._credentials is None:
            return

        refresh_token = self._credentials.refresh_token
        if refresh_token and _time_left_seconds(refresh_token) > REFRESH_MARGIN_SECONDS:
            # Update tokens using existing refresh_token
            data = AuthRequest(client_id=AUTH_CLIENT_ID, grant_type=GrantType.REFRESH, refresh_token=refresh_token)
        else:
            # Update tokens using username and password
            data = AuthRequest(
                client_id=AUTH_CLIENT_ID,
                grant_type=GrantType.PASSWORD,
                username=self._credentials.username,
                password=self._credentials.password,
            )

        url = f'{self._credentials.auth_server_url}/realms/{AUTH_REALM}/protocol/openid-connect/token'
        result = requests.post(url, data=data.dict(exclude_none=True), timeout=REQUESTS_TIMEOUT)
        if result.status_code != 200:
            raise ClientAuthenticationError(f'Failed to update tokens, {result.text}')
        tokens = result.json()
        self._credentials.access_token = tokens.get('access_token')
        self._credentials.refresh_token = tokens.get('refresh_token')
