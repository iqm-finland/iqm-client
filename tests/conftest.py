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

"""
Mocks server calls for testing
"""

from base64 import b64encode
import json
import os
import platform
import time
from typing import Any, Optional
from uuid import UUID

from mockito import expect, mock, when
from mockito.matchers import ANY
import pytest
import requests
from requests import HTTPError, Response

from iqm.iqm_client import (
    AUTH_CLIENT_ID,
    AUTH_REALM,
    DIST_NAME,
    REQUESTS_TIMEOUT,
    AuthRequest,
    Circuit,
    GrantType,
    HeraldingMode,
    Instruction,
    IQMClient,
    RunRequest,
    SingleQubitMapping,
    __version__,
)


@pytest.fixture()
def base_url() -> str:
    return 'https://example.com'


@pytest.fixture()
def client_signature() -> str:
    return 'some-signature'


@pytest.fixture()
def sample_calibration_set_id() -> UUID:
    return UUID('9ddb9586-8f27-49a9-90ed-41086b47f6bd')


@pytest.fixture()
def existing_run_id() -> UUID:
    return UUID('3c3fcda3-e860-46bf-92a4-bcc59fa76ce9')


@pytest.fixture()
def missing_run_id() -> UUID:
    return UUID('059e4186-50a3-4e6c-ba1f-37fe6afbdfc2')


@pytest.fixture()
def sample_client(base_url) -> IQMClient:
    return IQMClient(url=base_url)


@pytest.fixture()
def client_with_signature(base_url) -> IQMClient:
    return IQMClient(url=base_url, client_signature='some-signature')


@pytest.fixture()
def credentials(base_url):
    return {
        'auth_server_url': f'{base_url}/auth',
        'username': 'some_username',
        'password': 'some_password',
    }


@pytest.fixture()
def client_with_credentials(base_url, credentials):
    prepare_tokens(300, 300, **credentials)
    return IQMClient(url=base_url, **credentials)


@pytest.fixture()
def client_with_external_token(tokens_dict, credentials):
    prepare_tokens(300, 300, **credentials)
    tokens_path = os.path.dirname(os.path.realpath(__file__)) + '/resources/tokens.json'
    return IQMClient(tokens_dict['auth_server_url'], tokens_file=tokens_path)


@pytest.fixture()
def jobs_url(base_url) -> str:
    return f'{base_url}/jobs'


@pytest.fixture()
def existing_job_url(jobs_url, existing_run_id) -> str:
    return f'{jobs_url}/{existing_run_id}'


@pytest.fixture()
def existing_job_status_url(existing_job_url) -> str:
    return f'{existing_job_url}/status'


@pytest.fixture()
def quantum_architecture_url(base_url) -> str:
    return f'{base_url}/quantum-architecture'


@pytest.fixture
def settings_dict():
    """
    Reads and parses settings file into a dictionary
    """
    settings_path = os.path.dirname(os.path.realpath(__file__)) + '/resources/settings.json'
    with open(settings_path, 'r', encoding='utf-8') as f:
        return json.loads(f.read())


@pytest.fixture
def tokens_dict():
    """
    Reads and parses tokens file into a dictionary
    """
    tokens_path = os.path.dirname(os.path.realpath(__file__)) + '/resources/tokens.json'
    with open(tokens_path, 'r', encoding='utf-8') as f:
        return json.loads(f.read())


@pytest.fixture()
def sample_circuit_metadata():
    return {'experiment_type': 'test', 'qubits': (0, 1), 'values': [0.01686514, 0.05760602]}


@pytest.fixture
def sample_circuit(sample_circuit_metadata):
    """
    A sample circuit for testing submit_circuit
    """
    return Circuit(
        name='The circuit',
        instructions=[
            Instruction(
                name='cz',
                qubits=(
                    'Qubit A',
                    'Qubit B',
                ),
                args={},
            ),
            Instruction(
                name='phased_rx',
                implementation='drag_gaussian',
                qubits=('Qubit A',),
                args={'phase_t': 0.7, 'angle_t': 0.25},
            ),
            Instruction(
                name='prx',
                qubits=('Qubit A',),
                args={'phase_t': 0.3, 'angle_t': -0.2},
            ),
            Instruction(name='measurement', qubits=('Qubit A',), args={'key': 'A'}),
            Instruction(name='measure', qubits=('Qubit B',), args={'key': 'B'}),
        ],
        metadata=sample_circuit_metadata,
    )


@pytest.fixture
def sample_circuit_with_raw_instructions(sample_circuit_metadata):
    """
    A sample circuit with instructions defined by dicts for testing if
    we do not break pydantic parsing logic with custom validators
    """
    return Circuit(
        name='The circuit',
        instructions=[
            {
                'name': 'cz',
                'qubits': (
                    'Qubit A',
                    'Qubit B',
                ),
                'args': {},
            },
            {
                'name': 'phased_rx',
                'implementation': 'drag_gaussian',
                'qubits': ('Qubit A',),
                'args': {'phase_t': 0.7, 'angle_t': 0.25},
            },
            {
                'name': 'prx',
                'qubits': ('Qubit A',),
                'args': {'phase_t': 0.3, 'angle_t': -0.2},
            },
            {'name': 'measurement', 'qubits': ('Qubit A',), 'args': {'key': 'A'}},
            {'name': 'measure', 'qubits': ('Qubit B',), 'args': {'key': 'B'}},
        ],
        metadata=sample_circuit_metadata,
    )


@pytest.fixture()
def minimal_run_request(sample_circuit) -> RunRequest:
    return RunRequest(
        circuits=[sample_circuit],
        shots=10,
    )


@pytest.fixture()
def run_request_with_heralding(sample_circuit) -> RunRequest:
    return RunRequest(
        circuits=[sample_circuit],
        shots=10,
        heralding_mode=HeraldingMode.ZEROS,
    )


@pytest.fixture()
def run_request_with_custom_settings(sample_circuit, settings_dict) -> RunRequest:
    return RunRequest(
        circuits=[sample_circuit],
        shots=10,
        qubit_mapping=[
            SingleQubitMapping(logical_name='Qubit A', physical_name='QB1'),
            SingleQubitMapping(logical_name='Qubit B', physical_name='QB2'),
        ],
        custom_settings=settings_dict,
        heralding_mode=HeraldingMode.NONE,
    )


@pytest.fixture()
def run_request_without_qubit_mapping(sample_circuit) -> RunRequest:
    return RunRequest(
        circuits=[sample_circuit],
        shots=10,
        heralding_mode=HeraldingMode.NONE,
    )


@pytest.fixture()
def run_request_with_invalid_qubit_mapping(sample_circuit) -> RunRequest:
    return RunRequest(
        circuits=[sample_circuit],
        shots=10,
        qubit_mapping=[
            SingleQubitMapping(logical_name='Qubit A', physical_name='QB1'),
            SingleQubitMapping(logical_name='Qubit B', physical_name='QB1'),
        ],
        heralding_mode=HeraldingMode.NONE,
    )


@pytest.fixture()
def run_request_with_incomplete_qubit_mapping(sample_circuit) -> RunRequest:
    return RunRequest(
        circuits=[sample_circuit],
        shots=10,
        qubit_mapping=[
            SingleQubitMapping(logical_name='Qubit A', physical_name='QB1'),
        ],
        heralding_mode=HeraldingMode.NONE,
    )


@pytest.fixture()
def run_request_with_calibration_set_id(sample_circuit, sample_calibration_set_id) -> RunRequest:
    return RunRequest(
        circuits=[sample_circuit],
        shots=10,
        qubit_mapping=[
            SingleQubitMapping(logical_name='Qubit A', physical_name='QB1'),
            SingleQubitMapping(logical_name='Qubit B', physical_name='QB2'),
        ],
        calibration_set_id=sample_calibration_set_id,
        heralding_mode=HeraldingMode.NONE,
    )


@pytest.fixture()
def run_request_with_duration_check_disabled(sample_circuit) -> RunRequest:
    return RunRequest(
        circuits=[sample_circuit],
        shots=10,
        qubit_mapping=[
            SingleQubitMapping(logical_name='Qubit A', physical_name='QB1'),
            SingleQubitMapping(logical_name='Qubit B', physical_name='QB2'),
        ],
        circuit_duration_check=False,
        heralding_mode=HeraldingMode.NONE,
    )


@pytest.fixture()
def pending_compilation_job_result(sample_circuit):
    return MockJsonResponse(
        200, {'status': 'pending compilation', 'metadata': {'request': {'shots': 10, 'circuits': [sample_circuit]}}}
    )


@pytest.fixture()
def pending_execution_job_result(sample_circuit):
    return MockJsonResponse(
        200, {'status': 'pending execution', 'metadata': {'request': {'shots': 10, 'circuits': [sample_circuit]}}}
    )


@pytest.fixture()
def ready_job_result(sample_circuit, sample_calibration_set_id):
    return MockJsonResponse(
        200,
        {
            'status': 'ready',
            'measurements': [{'result': [[1, 0, 1, 1], [1, 0, 0, 1], [1, 0, 1, 1], [1, 0, 1, 1]]}],
            'metadata': {
                'calibration_set_id': str(sample_calibration_set_id),
                'request': {
                    'shots': 42,
                    'circuits': [sample_circuit],
                    'calibration_set_id': str(sample_calibration_set_id),
                },
                'timestamps': {
                    'job_start': '0.0',
                    'job_end': '1.1',
                },
            },
        },
    )


@pytest.fixture()
def job_result_with_warnings(sample_circuit, sample_calibration_set_id):
    return MockJsonResponse(
        200,
        {
            'status': 'ready',
            'metadata': {
                'calibration_set_id': str(sample_calibration_set_id),
                'request': {
                    'shots': 42,
                    'circuits': [sample_circuit],
                    'calibration_set_id': str(sample_calibration_set_id),
                },
                'timestamps': {
                    'job_start': '0.0',
                    'job_end': '1.1',
                },
            },
            'warnings': ['This is a warning message'],
        },
    )


@pytest.fixture()
def pending_compilation_status():
    return MockJsonResponse(200, {'status': 'pending compilation'})


@pytest.fixture()
def pending_execution_status():
    return MockJsonResponse(200, {'status': 'pending execution'})


@pytest.fixture()
def ready_status():
    return MockJsonResponse(200, {'status': 'ready'})


@pytest.fixture
def sample_quantum_architecture():
    return {
        'quantum_architecture': {
            'name': 'hercules',
            'qubits': ['QB1', 'QB2'],
            'qubit_connectivity': [['QB1', 'QB2']],
            'operations': ['phased_rx', 'CZ'],
        }
    }


class MockTextResponse:
    def __init__(self, status_code: int, text: str, history: Optional[list[Response]] = None):
        self.status_code = status_code
        self.text = text
        self.history = history

    def json(self):
        return json.loads(self.text)

    def raise_for_status(self):
        if 400 <= self.status_code < 600:
            raise HTTPError('')


@pytest.fixture()
def not_valid_json_response() -> MockTextResponse:
    return MockTextResponse(200, 'not a valid json')


class MockJsonResponse:
    def __init__(self, status_code: int, json_data: dict, history: Optional[list[Response]] = None):
        self.status_code = status_code
        self.json_data = json_data
        self.history = history

    @property
    def text(self):
        return json.dumps(self.json_data)

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if 400 <= self.status_code < 600:
            raise HTTPError(f'{self.status_code}', response=self)


@pytest.fixture()
def submit_success(existing_run_id) -> MockJsonResponse:
    return MockJsonResponse(201, {'id': str(existing_run_id)})


@pytest.fixture()
def submit_failed_auth() -> MockJsonResponse:
    return MockJsonResponse(401, {'detail': 'unauthorized'})


@pytest.fixture()
def quantum_architecture_success(sample_quantum_architecture) -> MockJsonResponse:
    return MockJsonResponse(200, sample_quantum_architecture)


@pytest.fixture()
def abort_job_success() -> MockJsonResponse:
    return MockJsonResponse(200, {})


@pytest.fixture()
def abort_job_failed() -> MockJsonResponse:
    return MockJsonResponse(400, {'detail': 'failed to abort job'})


def prepare_tokens(
    access_token_lifetime: int,
    refresh_token_lifetime: int,
    previous_refresh_token: Optional[str] = None,
    status_code: int = 200,
    **credentials,
) -> dict[str, str]:
    """Prepare tokens and set them to be returned for a token request.

    Args:
        access_token_lifetime: seconds from current time to access token expire time
        refresh_token_lifetime: seconds from current time to refresh token expire time
        previous_refresh_token: refresh token to be used in refresh request
        status_code: status code to return for token request
        credentials: dict containing auth_server_url, username and password

    Returns:
         Prepared tokens as a dict.
    """
    if previous_refresh_token is None:
        request_data = AuthRequest(
            client_id=AUTH_CLIENT_ID,
            grant_type=GrantType.PASSWORD,
            username=credentials['username'],
            password=credentials['password'],
        )
    else:
        request_data = AuthRequest(
            client_id=AUTH_CLIENT_ID, grant_type=GrantType.REFRESH, refresh_token=previous_refresh_token
        )

    tokens = {
        'access_token': make_token('Bearer', access_token_lifetime),
        'refresh_token': make_token('Refresh', refresh_token_lifetime),
    }
    when(requests).post(
        f'{credentials["auth_server_url"]}/realms/{AUTH_REALM}/protocol/openid-connect/token',
        data=request_data.model_dump(exclude_none=True),
        timeout=REQUESTS_TIMEOUT,
    ).thenReturn(MockJsonResponse(status_code, tokens))

    return tokens


def make_token(token_type: str, lifetime: int) -> str:
    """Encode given token type and expire time as a token.

    Args:
        token_type: 'Bearer' for access tokens, 'Refresh' for refresh tokens
        lifetime: seconds from current time to token's expire time

    Returns:
        Encoded token
    """
    empty = b64encode('{}'.encode('utf-8')).decode('utf-8')
    body = f'{{ "typ": "{token_type}", "exp": {int(time.time()) + lifetime} }}'
    body = b64encode(body.encode('utf-8')).decode('utf-8')
    return f'{empty}.{body}.{empty}'


def expect_logout(auth_server_url: str, refresh_token: str, timeout: float = ANY(float)):
    """Prepare for logout request.

    Args:
        auth_server_url: base URL of the authentication server
        refresh_token: refresh token expected to be used in the request
        timeout: expected timeout value, if any
    """
    request_data = AuthRequest(client_id=AUTH_CLIENT_ID, refresh_token=refresh_token)
    expect(requests, times=1).post(
        f'{auth_server_url}/realms/{AUTH_REALM}/protocol/openid-connect/logout',
        data=request_data.model_dump(exclude_none=True),
        timeout=timeout,
    ).thenReturn(mock({'status_code': 204, 'text': '{}'}))


def post_jobs_args(
    run_request: Optional[RunRequest] = None,
    user_agent: Optional[str] = None,
    access_token: Optional[str] = None,
) -> dict[str, Any]:
    """Returns expected kwargs of POST /jobs request"""
    headers = {'Expect': '100-Continue'} if run_request is not None else {}
    signature = f'{platform.platform(terse=True)}, python {platform.python_version()}, {DIST_NAME} {__version__}'
    headers['User-Agent'] = signature if user_agent is None else user_agent
    if access_token is not None:
        headers['Authorization'] = f'Bearer {access_token}'
    if run_request is None:
        return {'headers': headers, 'timeout': REQUESTS_TIMEOUT}
    return {
        'json': json.loads(run_request.model_dump_json(exclude_none=True)),
        'headers': headers,
        'timeout': REQUESTS_TIMEOUT,
    }


def get_jobs_args(
    user_agent: Optional[str] = None,
    access_token: Optional[str] = None,
) -> dict[str, Any]:
    """Returns expected kwargs of POST /jobs request"""
    headers = {}
    signature = f'{platform.platform(terse=True)}, python {platform.python_version()}, {DIST_NAME} {__version__}'
    headers['User-Agent'] = signature if user_agent is None else user_agent
    if access_token is not None:
        headers['Authorization'] = f'Bearer {access_token}'
    return {
        'headers': headers if headers else None,
        'timeout': REQUESTS_TIMEOUT,
    }


def submit_circuits_args(run_request: RunRequest) -> dict[str, Any]:
    """Return args to be used with submit_circuits to generate the expected RunRequest"""
    qm_dict = None
    if run_request.qubit_mapping is not None:
        qm_dict = {qm.logical_name: qm.physical_name for qm in run_request.qubit_mapping}
    return {
        'circuits': run_request.circuits,
        'qubit_mapping': qm_dict,
        'custom_settings': run_request.custom_settings,
        'calibration_set_id': run_request.calibration_set_id,
        'shots': run_request.shots,
        'circuit_duration_check': run_request.circuit_duration_check,
        'heralding_mode': run_request.heralding_mode,
    }
