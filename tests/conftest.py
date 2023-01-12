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
import time
from typing import Optional
from uuid import UUID, uuid4

from mockito import ANY, expect, mock, unstub, when
import pytest
import requests
from requests import HTTPError, Response

from iqm_client import AUTH_CLIENT_ID, AUTH_REALM, AuthRequest, GrantType

REQUESTS_TIMEOUT = 60

calibration_set_id_value = UUID('9ddb9586-8f27-49a9-90ed-41086b47f6bd')
existing_run = UUID('3c3fcda3-e860-46bf-92a4-bcc59fa76ce9')
missing_run = UUID('059e4186-50a3-4e6c-ba1f-37fe6afbdfc2')


@pytest.fixture()
def base_url():
    return 'https://example.com'


@pytest.fixture()
def credentials():
    return {
        'auth_server_url': 'some_auth_server',
        'username': 'some_username',
        'password': 'some_password',
    }


@pytest.fixture(scope='function')
def mock_server(base_url, sample_circuit):
    """
    Runs mocking separately for each test
    """
    generate_server_stubs(base_url, sample_circuit)
    yield  # running test function
    unstub()


@pytest.fixture
def settings_dict():
    """
    Reads and parses settings file into a dictionary
    """
    settings_path = os.path.dirname(os.path.realpath(__file__)) + '/resources/settings.json'
    with open(settings_path, 'r', encoding='utf-8') as f:
        return json.loads(f.read())


@pytest.fixture()
def calibration_set_id():
    return calibration_set_id_value


@pytest.fixture
def tokens_dict():
    """
    Reads and parses tokens file into a dictionary
    """
    tokens_path = os.path.dirname(os.path.realpath(__file__)) + '/resources/tokens.json'
    with open(tokens_path, 'r', encoding='utf-8') as f:
        return json.loads(f.read())


@pytest.fixture
def sample_circuit():
    """
    A sample circuit for testing submit_circuit
    """
    return {
        'name': 'The circuit',
        'instructions': [
            {'name': 'cz', 'qubits': ['Qubit A', 'Qubit B'], 'args': {}},
            {
                'name': 'phased_rx',
                'implementation': 'drag_gaussian',
                'qubits': ['Qubit A'],
                'args': {'phase_t': 0.7, 'angle_t': 0.25},
            },
            {'name': 'measurement', 'qubits': ['Qubit A'], 'args': {'output_label': 'A'}},
        ],
        'metadata': {'experiment_type': 'test', 'qubits': (0, 1), 'values': [0.01686514, 0.05760602]},
    }


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
            raise HTTPError('')


def generate_server_stubs(base_url, sample_circuit):
    """
    Mocking some calls to the server by mocking 'requests'
    """
    when(requests).post(f'{base_url}/jobs', ...).thenReturn(MockJsonResponse(201, {'id': str(existing_run)}))

    when(requests).get(f'{base_url}/jobs/{existing_run}', ...).thenReturn(
        MockJsonResponse(
            200, {'status': 'pending', 'metadata': {'request': {'shots': 42, 'circuits': [sample_circuit]}}}
        )
    ).thenReturn(
        MockJsonResponse(
            200,
            {
                'status': 'ready',
                'measurements': [{'result': [[1, 0, 1, 1], [1, 0, 0, 1], [1, 0, 1, 1], [1, 0, 1, 1]]}],
                'metadata': {
                    'calibration_set_id': calibration_set_id_value,
                    'request': {
                        'shots': 42,
                        'circuits': [sample_circuit],
                        'calibration_set_id': calibration_set_id_value,
                    },
                },
            },
        )
    )

    when(requests).get(f'{base_url}/jobs/{existing_run}/status', ...).thenReturn(
        MockJsonResponse(200, {'status': 'pending'})
    ).thenReturn(MockJsonResponse(200, {'status': 'ready'}))

    # 'run was not created' response
    no_run_response = Response()
    no_run_response.status_code = 404
    no_run_response.reason = 'Run not found'
    when(requests).get(f'{base_url}/jobs/{missing_run}', ...).thenReturn(no_run_response)
    when(requests).get(f'{base_url}/jobs/{missing_run}/status', ...).thenReturn(no_run_response)


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
        data=request_data.dict(exclude_none=True),
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


def expect_status_request(url: str, access_token: Optional[str], times: int = 1) -> UUID:
    """Prepare for status request.

    Args:
        url: server URL for the status request
        access_token: access token to use in Authorization header
            If not set, expect request to have no Authorization header
        times: number of times the status request is expected to be made

    Returns:
        Expected job ID to be used in the request
    """
    job_id = uuid4()
    headers = None if access_token is None else {'Authorization': f'Bearer {access_token}'}
    expect(requests, times=times).get(f'{url}/jobs/{job_id}', headers=headers, timeout=REQUESTS_TIMEOUT).thenReturn(
        MockJsonResponse(200, {'status': 'pending', 'metadata': {'request': {'shots': 42, 'circuits': []}}})
    )
    return job_id


def expect_submit_circuits_request(
    url: str, access_token: Optional[str], times: int = 1, response_status: int = 200
) -> UUID:
    """Prepare for submit_circuits request.

    Args:
        url: server URL for the status request
        access_token: access token to use in Authorization header
            If not set, expect request to have no Authorization header
        times: number of times the status request is expected to be made
        response_status: status code to return in the response
    """
    job_id = uuid4()
    headers = None if access_token is None else {'Authorization': f'Bearer {access_token}', 'Expect': '100-Continue'}
    expect(requests, times=times).post(
        f'{url}/jobs', json=ANY(dict), headers=headers, timeout=REQUESTS_TIMEOUT
    ).thenReturn(MockJsonResponse(response_status, {'id': str(job_id)}))
    return job_id


def expect_logout(auth_server_url: str, refresh_token: str):
    """Prepare for logout request.

    Args:
        auth_server_url: base URL of the authentication server
        refresh_token: refresh token expected to be used in the request
    """
    request_data = AuthRequest(client_id=AUTH_CLIENT_ID, refresh_token=refresh_token)
    expect(requests, times=1).post(
        f'{auth_server_url}/realms/{AUTH_REALM}/protocol/openid-connect/logout',
        data=request_data.dict(exclude_none=True),
        timeout=REQUESTS_TIMEOUT,
    ).thenReturn(mock({'status_code': 204, 'text': '{}'}))
