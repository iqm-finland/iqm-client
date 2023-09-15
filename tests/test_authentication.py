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
from time import sleep

from mockito import expect, unstub, verifyNoUnwantedInteractions, when
import pytest
import requests

from iqm.iqm_client import ClientAuthenticationError, ClientConfigurationError, Credentials, IQMClient
from iqm.iqm_client.iqm_client import _time_left_seconds
from tests.conftest import (
    MockJsonResponse,
    expect_logout,
    get_jobs_args,
    make_token,
    post_jobs_args,
    prepare_tokens,
    submit_circuits_args,
)


def test_get_initial_tokens_with_credentials_from_arguments(credentials):
    """
    Tests that if the client is initialized with credentials, they are used correctly
    """
    tokens = prepare_tokens(300, 3600, **credentials)
    expected_credentials = Credentials(
        access_token=tokens['access_token'], refresh_token=tokens['refresh_token'], **credentials
    )

    client = IQMClient('https://example.com', **credentials)
    assert client._credentials == expected_credentials

    unstub()


def test_get_initial_tokens_with_credentials_from_env_variables(credentials, monkeypatch):
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

    client = IQMClient(url='https://example.com')
    assert client._credentials == expected_credentials
    unstub()


def test_get_initial_tokens_with_incomplete_credentials_from_env_variables(credentials, monkeypatch):
    """
    Tests configuration error is reported if IQM_AUTH_SERVER is set, but no credentials provided
    """
    monkeypatch.setenv('IQM_AUTH_SERVER', credentials['auth_server_url'])
    with pytest.raises(ClientConfigurationError) as e:
        IQMClient('https://example.com')
    assert str(e.value) == 'Auth server URL is set but no username or password'
    unstub()


def test_add_authorization_header_when_credentials_are_provided(
    client_with_credentials, existing_job_url, existing_run_id, pending_compilation_job_result
):
    """
    Tests that ``get_run`` requests are sent with Authorization header when credentials are provided
    """
    expect(requests, times=1).get(
        existing_job_url, **post_jobs_args(access_token=client_with_credentials._credentials.access_token)
    ).thenReturn(pending_compilation_job_result)

    result = client_with_credentials.get_run(existing_run_id)
    assert result.status == 'pending compilation'

    verifyNoUnwantedInteractions()
    unstub()


def test_add_authorization_header_on_submit_circuits_when_credentials_are_provided(
    client_with_credentials, jobs_url, minimal_run_request, existing_run_id, submit_success
):
    """
    Tests that ``submit_circuits`` requests are sent with Authorization header when credentials are provided
    """
    expect(requests, times=1).post(
        jobs_url, **post_jobs_args(minimal_run_request, access_token=client_with_credentials._credentials.access_token)
    ).thenReturn(submit_success)

    assert existing_run_id == client_with_credentials.submit_circuits(**submit_circuits_args(minimal_run_request))

    verifyNoUnwantedInteractions()
    unstub()


def test_submit_circuits_raises_when_auth_failed(
    client_with_credentials, jobs_url, minimal_run_request, submit_failed_auth
):
    """
    Tests that ``submit_circuits`` raises ClientAuthenticationError when authentication fails
    """
    expect(requests, times=1).post(
        jobs_url, **post_jobs_args(minimal_run_request, access_token=client_with_credentials._credentials.access_token)
    ).thenReturn(submit_failed_auth)

    with pytest.raises(ClientAuthenticationError) as e:
        client_with_credentials.submit_circuits(**submit_circuits_args(minimal_run_request))
    assert str(e.value).startswith('Authentication failed')

    verifyNoUnwantedInteractions()
    unstub()


def test_add_authorization_header_on_get_jobs_when_external_token_is_provided(
    client_with_external_token, existing_job_url, tokens_dict, existing_run_id, pending_execution_job_result
):
    """
    Tests that get jobs requests are sent with Authorization header when external token is provided
    """
    expect(requests, times=1).get(
        existing_job_url, **get_jobs_args(access_token=tokens_dict['access_token'])
    ).thenReturn(pending_execution_job_result)

    result = client_with_external_token.get_run(existing_run_id)
    assert result.status == 'pending execution'

    verifyNoUnwantedInteractions()
    unstub()


def test_no_authorization_header_on_get_jobs_when_credentials_are_not_provided(
    sample_client, existing_job_url, existing_run_id, pending_execution_job_result
):
    """
    Tests that get jobs requests are sent without Authorization header when no credentials are provided
    """
    expect(requests, times=1).get(existing_job_url, **get_jobs_args(access_token=None)).thenReturn(
        pending_execution_job_result
    )

    result = sample_client.get_run(existing_run_id)
    assert result.status == 'pending execution'

    verifyNoUnwantedInteractions()
    unstub()


def test_raises_client_authentication_error_if_authentication_fails(base_url, credentials):
    """
    Tests that authentication failure raises ClientAuthenticationError
    """
    prepare_tokens(300, 3600, status_code=401, **credentials)
    with pytest.raises(ClientAuthenticationError) as e:
        IQMClient(base_url, **credentials)
    assert str(e.value).startswith('Failed to update tokens')

    verifyNoUnwantedInteractions()
    unstub()


def test_get_quantum_architecture_raises_if_no_auth_provided(sample_client, quantum_architecture_url):
    """Test retrieving the quantum architecture if server responded with redirect"""
    redirection_response = requests.Response()
    redirection_response.status_code = 302

    expect(requests, times=1).get(quantum_architecture_url, **get_jobs_args(access_token=None)).thenReturn(
        MockJsonResponse(401, {'detail': 'unauthorized'}, [redirection_response])
    )

    with pytest.raises(ClientConfigurationError) as e:
        sample_client.get_quantum_architecture()
    assert str(e.value) == 'Authentication is required.'

    verifyNoUnwantedInteractions()
    unstub()


def test_get_quantum_architecture_raises_if_wrong_auth_provided(client_with_credentials, quantum_architecture_url):
    """Test retrieving the quantum architecture if server responded with auth error"""
    expect(requests, times=1).get(
        quantum_architecture_url, **get_jobs_args(access_token=client_with_credentials._credentials.access_token)
    ).thenReturn(MockJsonResponse(401, {'detail': 'unauthorized'}))

    with pytest.raises(ClientAuthenticationError) as e:
        client_with_credentials.get_quantum_architecture()
    assert str(e.value).startswith('Authentication failed')

    verifyNoUnwantedInteractions()
    unstub()


def test_access_token_is_not_refreshed_if_it_has_not_expired(
    client_with_credentials, credentials, existing_job_url, existing_run_id, pending_execution_job_result
):
    """
    Test that access token is not refreshed if it has not expired
    """
    tokens = prepare_tokens(300, 3600, **credentials)
    assert client_with_credentials._credentials.access_token == tokens['access_token']

    expect(requests, times=3).get(
        existing_job_url, **get_jobs_args(access_token=client_with_credentials._credentials.access_token)
    ).thenReturn(pending_execution_job_result)

    client_with_credentials.get_run(existing_run_id)
    client_with_credentials.get_run(existing_run_id)
    client_with_credentials.get_run(existing_run_id)

    verifyNoUnwantedInteractions()
    unstub()


def test_expired_access_token_is_refreshed_automatically(
    client_with_credentials, credentials, existing_job_url, existing_run_id, pending_execution_job_result
):
    """
    Test that access token is refreshed automatically if it has expired
    """
    # Provide client with an expired access token
    client_with_credentials._credentials.access_token = make_token('Bearer', -300)
    client_with_credentials._credentials.refresh_token = make_token('Refresh', 4200)

    # Prepare for token refresh request
    refreshed_tokens = prepare_tokens(300, 4200, client_with_credentials._credentials.refresh_token, **credentials)

    # Expect get jobs request with refreshed token
    expect(requests, times=1).get(
        existing_job_url, **get_jobs_args(access_token=refreshed_tokens['access_token'])
    ).thenReturn(pending_execution_job_result)

    # Client should refresh tokens for get jobs request
    result = client_with_credentials.get_run(existing_run_id)
    assert result.status == 'pending execution'

    # Verify that access token has been refreshed
    assert client_with_credentials._credentials.access_token == refreshed_tokens['access_token']

    verifyNoUnwantedInteractions()
    unstub()


def test_start_new_session_when_refresh_token_has_expired(
    client_with_credentials, credentials, existing_job_url, existing_run_id, pending_execution_job_result
):
    """
    Test that a new session is started automatically if refresh token has expired
    """
    # Provide client with an expired tokens
    client_with_credentials._credentials.access_token = make_token('Bearer', -300)
    client_with_credentials._credentials.refresh_token = make_token('Refresh', -300)

    # Prepare for new session start instead of token refresh request
    refreshed_tokens = prepare_tokens(300, 3600, **credentials)

    # Expect get jobs request with refreshed token
    expect(requests, times=1).get(
        existing_job_url, **get_jobs_args(access_token=refreshed_tokens['access_token'])
    ).thenReturn(pending_execution_job_result)

    # Client should refresh tokens for get jobs request
    result = client_with_credentials.get_run(existing_run_id)
    assert result.status == 'pending execution'

    assert client_with_credentials._credentials.access_token == refreshed_tokens['access_token']
    assert client_with_credentials._credentials.refresh_token == refreshed_tokens['refresh_token']

    verifyNoUnwantedInteractions()
    unstub()


def test_tokens_are_cleared_at_logout(client_with_credentials, credentials):
    """
    Tests that calling ``close`` will terminate the session and clear tokens
    """
    expect_logout(credentials['auth_server_url'], client_with_credentials._credentials.refresh_token)

    client_with_credentials.close_auth_session()
    assert client_with_credentials._credentials.access_token is None
    assert client_with_credentials._credentials.refresh_token is None

    verifyNoUnwantedInteractions()
    unstub()


def test_cannot_close_external_auth_session(client_with_external_token):
    """
    Tests that calling ``close_auth_session`` while initialized with an external auth session
    raises ClientAuthenticationError
    """
    with pytest.raises(ClientAuthenticationError) as e:
        client_with_external_token.close_auth_session()
    assert 'Unable to close externally managed auth session' == str(e.value)


def test_logout_on_client_destruction(base_url, credentials):
    """
    Tests that client is trying to terminate the authentication session on destruction
    """
    prepare_tokens(300, 300, **credentials)
    client = IQMClient(base_url, **credentials)

    expect_logout(credentials['auth_server_url'], client._credentials.refresh_token)
    del client

    verifyNoUnwantedInteractions()
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
