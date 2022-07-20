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

The :class:`Circuit` class represents quantum circuits to be executed, consisting of a list of
native quantum operations, each represented by an instance of the :class:`Instruction` class.
Different Instruction types are distinguished by their :attr:`~Instruction.name`.
Each Instruction type acts on a number of :attr:`~Instruction.qubits`, and expects certain
:attr:`~Instruction.args`.


Instructions
============

We currently support three native instruction types:

================ =========== ====================================== ===========
name             # of qubits args                                   description
================ =========== ====================================== ===========
measurement      >= 1        ``key: str``                           Measurement in the Z basis.
phased_rx        1           ``angle_t: float``, ``phase_t: float`` Phased x-rotation gate.
cz               2                                                  Controlled-Z gate.
barrier          >= 2                                               Barrier instruction.
================ =========== ====================================== ===========

Measurement
-----------

Measurement in the computational (Z) basis. The measurement results are the output of the circuit.
Takes one string argument, ``key``, denoting the measurement key the results are labeled with.
All the measurement keys in a circuit must be unique.
Each qubit may only be measured once.
The measurement must be the last operation on each qubit, i.e. it cannot be followed by gates.

Example: ``Instruction(name='measurement', qubits=['alice', 'bob', 'charlie'], args={'key': 'm1'})``


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

Example: ``Instruction(name='phased_rx', qubits=['bob'], args={'angle_t': 0.7, 'phase_t': 0.25})``


CZ
--

Controlled-Z gate. Represented in the standard computational basis by the matrix

.. math:: \text{CZ} = \text{diag}(1, 1, 1, -1).

Symmetric wrt. the qubits it's acting on. Takes no arguments.

Example: ``Instruction(name='cz', qubits=['alice', 'bob'], args={})``


Barrier
-------

Barriers ensure that all operations after the barrier on the qubit subsystems spanned by
the barrier are only executed when all the operations before the barrier have been completed.

Example: ``Instruction(name='barrier', qubits=['alice', 'bob'], args={})``


Circuit output
==============

The :class:`RunResult` class represents the results of the quantum circuit execution.
If the run succeeded, :attr:`RunResult.measurements` contains the output of the batch of circuits,
consisting of the results of the measurement operations in each circuit.
It is a list of dictionaries, where each dict maps each measurement key to a 2D array of measurement
results, represented as a nested list.
``RunResult.measurements[circuit_index][key][shot][qubit_index]`` is the result of measuring the
``qubit_index``'th qubit in measurement operation ``key`` in the shot ``shot`` in the
``circuit_index``'th circuit of the batch.

The results are nonnegative integers representing the computational basis state (for qubits, 0 or 1)
that was the measurement outcome.

----
"""
from __future__ import annotations

import json
import os
import time
import warnings
from base64 import b64decode
from datetime import datetime
from enum import Enum
from posixpath import join
from typing import Any, Optional, Union
from uuid import UUID

import requests
from pydantic import BaseModel, Field

DEFAULT_TIMEOUT_SECONDS = 900
SECONDS_BETWEEN_CALLS = 1
REFRESH_MARGIN_SECONDS = 5

AUTH_CLIENT_ID = 'iqm_client'
AUTH_REALM = 'cortex'


class ClientConfigurationError(RuntimeError):
    """Wrong configuration provided.
    """


class ClientAuthenticationError(RuntimeError):
    """Something went wrong with user authentication.
    """


class CircuitExecutionError(RuntimeError):
    """Something went wrong on the server.
    """


class APITimeoutError(CircuitExecutionError):
    """Exception for when executing a task on the server takes too long.
    """


class RunStatus(str, Enum):
    """
    Status of a task.
    """
    PENDING = 'pending'
    READY = 'ready'
    FAILED = 'failed'


class Instruction(BaseModel):
    """An instruction in a quantum circuit.
    """
    name: str = Field(..., description='name of the quantum operation', example='measurement')
    'name of the quantum operation'
    qubits: list[str] = Field(
        ...,
        description='names of the logical qubits the operation acts on',
        example=['alice'],
    )
    'names of the logical qubits the operation acts on'
    args: dict[str, Any] = Field(
        ...,
        description='arguments for the operation',
        example={'key': 'm'},
    )
    'arguments for the operation'


class Circuit(BaseModel):
    """Quantum circuit to be executed.
    """
    name: str = Field(..., description='name of the circuit', example='test circuit')
    'name of the circuit'
    instructions: list[Instruction] = Field(..., description='instructions comprising the circuit')
    'instructions comprising the circuit'


class SingleQubitMapping(BaseModel):
    """Mapping of a logical qubit name to a physical qubit name.
    """
    logical_name: str = Field(..., description='logical qubit name', example='alice')
    'logical qubit name'
    physical_name: str = Field(..., description='physical qubit name', example='QB1')
    'physical qubit name'


class RunRequest(BaseModel):
    """Request for an IQM quantum computer to execute a batch of quantum circuits.

    Note: all circuits in a batch must measure the same qubits otherwise batch execution fails.
    """
    circuits: list[Circuit] = Field(..., description='batch of quantum circuit(s) to execute')
    'batch of quantum circuit(s) to execute'
    settings: Optional[dict[str, Any]] = Field(
        None,
        description='EXA settings node containing the calibration data, or None if using default settings'
    )
    'EXA settings node containing the calibration data, or None if using default settings'
    qubit_mapping: Optional[list[SingleQubitMapping]] = Field(
        None,
        description='mapping of logical qubit names to physical qubit names, or None if using physical qubit names'
    )
    'mapping of logical qubit names to physical qubit names, or None if using physical qubit names'
    shots: int = Field(..., description='how many times to execute each circuit in the batch')
    'how many times to execute each circuit in the batch'


CircuitMeasurementResults = dict[str, list[list[int]]]
"""Measurement results from a single circuit. For each measurement operation in the circuit,
maps the measurement key to the corresponding results. The outer list elements correspond to shots,
and the inner list elements to the qubits measured in the measurement operation."""


class RunResult(BaseModel):
    """Results of executing a batch of circuit(s).

    * ``measurements`` is present iff the status is ``'ready'``.
    * ``message`` carries additional information for the ``'failed'`` status.
    * If the status is ``'pending'``, ``measurements`` and ``message`` are ``None``.
    """
    status: RunStatus = Field(..., description="current status of the run, in ``{'pending', 'ready', 'failed'}``")
    "current status of the run, in ``{'pending', 'ready', 'failed'}``"
    measurements: Optional[list[CircuitMeasurementResults]] = Field(
        None,
        description='if the run has finished successfully, the measurement results for the circuit(s)'
    )
    'if the run has finished successfully, the measurement results for the circuit(s)'
    message: Optional[str] = Field(None, description='if the run failed, an error message')
    'if the run failed, an error message'
    warnings: Optional[list[str]] = Field(None, description='list of warning messages')
    'list of warning messages'

    @staticmethod
    def from_dict(inp: dict[str, Union[str, dict]]) -> RunResult:
        """Parses the result from a dict.

        Args:
            inp: value to parse, has to map to RunResult

        Returns:
            parsed run result

        """
        input_copy = inp.copy()
        return RunResult(status=RunStatus(input_copy.pop('status')), **input_copy)


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
    client_id: str = Field(..., description='name of the client for all request types')
    'name of the client for all request types'
    grant_type: Optional[GrantType] = Field(
        None,
        description="type of token request, in ``{'password', 'refresh_token'}``"
    )
    "type of token request, in ``{'password', 'refresh_token'}``"
    username: Optional[str] = Field(None, description="username for grant type ``'password'``")
    "username for grant type ``'password'``"
    password: Optional[str] = Field(None, description="password for grant type ``'password'``")
    "password for grant type ``'password'``"
    refresh_token: Optional[str] = Field(
        None,
        description="refresh token for grant type ``'refresh_token'`` and logout request")
    "refresh token for grant type ``'refresh_token'`` and logout request"


class Credentials(BaseModel):
    """Credentials and tokens for maintaining a session with the authentication server.

    * Fields ``auth_server_url``, ``username`` and ``password`` are provided by the user.
    * Fields ``access_token`` and ``refresh_token`` are loaded from the authentication server and
      refreshed periodically.
    """
    auth_server_url: str = Field(..., description='Base URL of the authentication server')
    'Base URL of the authentication server'
    username: str = Field(..., description='username for logging in to the server')
    'username for logging in to the server'
    password: str = Field(..., description='password for logging in to the server')
    'password for logging in to the server'
    access_token: Optional[str] = Field(None, description='current access token of the session')
    'current access token of the session'
    refresh_token: Optional[str] = Field(None, description='current refresh token of the session')
    'current refresh token of the session'

class ExternalToken(BaseModel):
    """Externally managed token for maintaining a session with the authentication server.

    * Fields ``auth_server_url`` and ``access_token`` are loaded from an
      external resource, e.g. file generated by Cortex CLI's token manager.
    """

    auth_server_url: str = Field(..., description='Base URL of the authentication server')
    'Base URL of the authentication server'
    access_token: str = Field(None, description='current access token of the session')
    'current access token of the session'

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
        settings: Settings for the quantum computer, in IQM JSON format.
        tokens_file: Optional path to a tokens file used for authentication.
            This can also be set in the IQM_TOKENS_FILE environment variable.
            If tokens_file is set, auth_server_url, username and password
            must no be set.

    Keyword Args:
        auth_server_url: Optional base URL of the authentication server.
            This can also be set in the IQM_AUTH_SERVER environment variable.
            If unset, requests will be sent unauthenticated.
        username: Optional username to log in to authentication server.
            This can also be set in the IQM_AUTH_USERNAME environment variable.
            Username must be set if ``auth_server_url`` is set.
        password: Optional password to log in to authentication server.
            This can also be set in the IQM_AUTH_PASSWORD environment variable.
            Password must be set if ``auth_server_url`` is set.
    """
    def __init__(
            self,
            url: str,
            settings: Optional[dict[str, Any]] = None,
            tokens_file: Optional[str] = None,
            **credentials  # contains auth_server_url, username, password
    ):
        if not url.startswith(('http:', 'https:')):
            raise ClientConfigurationError(f'The URL schema has to be http or https. Incorrect schema in URL: {url}')
        if tokens_file and credentials:
            raise ClientConfigurationError('Either external token or credentials must be provided. Both were provided.')
        self._base_url = url
        self._settings = settings
        self._external_token = _get_external_token(tokens_file)
        if not self._external_token:
            self._credentials = _get_credentials(credentials)
            self._update_tokens()

    def submit_circuits(
            self,
            circuits: list[Circuit],
            qubit_mapping: Optional[list[SingleQubitMapping]] = None,
            shots: int = 1
    ) -> UUID:
        """Submits a batch of quantum circuits for execution on a quantum computer.

        Args:
            circuits: list of circuit to be executed
            qubit_mapping: Mapping of human-readable (logical) qubit names in to physical qubit names.
                Can be set to ``None`` if all ``circuits`` already use physical qubit names.
                Note that the ``qubit_mapping`` is used for all ``circuits``.
            shots: number of times ``circuit`` is executed

        Returns:
            ID for the created task. This ID is needed to query the status and the execution results.
        """

        bearer_token = self._get_bearer_token()

        data = RunRequest(
            qubit_mapping=qubit_mapping,
            circuits=circuits,
            settings=self._settings,
            shots=shots
        )

        headers = {'Expect': '100-Continue'}
        if bearer_token:
            headers['Authorization'] = bearer_token

        result = requests.post(
            join(self._base_url, 'jobs'),
            json=data.dict(exclude_none=True),
            headers=headers,
        )
        result.raise_for_status()
        return UUID(result.json()['id'])

    def get_run(self, job_id: UUID) -> RunResult:
        """Query the status and results of the running task.

        Args:
            job_id: id of the task

        Returns:
            result of the run (can be pending)

        Raises:
            HTTPException: http exceptions
            CircuitExecutionError: IQM server specific exceptions
        """
        bearer_token = self._get_bearer_token()
        result = requests.get(
            join(self._base_url, 'jobs/', str(job_id)),
            headers=None if not bearer_token else {'Authorization': bearer_token}
        )
        result.raise_for_status()
        result = RunResult.from_dict(result.json())
        if result.warnings:
            for warning in result.warnings:
                warnings.warn(warning)
        if result.status == RunStatus.FAILED:
            raise CircuitExecutionError(result.message)
        return result

    def get_run_status(self, job_id: UUID) -> RunResult:
        """Query the status of the running task.

        Args:
            job_id: id of the task

        Returns:
            status of the run

        Raises:
            HTTPException: http exceptions
            CircuitExecutionError: IQM server specific exceptions
        """
        bearer_token = self._get_bearer_token()
        result = requests.get(
            join(self._base_url, 'jobs/', str(job_id), 'status'),
            headers=None if not bearer_token else {'Authorization': bearer_token}
        )
        result.raise_for_status()
        result = RunResult.from_dict(result.json())
        if result.warnings:
            for warning in result.warnings:
                warnings.warn(warning)
        return result

    def wait_for_results(self, job_id: UUID, timeout_secs: float = DEFAULT_TIMEOUT_SECONDS) -> RunResult:
        """Poll results until run is ready, failed, or timed out.

        Args:
            job_id: id of the task to wait
            timeout_secs: how long to wait for a response before raising an APITimeoutError

        Returns:
            run result

        Raises:
            APITimeoutError: time exceeded the set timeout
        """
        start_time = datetime.now()
        while (datetime.now() - start_time).total_seconds() < timeout_secs:
            results = self.get_run(job_id)
            if results.status != RunStatus.PENDING:
                return results
            time.sleep(SECONDS_BETWEEN_CALLS)
        raise APITimeoutError(f"The task didn't finish in {timeout_secs} seconds.")

    def close(self) -> bool:
        """Terminate session with authentication server.

        Returns:
            True iff session was successfully closed

        Raises:
            ClientAuthenticationError: if logout failed
        """
        if self._credentials is None:
            return False

        if not self._credentials.refresh_token:
            return False

        url = f'{self._credentials.auth_server_url}/realms/{AUTH_REALM}/protocol/openid-connect/logout'
        data = AuthRequest(client_id=AUTH_CLIENT_ID, refresh_token=self._credentials.refresh_token)
        result = requests.post(url, data=data.dict(exclude_none=True))
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
            data = AuthRequest(
                client_id=AUTH_CLIENT_ID,
                grant_type=GrantType.REFRESH,
                refresh_token=refresh_token
            )
        else:
            # Update tokens using username and password
            data = AuthRequest(
                client_id=AUTH_CLIENT_ID,
                grant_type=GrantType.PASSWORD,
                username=self._credentials.username,
                password=self._credentials.password
            )

        url = f'{self._credentials.auth_server_url}/realms/{AUTH_REALM}/protocol/openid-connect/token'
        result = requests.post(url, data=data.dict(exclude_none=True))
        if result.status_code != 200:
            raise ClientAuthenticationError(f'Failed to update tokens, {result.text}')
        tokens = result.json()
        self._credentials.access_token = tokens.get('access_token')
        self._credentials.refresh_token = tokens.get('refresh_token')
