# Copyright 2021 IQM client developers
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
"""Tests for the IQM client.
"""
# pylint: disable=unused-argument
import json

import pytest
import requests
from mockito import mock, when
from requests import HTTPError

from iqm_client.iqm_client import (Circuit, IQMClient, RunStatus,
                                   SingleQubitMapping, ClientConfigurationError)
from tests.conftest import existing_run, missing_run


def test_submit_circuit_returns_id(mock_server, settings_dict, base_url):
    """
    Tests sending a circuit
    """
    client = IQMClient(base_url, settings_dict)
    run_id = client.submit_circuit(
        qubit_mapping=[
            SingleQubitMapping(logical_name='Qubit A', physical_name='qubit_1'),
            SingleQubitMapping(logical_name='Qubit B', physical_name='qubit_2')
        ],
        circuit=Circuit.parse_obj(
            {
                'name': 'The circuit',
                'instructions': [
                    {
                        'name': 'cz',
                        'qubits': [
                            'Qubit A',
                            'Qubit B'
                        ],
                        'args': {}
                    },
                    {
                        'name': 'phased_rx',
                        'qubits': [
                            'Qubit A'
                        ],
                        'args': {
                            'phase_t': 1.22,
                            'angle_t': {
                                'expr': '{{alpha}}/2'
                            }
                        }
                    },
                    {
                        'name': 'measurement',
                        'qubits': [
                            'Qubit A'
                        ],
                        'args': {
                            'output_label': 'A'
                        }
                    }
                ]
            }),
        shots=1000)
    assert run_id == existing_run


def test_get_run_status_for_existing_run(mock_server, base_url, settings_dict):
    """
    Tests getting the run status
    """
    client = IQMClient(base_url, settings_dict)
    assert client.get_run(existing_run).status == RunStatus.PENDING
    assert client.get_run(existing_run).status == RunStatus.READY


def test_get_run_status_for_missing_run(mock_server, base_url, settings_dict):
    """
    Tests getting a task that was not created
    """
    client = IQMClient(base_url, settings_dict)
    with pytest.raises(HTTPError):
        assert client.get_run(missing_run)


def test_waiting_for_results(mock_server, base_url, settings_dict):
    """
    Tests waiting for results for an existing task
    """
    client = IQMClient(base_url, settings_dict)
    assert client.wait_for_results(existing_run).status == RunStatus.READY


def test_credentials_passed_to_server_from_arguments(base_url, settings_dict):
    """
    Tests that if the client is initialized with credentials, they are passed to the server correctly.
    """
    fake_username = 'a user'
    fake_api_key = 'an api key'
    client = IQMClient(base_url, settings_dict, username=fake_username, api_key=fake_api_key)
    with when(requests).get(f'{base_url}/circuit/run/{existing_run}', auth=(fake_username, fake_api_key))\
            .thenReturn(mock({'status_code': 200, 'text': json.dumps({'status': 'pending'})})):
        client.get_run(existing_run)


def test_credentials_passed_to_server_from_env_variables(base_url, settings_dict, monkeypatch):
    """
    Tests that credentials are read from environment variables
    """
    fake_username = 'fake username'
    fake_api_key = 'fake key'
    monkeypatch.setenv('IQM_SERVER_USERNAME', fake_username)
    monkeypatch.setenv('IQM_SERVER_API_KEY', fake_api_key)
    client = IQMClient(base_url, settings_dict)
    with when(requests).get(f'{base_url}/circuit/run/{existing_run}', auth=(fake_username, fake_api_key))\
            .thenReturn(mock({'status_code': 200, 'text': json.dumps({'status': 'pending'})})):
        client.get_run(existing_run)


def test_user_warning_is_emitted_when_warnings_in_response(base_url, settings_dict, capsys):
    client = IQMClient(base_url, settings_dict)
    msg = 'This is a warning msg'
    with when(requests).get(f'{base_url}/circuit/run/{existing_run}', auth=None) \
            .thenReturn(mock({'status_code': 200, 'text': json.dumps({'status': 'ready', 'warnings': [msg]})})):
        with pytest.warns(UserWarning, match=msg):
            client.get_run(existing_run)


def test_base_url_is_invalid(settings_dict):
    invalid_base_url = 'https//example.com'
    with pytest.raises(ClientConfigurationError) as exc:
        IQMClient(invalid_base_url, settings_dict)
    assert f'The URL schema has to be http or https. Incorrect schema in URL: {invalid_base_url}' == str(exc.value)
