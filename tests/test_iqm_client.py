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
"""Tests for the IQM client.
"""
# pylint: disable=unused-argument
import pytest
import requests
from mockito import when
from requests import HTTPError

from iqm_client.iqm_client import (Circuit, ClientConfigurationError,
                                   IQMClient, RunStatus, SingleQubitMapping)
from tests.conftest import MockJsonResponse, existing_run, missing_run


def test_submit_circuits_returns_id(mock_server, settings_dict, base_url, sample_circuit):
    """
    Tests sending a circuit
    """
    client = IQMClient(base_url, settings_dict)
    job_id = client.submit_circuits(
        qubit_mapping=[
            SingleQubitMapping(logical_name='Qubit A', physical_name='qubit_1'),
            SingleQubitMapping(logical_name='Qubit B', physical_name='qubit_2')
        ],
        circuits=[Circuit.parse_obj(sample_circuit)],
        shots=1000)
    assert job_id == existing_run


def test_submit_circuits_without_settings_returns_id(mock_server, base_url, sample_circuit):
    """
    Tests sending a circuit
    """
    client = IQMClient(base_url)
    job_id = client.submit_circuits(
        qubit_mapping=[
            SingleQubitMapping(logical_name='Qubit A', physical_name='qubit_1'),
            SingleQubitMapping(logical_name='Qubit B', physical_name='qubit_2')
        ],
        circuits=[Circuit.parse_obj(sample_circuit)],
        shots=1000)
    assert job_id == existing_run


def test_submit_circuits_without_qubit_mapping_returns_id(mock_server, settings_dict, base_url, sample_circuit):
    """
    Tests sending a circuit without qubit mapping
    """
    client = IQMClient(base_url, settings_dict)
    job_id = client.submit_circuits(
        circuits=[Circuit.parse_obj(sample_circuit)],
        shots=1000)
    assert job_id == existing_run


def test_get_run_status_and_results_for_existing_run(mock_server, base_url, settings_dict):
    """
    Tests getting the run status
    """
    client = IQMClient(base_url, settings_dict)
    assert client.get_run(existing_run).status == RunStatus.PENDING
    ready_run = client.get_run(existing_run)
    assert ready_run.status == RunStatus.READY
    assert ready_run.measurements is not None


def test_get_run_status_for_existing_run(mock_server, base_url, settings_dict):
    """
    Tests getting the run status
    """
    client = IQMClient(base_url, settings_dict)
    assert client.get_run_status(existing_run).status == RunStatus.PENDING
    ready_run = client.get_run_status(existing_run)
    assert ready_run.status == RunStatus.READY
    assert ready_run.measurements is None


def test_get_run_status_and_results_for_missing_run(mock_server, base_url, settings_dict):
    """
    Tests getting a task that was not created
    """
    client = IQMClient(base_url, settings_dict)
    with pytest.raises(HTTPError):
        assert client.get_run(missing_run)


def test_get_run_status_for_missing_run(mock_server, base_url, settings_dict):
    """
    Tests getting a task that was not created
    """
    client = IQMClient(base_url, settings_dict)
    with pytest.raises(HTTPError):
        assert client.get_run_status(missing_run)


def test_waiting_for_results(mock_server, base_url, settings_dict):
    """
    Tests waiting for results for an existing task
    """
    client = IQMClient(base_url, settings_dict)
    assert client.wait_for_results(existing_run).status == RunStatus.READY


def test_user_warning_is_emitted_when_warnings_in_response(base_url, settings_dict, capsys):
    client = IQMClient(base_url, settings_dict)
    msg = 'This is a warning msg'
    with when(requests).get(f'{base_url}/jobs/{existing_run}', headers=None).thenReturn(
            MockJsonResponse(200, {'status': 'ready', 'warnings': [msg]})
    ):
        with pytest.warns(UserWarning, match=msg):
            client.get_run(existing_run)


def test_base_url_is_invalid(settings_dict):
    invalid_base_url = 'https//example.com'
    with pytest.raises(ClientConfigurationError) as exc:
        IQMClient(invalid_base_url, settings_dict)
    assert f'The URL schema has to be http or https. Incorrect schema in URL: {invalid_base_url}' == str(exc.value)

def test_tokens_file_not_found(settings_dict):
    base_url = 'https://example.com'
    tokens_file = '/home/iqm/tokens.json'
    with pytest.raises(ClientConfigurationError) as exc:
        IQMClient(base_url, settings_dict, tokens_file = tokens_file)
    assert f'File not found: {tokens_file}' == str(exc.value)

def test_tokens_and_credentials_combo_invalid(settings_dict, credentials):
    tokens_file = '/home/iqm/tokens.json'
    base_url = 'https://example.com'
    with pytest.raises(ClientConfigurationError) as exc:
        IQMClient(base_url, settings_dict, tokens_file = tokens_file, **credentials)
    assert 'Either external token or credentials must be provided. Both were provided.' == str(exc.value)
