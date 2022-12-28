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
from mockito import when

# pylint: disable=unused-argument
import pytest
import requests
from requests import HTTPError

from iqm_client import (
    Circuit,
    ClientConfigurationError,
    IQMClient,
    QuantumArchitectureSpecification,
    SingleQubitMapping,
    Status,
    serialize_qubit_mapping,
)
from tests.conftest import MockJsonResponse, existing_run, missing_run

REQUESTS_TIMEOUT = 60


def test_serialize_qubit_mapping():
    qubit_mapping = {'Alice': 'QB1', 'Bob': 'qubit_3', 'Charlie': 'physical 0'}
    assert serialize_qubit_mapping(qubit_mapping) == [
        SingleQubitMapping(logical_name='Alice', physical_name='QB1'),
        SingleQubitMapping(logical_name='Bob', physical_name='qubit_3'),
        SingleQubitMapping(logical_name='Charlie', physical_name='physical 0'),
    ]


def test_submit_circuits_returns_id(mock_server, base_url, sample_circuit):
    """
    Tests sending a circuit
    """
    client = IQMClient(base_url)
    job_id = client.submit_circuits(
        circuits=[Circuit.parse_obj(sample_circuit)], qubit_mapping={'Qubit A': 'QB1', 'Qubit B': 'QB2'}, shots=1000
    )
    assert job_id == existing_run


def test_submit_circuits_with_custom_settings_returns_id(mock_server, settings_dict, base_url, sample_circuit):
    """
    Tests sending a circuit
    """
    client = IQMClient(base_url)
    job_id = client.submit_circuits(
        circuits=[Circuit.parse_obj(sample_circuit)],
        custom_settings=settings_dict,
        qubit_mapping={'Qubit A': 'QB1', 'Qubit B': 'QB2'},
        shots=1000,
    )
    assert job_id == existing_run


def test_submit_circuit_with_non_injective_qubit_mapping(mock_server, base_url, sample_circuit):
    """
    Test non-injective qubit mapping.
    """
    client = IQMClient(base_url)
    with pytest.raises(ValueError, match='Multiple logical qubits map to the same physical qubit'):
        client.submit_circuits(
            circuits=[Circuit.parse_obj(sample_circuit)],
            qubit_mapping={'Qubit A': 'QB1', 'Qubit B': 'QB1'},
        )


def test_submit_circuit_with_incomplete_qubit_mapping(mock_server, base_url, sample_circuit):
    """
    Test the scenario when circuits contain qubit names that are not present in the provided qubit mapping.
    """
    client = IQMClient(base_url)

    circuit_1 = Circuit.parse_obj(sample_circuit)

    sample_circuit['name'] = 'The other circuit'
    sample_circuit['instructions'].insert(
        0, {'name': 'phased_rx', 'qubits': ['Qubit C'], 'args': {'phase_t': 0.0, 'angle_t': 0.25}}
    )
    circuit_2 = Circuit.parse_obj(sample_circuit)
    with pytest.raises(
        ValueError,
        match="The qubits {'Qubit C'} in circuit 'The other circuit' at index 1 "
        'are not found in the provided qubit mapping.',
    ):
        client.submit_circuits(
            circuits=[circuit_1, circuit_2],
            qubit_mapping={'Qubit A': 'QB1', 'Qubit B': 'QB2'},
        )


def test_submit_circuits_with_calibration_set_id_returns_id(mock_server, base_url, calibration_set_id, sample_circuit):
    """
    Tests sending a circuit with calibration set id
    """
    client = IQMClient(base_url)
    job_id = client.submit_circuits(
        qubit_mapping={'Qubit A': 'QB1', 'Qubit B': 'QB2'},
        circuits=[Circuit.parse_obj(sample_circuit)],
        calibration_set_id=calibration_set_id,
        shots=1000,
    )
    assert job_id == existing_run


def test_submit_circuits_without_qubit_mapping_returns_id(mock_server, base_url, sample_circuit):
    """
    Tests sending a circuit without qubit mapping
    """
    client = IQMClient(base_url)
    job_id = client.submit_circuits(circuits=[Circuit.parse_obj(sample_circuit)], shots=1000)
    assert job_id == existing_run


def test_get_run_status_and_results_for_existing_run(mock_server, base_url, calibration_set_id, sample_circuit):
    """
    Tests getting the run status
    """
    client = IQMClient(base_url)
    assert client.get_run(existing_run).status == Status.PENDING
    ready_run = client.get_run(existing_run)
    assert ready_run.status == Status.READY
    assert ready_run.measurements is not None
    assert ready_run.metadata.request.calibration_set_id == calibration_set_id
    assert ready_run.metadata.request.circuits[0].metadata == sample_circuit['metadata']


def test_get_run_status_for_existing_run(mock_server, base_url):
    """
    Tests getting the run status
    """
    client = IQMClient(base_url)
    assert client.get_run_status(existing_run).status == Status.PENDING
    ready_run = client.get_run_status(existing_run)
    assert ready_run.status == Status.READY


def test_get_run_status_and_results_for_missing_run(mock_server, base_url):
    """
    Tests getting a task that was not created
    """
    client = IQMClient(base_url)
    with pytest.raises(HTTPError):
        assert client.get_run(missing_run)


def test_get_run_status_for_missing_run(mock_server, base_url):
    """
    Tests getting a task that was not created
    """
    client = IQMClient(base_url)
    with pytest.raises(HTTPError):
        assert client.get_run_status(missing_run)


def test_waiting_for_results(mock_server, base_url):
    """
    Tests waiting for results for an existing task
    """
    client = IQMClient(base_url)
    assert client.wait_for_results(existing_run).status == Status.READY


def test_get_quantum_architecture(sample_quantum_architecture, base_url):
    """Test retrieving the quantum architecture"""
    client = IQMClient(base_url)
    when(requests).get(f'{base_url}/quantum-architecture', ...).thenReturn(
        MockJsonResponse(200, sample_quantum_architecture)
    )
    assert client.get_quantum_architecture() == QuantumArchitectureSpecification(
        **sample_quantum_architecture['quantum_architecture']
    )


def test_user_warning_is_emitted_when_warnings_in_response(base_url, calibration_set_id):
    client = IQMClient(base_url)
    msg = 'This is a warning msg'
    with when(requests).get(f'{base_url}/jobs/{existing_run}', headers=None, timeout=REQUESTS_TIMEOUT).thenReturn(
        MockJsonResponse(
            200,
            {
                'status': 'ready',
                'warnings': [msg],
                'metadata': {'calibration_set_id': calibration_set_id, 'request': {'shots': 42, 'circuits': []}},
            },
        )
    ):
        with pytest.warns(UserWarning, match=msg):
            client.get_run(existing_run)


def test_base_url_is_invalid():
    invalid_base_url = 'https//example.com'
    with pytest.raises(ClientConfigurationError) as exc:
        IQMClient(invalid_base_url)
    assert f'The URL schema has to be http or https. Incorrect schema in URL: {invalid_base_url}' == str(exc.value)


def test_tokens_file_not_found():
    base_url = 'https://example.com'
    tokens_file = '/home/iqm/tokens.json'
    with pytest.raises(ClientConfigurationError) as exc:
        IQMClient(base_url, tokens_file=tokens_file)
    assert f'File not found: {tokens_file}' == str(exc.value)


def test_tokens_and_credentials_combo_invalid(credentials):
    tokens_file = '/home/iqm/tokens.json'
    base_url = 'https://example.com'
    with pytest.raises(ClientConfigurationError) as exc:
        IQMClient(base_url, tokens_file=tokens_file, **credentials)
    assert 'Either external token or credentials must be provided. Both were provided.' == str(exc.value)
