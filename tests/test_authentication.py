# Copyright 2022 IQM client developers
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
"""Tests for user authentication and token management in IQM client.
"""

import builtins
import io
import json
import os
from time import sleep

from mockito import unstub, when
import pytest
import requests

from iqm_client import Circuit, ClientAuthenticationError, ClientConfigurationError, Credentials, IQMClient
from iqm_client.iqm_client import _time_left_seconds
from tests.conftest import (
    MockJsonResponse,
    expect_logout,
    expect_status_request,
    expect_submit_circuits_request,
    make_token,
    prepare_tokens,
)


def test_get_initial_tokens_with_credentials_from_arguments(base_url, credentials):
    """
    Tests that if the client is initialized with credentials, they are used correctly
    """
    tokens = prepare_tokens(300, 3600, **credentials)
    expected_credentials = Credentials(
        access_token=tokens['access_token'], refresh_token=tokens['refresh_token'], **credentials
    )
    client = IQMClient(base_url, **credentials)
    assert client._credentials == expected_credentials
    unstub()


def test_get_initial_tokens_with_credentials_from_env_variables(base_url, credentials, monkeypatch):
    """
    Tests that credentials are read from environment variables if they are not given as arguments
    """
    tokens = prepare_tokens(300, 3600, **credentials)
    expected_credentials = Credentials(
        access_token=tokens['access_token'], refresh_token=tokens['refresh_token'], **credentials
    )
    monkeypatch.setenv('IQM_AUTH_SERVER', credentials['auth_server_url'])
    monkeypatch.setenv('IQM_AUTH_USERNAME', credentials['username'])
    monkeypatch.setenv('IQM_AUTH_PASSWORD', credentials['password'])
    client = IQMClient(base_url)
    assert client._credentials == expected_credentials
    unstub()


def test_get_initial_tokens_with_incomplete_credentials_from_env_variables(base_url, credentials, monkeypatch):
    """
    Tests configuration error is reported if IQM_AUTH_SERVER is set, but no credentials provided
    """
    monkeypatch.setenv('IQM_AUTH_SERVER', credentials['auth_server_url'])
    with pytest.raises(ClientConfigurationError) as e:
        IQMClient(base_url)
    assert str(e.value) == 'Auth server URL is set but no username or password'
    unstub()


def test_add_authorization_header_when_credentials_are_provided(base_url, credentials):
    """
    Tests that ``get_run`` requests are sent with Authorization header when credentials are provided
    """
    tokens = prepare_tokens(300, 3600, **credentials)
    job_id = expect_status_request(base_url, tokens['access_token'])
    client = IQMClient(base_url, **credentials)
    result = client.get_run(job_id)
    assert result.status == 'pending'
    unstub()


def test_add_authorization_header_on_submit_circuits_when_credentials_are_provided(
    base_url, credentials, sample_circuit
):
    """
    Tests that ``submit_circuits`` requests are sent with Authorization header when credentials are provided
    """
    tokens = prepare_tokens(300, 3600, **credentials)
    expected_job_id = expect_submit_circuits_request(base_url, tokens['access_token'], response_status=200)
    client = IQMClient(base_url, **credentials)
    created_job_id = client.submit_circuits(
        circuits=[Circuit.parse_obj(sample_circuit)],
        qubit_mapping={'Qubit A': 'QB1', 'Qubit B': 'QB2'},
        shots=1000,
    )
    assert expected_job_id == created_job_id
    unstub()


def test_submit_circuits_raises_when_auth_failed(base_url, credentials, sample_circuit):
    """
    Tests that ``submit_circuits`` raises ClientAuthenticationError when authentication fails
    """
    tokens = prepare_tokens(300, 3600, **credentials)
    expect_submit_circuits_request(base_url, tokens['access_token'], response_status=401)
    client = IQMClient(base_url, **credentials)
    with pytest.raises(ClientAuthenticationError) as e:
        client.submit_circuits(
            circuits=[Circuit.parse_obj(sample_circuit)],
            qubit_mapping={'Qubit A': 'QB1', 'Qubit B': 'QB2'},
            shots=1000,
        )
    assert str(e.value).startswith('Authentication failed')
    unstub()


def test_add_authorization_header_when_external_token_is_provided(base_url, tokens_dict):
    """
    Tests that requests are sent with Authorization header when external token is provided
    """
    tokens_path = os.path.dirname(os.path.realpath(__file__)) + '/resources/tokens.json'
    job_id = expect_status_request(base_url, tokens_dict['access_token'])
    client = IQMClient(base_url, tokens_file=tokens_path)
    result = client.get_run(job_id)
    assert result.status == 'pending'
    unstub()


def test_no_authorization_header_when_credentials_are_not_provided(base_url):
    """
    Tests that requests are sent without Authorization header when no credentials are provided
    """
    job_id = expect_status_request(base_url, None)
    client = IQMClient(base_url)
    result = client.get_run(job_id)
    assert result.status == 'pending'
    unstub()


def test_raises_client_authentication_error_if_authentication_fails(base_url, credentials):
    """
    Tests that authentication failure raises ClientAuthenticationError
    """
    prepare_tokens(300, 3600, status_code=401, **credentials)
    with pytest.raises(ClientAuthenticationError):
        IQMClient(base_url, **credentials)
    unstub()


def test_get_quantum_architecture_raises_if_no_auth_provided(base_url):
    """Test retrieving the quantum architecture if server responded with redirect"""
    client = IQMClient(base_url)
    redirection_response = requests.Response()
    redirection_response.status_code = 302
    when(requests).get(f'{base_url}/quantum-architecture', ...).thenReturn(
        MockJsonResponse(200, 'not a valid json', [redirection_response])
    )
    with pytest.raises(ClientConfigurationError) as e:
        client.get_quantum_architecture()
    assert str(e.value) == 'Authentication is required.'


def test_get_quantum_architecture_raises_if_wrong_auth_provided(base_url):
    """Test retrieving the quantum architecture if server responded with auth error"""
    client = IQMClient(base_url)
    when(requests).get(f'{base_url}/quantum-architecture', ...).thenReturn(
        MockJsonResponse(401, {'details': 'failed to authenticate'})
    )
    with pytest.raises(ClientAuthenticationError) as e:
        client.get_quantum_architecture()
    assert str(e.value).startswith('Authentication failed')


def test_access_token_is_not_refreshed_if_it_has_not_expired(base_url, credentials):
    """
    Test that access token is not refreshed if it has not expired
    """
    tokens = prepare_tokens(300, 3600, **credentials)
    client = IQMClient(base_url, **credentials)
    assert client._credentials.access_token == tokens['access_token']

    job_id = expect_status_request(base_url, tokens['access_token'], 3)
    client.get_run(job_id)
    client.get_run(job_id)
    client.get_run(job_id)


def test_expired_access_token_is_refreshed_automatically(base_url, credentials):
    """
    Test that access token is refreshed automatically if it has expired
    """
    initial_tokens = prepare_tokens(-300, 3600, **credentials)  # expired initial access token
    refreshed_tokens = prepare_tokens(300, 4200, initial_tokens['refresh_token'], **credentials)
    job_id = expect_status_request(base_url, refreshed_tokens['access_token'])

    # Check initial access token
    client = IQMClient(base_url, **credentials)
    assert client._credentials.access_token == initial_tokens['access_token']

    # Check that assert token is refreshed
    result = client.get_run(job_id)
    assert client._credentials.access_token == refreshed_tokens['access_token']
    assert result.status == 'pending'

    unstub()


def test_start_new_session_when_refresh_token_has_expired(base_url, credentials):
    """
    Test that a new session is started automatically if refresh token has expired
    """
    initial_tokens = prepare_tokens(-3600, -300, **credentials)  # expired initial access token and refresh token

    client = IQMClient(base_url, **credentials)
    assert client._credentials.access_token == initial_tokens['access_token']
    assert client._credentials.refresh_token == initial_tokens['refresh_token']

    refreshed_tokens = prepare_tokens(300, 3600, **credentials)  # refreshed access token and refresh token
    job_id = expect_status_request(base_url, refreshed_tokens['access_token'])
    result = client.get_run(job_id)
    assert client._credentials.access_token == refreshed_tokens['access_token']
    assert result.status == 'pending'

    unstub()


def test_tokens_are_cleared_at_logout(base_url, credentials):
    """
    Tests that calling ``close`` will terminate the session and clear tokens
    """
    initial_tokens = prepare_tokens(300, 3600, **credentials)
    expect_logout(credentials['auth_server_url'], initial_tokens['refresh_token'])

    client = IQMClient(base_url, **credentials)
    assert client._credentials.access_token == initial_tokens['access_token']
    assert client._credentials.refresh_token == initial_tokens['refresh_token']

    client.close_auth_session()
    assert client._credentials.access_token is None
    assert client._credentials.refresh_token is None

    unstub()


def test_cannot_close_external_auth_session(base_url):
    """
    Tests that calling ``close_auth_session`` while initialized with an external auth session
    raises ClientAuthenticationError
    """
    tokens_path = os.path.dirname(os.path.realpath(__file__)) + '/resources/tokens.json'
    client = IQMClient(base_url, tokens_file=tokens_path)
    with pytest.raises(ClientAuthenticationError) as exc:
        client.close_auth_session()
    assert 'Unable to close externally managed auth session' == str(exc.value)


def test_logout_on_client_destruction(base_url, credentials):
    """
    Tests that client is trying to terminate the authentication session on destruction
    """
    initial_tokens = prepare_tokens(300, 3600, **credentials)
    expect_logout(credentials['auth_server_url'], initial_tokens['refresh_token'])

    client = IQMClient(base_url, **credentials)
    assert client._credentials.access_token == initial_tokens['access_token']
    assert client._credentials.refresh_token == initial_tokens['refresh_token']

    del client

    unstub()


def test_external_token_updated_if_expired(base_url):
    """
    Tests that client gets updated token from tokens file if old external token has expired
    """
    tokens_path = 'dummy_path'

    def setup_tokens_file(access_token_lifetime):
        access_token = make_token('Bearer', access_token_lifetime)
        tokens_file_contents = json.dumps({'auth_server_url': base_url + '/auth', 'access_token': access_token})
        when(builtins).open(tokens_path, 'r', encoding='utf-8').thenReturn(io.StringIO(tokens_file_contents))

    setup_tokens_file(1)
    client = IQMClient(base_url, tokens_file=tokens_path)
    sleep(2)
    setup_tokens_file(300)
    bearer_token = client._get_bearer_token()
    assert bearer_token is not None
    assert _time_left_seconds(bearer_token.removeprefix('Bearer ')) > 0
    unstub()
