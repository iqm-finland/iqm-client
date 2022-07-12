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

import os

from mockito import unstub
from pytest import raises

from iqm_client.iqm_client import (ClientAuthenticationError, Credentials,
                                   IQMClient)
from tests.conftest import expect_logout, expect_status_request, prepare_tokens


def test_get_initial_tokens_with_credentials_from_arguments(base_url, credentials, settings_dict):
    """
    Tests that if the client is initialized with credentials, they are used correctly
    """
    tokens = prepare_tokens(300, 3600, **credentials)
    expected_credentials = Credentials(
        access_token=tokens['access_token'],
        refresh_token=tokens['refresh_token'],
        **credentials
    )
    client = IQMClient(base_url, settings_dict, **credentials)
    assert client._credentials == expected_credentials
    unstub()


def test_get_initial_tokens_with_credentials_from_env_variables(base_url, credentials, settings_dict, monkeypatch):
    """
    Tests that credentials are read from environment variables if they are not given as arguments
    """
    tokens = prepare_tokens(300, 3600, **credentials)
    expected_credentials = Credentials(
        access_token=tokens['access_token'],
        refresh_token=tokens['refresh_token'],
        **credentials
    )
    monkeypatch.setenv('IQM_AUTH_SERVER', credentials['auth_server_url'])
    monkeypatch.setenv('IQM_AUTH_USERNAME', credentials['username'])
    monkeypatch.setenv('IQM_AUTH_PASSWORD', credentials['password'])
    client = IQMClient(base_url, settings_dict)
    assert client._credentials == expected_credentials
    unstub()


def test_add_authorization_header_when_credentials_are_provided(base_url, credentials, settings_dict):
    """
    Tests that requests are sent with Authorization header when credentials are provided
    """
    tokens = prepare_tokens(300, 3600, **credentials)
    job_id = expect_status_request(base_url, tokens['access_token'])
    client = IQMClient(base_url, settings_dict, **credentials)
    result = client.get_run(job_id)
    assert result.status == 'pending'
    unstub()


def test_add_authorization_header_when_external_token_is_provided(base_url, settings_dict, tokens_dict):
    """
    Tests that requests are sent with Authorization header when credentials are provided
    """
    tokens_path = os.path.dirname(os.path.realpath(__file__)) + '/resources/tokens.json'
    job_id = expect_status_request(base_url, tokens_dict['access_token'])
    client = IQMClient(base_url, settings_dict, tokens_file = tokens_path)
    result = client.get_run(job_id)
    assert result.status == 'pending'
    unstub()


def test_no_authorization_header_when_credentials_are_not_provided(base_url, settings_dict):
    """
    Tests that requests are sent without Authorization header when no credentials are provided
    """
    job_id = expect_status_request(base_url, None)
    client = IQMClient(base_url, settings_dict)
    result = client.get_run(job_id)
    assert result.status == 'pending'
    unstub()


def test_raises_client_authentication_error_if_authentication_fails(base_url, credentials, settings_dict):
    """
    Tests that authentication failure raises ClientAuthenticationError
    """
    prepare_tokens(300, 3600, status_code=401, **credentials)
    with raises(ClientAuthenticationError):
        IQMClient(base_url, settings_dict, **credentials)
    unstub()


def test_access_token_is_not_refreshed_if_it_has_not_expired(base_url, credentials, settings_dict):
    """
    Test that access token is not refreshed if it has not expired
    """
    tokens = prepare_tokens(300, 3600, **credentials)
    client = IQMClient(base_url, settings_dict, **credentials)
    assert client._credentials.access_token == tokens['access_token']

    job_id = expect_status_request(base_url, tokens['access_token'], 3)
    client.get_run(job_id)
    client.get_run(job_id)
    client.get_run(job_id)


def test_expired_access_token_is_refreshed_automatically(base_url, credentials, settings_dict):
    """
    Test that access token is refreshed automatically if it has expired
    """
    initial_tokens = prepare_tokens(-300, 3600, **credentials)  # expired initial access token
    refreshed_tokens = prepare_tokens(300, 4200, initial_tokens['refresh_token'], **credentials)
    job_id = expect_status_request(base_url, refreshed_tokens['access_token'])

    # Check initial access token
    client = IQMClient(base_url, settings_dict, **credentials)
    assert client._credentials.access_token == initial_tokens['access_token']

    # Check that assert token is refreshed
    result = client.get_run(job_id)
    assert client._credentials.access_token == refreshed_tokens['access_token']
    assert result.status == 'pending'

    unstub()


def test_start_new_session_when_refresh_token_has_expired(base_url, credentials, settings_dict):
    """
    Test that a new session is started automatically if refresh token has expired
    """
    initial_tokens = prepare_tokens(-3600, -300, **credentials)  # expired initial access token and refresh token

    client = IQMClient(base_url, settings_dict, **credentials)
    assert client._credentials.access_token == initial_tokens['access_token']
    assert client._credentials.refresh_token == initial_tokens['refresh_token']

    refreshed_tokens = prepare_tokens(300, 3600, **credentials)  # refreshed access token and refresh token
    job_id = expect_status_request(base_url, refreshed_tokens['access_token'])
    result = client.get_run(job_id)
    assert client._credentials.access_token == refreshed_tokens['access_token']
    assert result.status == 'pending'

    unstub()


def test_tokens_are_cleared_at_logout(base_url, credentials, settings_dict):
    """
    Tests that calling ``close`` will terminate the session and clear tokens
    """
    initial_tokens = prepare_tokens(300, 3600, **credentials)
    expect_logout(credentials['auth_server_url'], initial_tokens['refresh_token'])

    client = IQMClient(base_url, settings_dict, **credentials)
    assert client._credentials.access_token == initial_tokens['access_token']
    assert client._credentials.refresh_token == initial_tokens['refresh_token']

    client.close()
    assert client._credentials.access_token is None
    assert client._credentials.refresh_token is None

    unstub()
