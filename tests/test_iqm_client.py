# Copyright 2021-2023 IQM client developers
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
from mockito import ANY, verify, when

# pylint: disable=unused-argument
import pytest
import requests
from requests import HTTPError

from iqm_client import (
    DIST_NAME,
    Circuit,
    CircuitExecutionError,
    CircuitValidationError,
    ClientConfigurationError,
    IQMClient,
    QuantumArchitectureSpecification,
    SingleQubitMapping,
    Status,
    __version__,
    serialize_qubit_mapping,
    validate_circuit,
)
from tests.conftest import MockJsonResponse, MockTextResponse, existing_run, missing_run

REQUESTS_TIMEOUT = 60


def test_serialize_qubit_mapping():
    """
    Tests that serialize_qubit_mapping returns a list of SingleQubitMapping objects
    """
    qubit_mapping = {'Alice': 'QB1', 'Bob': 'qubit_3', 'Charlie': 'physical 0'}
    assert serialize_qubit_mapping(qubit_mapping) == [
        SingleQubitMapping(logical_name='Alice', physical_name='QB1'),
        SingleQubitMapping(logical_name='Bob', physical_name='qubit_3'),
        SingleQubitMapping(logical_name='Charlie', physical_name='physical 0'),
    ]


def test_submit_circuits_adds_user_agent(mock_server, base_url, sample_circuit):
    """
    Tests that submit_circuit without client signature adds correct User-Agent header
    """
    client = IQMClient(base_url)
    client.submit_circuits(
        circuits=[Circuit.parse_obj(sample_circuit)],
        qubit_mapping={'Qubit A': 'QB1', 'Qubit B': 'QB2'},
        shots=1000,
    )
    verify(requests).post(
        f'{base_url}/jobs',
        json=ANY,
        headers={'Expect': '100-Continue', 'User-Agent': f'{DIST_NAME} {__version__}'},
        timeout=ANY,
    )


def test_submit_circuits_adds_user_agent_with_client_signature(mock_server, base_url, sample_circuit):
    """
    Tests that submit_circuit with client signature adds correct User-Agent header
    """
    client = IQMClient(base_url, client_signature='some-client-signature')
    assert 'some-client-signature' in client._signature
    client.submit_circuits(
        circuits=[Circuit.parse_obj(sample_circuit)],
        qubit_mapping={'Qubit A': 'QB1', 'Qubit B': 'QB2'},
        shots=1000,
    )
    verify(requests).post(
        f'{base_url}/jobs',
        json=ANY,
        headers={'Expect': '100-Continue', 'User-Agent': f'{DIST_NAME} {__version__}, some-client-signature'},
        timeout=REQUESTS_TIMEOUT,
    )


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


def test_get_run_adds_user_agent(mock_server, base_url, calibration_set_id, sample_circuit):
    """
    Tests that get_run without client signature adds the correct User-Agent header
    """
    client = IQMClient(base_url)
    client.get_run(existing_run)
    verify(requests).get(
        f'{base_url}/jobs/{existing_run}',
        headers={'User-Agent': f'{DIST_NAME} {__version__}'},
        timeout=REQUESTS_TIMEOUT,
    )


def test_get_run_adds_user_agent_with_client_signature(mock_server, base_url, calibration_set_id, sample_circuit):
    """
    Tests that get_run with client signature adds the correct User-Agent header
    """
    client = IQMClient(base_url, client_signature='some-client-signature')
    assert 'some-client-signature' in client._signature
    client.get_run(existing_run)
    verify(requests).get(
        f'{base_url}/jobs/{existing_run}',
        headers={'User-Agent': f'{DIST_NAME} {__version__}, some-client-signature'},
        timeout=REQUESTS_TIMEOUT,
    )


def test_get_run_status_and_results_for_existing_run(mock_server, base_url, calibration_set_id, sample_circuit):
    """
    Tests getting the run status
    """
    client = IQMClient(base_url)
    assert client.get_run(existing_run).status == Status.PENDING_COMPILATION
    compiled_run = client.get_run(existing_run)
    assert compiled_run.status == Status.PENDING_EXECUTION
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
    assert client.get_run_status(existing_run).status == Status.PENDING_COMPILATION
    compiled_run = client.get_run_status(existing_run)
    assert compiled_run.status == Status.PENDING_EXECUTION
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


def test_waiting_for_compilation(mock_server, base_url):
    """
    Tests waiting for compilation for an existing task
    """
    client = IQMClient(base_url)
    assert client.wait_for_compilation(existing_run).status == Status.PENDING_EXECUTION


def test_wait_for_compilation_adds_user_agent(mock_server, base_url):
    """
    Tests that wait_for_compilation without client signature adds the correct User-Agent header
    """
    client = IQMClient(base_url)
    client.wait_for_compilation(existing_run)
    verify(requests, times=2).get(
        f'{base_url}/jobs/{existing_run}',
        headers={'User-Agent': f'{DIST_NAME} {__version__}'},
        timeout=REQUESTS_TIMEOUT,
    )


def test_wait_for_compilation_adds_user_agent_with_client_signature(mock_server, base_url):
    """
    Tests that wait_for_compilation with client signature adds the correct User-Agent header
    """
    client = IQMClient(base_url, client_signature='some-client-signature')
    client.wait_for_compilation(existing_run)
    assert 'some-client-signature' in client._signature
    verify(requests, times=2).get(
        f'{base_url}/jobs/{existing_run}',
        headers={'User-Agent': f'{DIST_NAME} {__version__}, some-client-signature'},
        timeout=REQUESTS_TIMEOUT,
    )


def test_waiting_for_results(mock_server, base_url):
    """
    Tests waiting for results for an existing task
    """
    client = IQMClient(base_url)
    assert client.wait_for_results(existing_run).status == Status.READY


def test_wait_for_results_adds_user_agent(mock_server, base_url):
    """
    Tests that wait_for_results without client signature adds the correct User-Agent header
    """
    client = IQMClient(base_url)
    client.wait_for_results(existing_run)
    verify(requests, times=3).get(
        f'{base_url}/jobs/{existing_run}',
        headers={'User-Agent': f'{DIST_NAME} {__version__}'},
        timeout=REQUESTS_TIMEOUT,
    )


def test_wait_for_results_adds_user_agent_with_client_signature(mock_server, base_url):
    """
    Tests that wait_for_results with client signature adds the correct User-Agent header
    """
    client = IQMClient(base_url, client_signature='some-client-signature')
    client.wait_for_results(existing_run)
    assert 'some-client-signature' in client._signature
    verify(requests, times=3).get(
        f'{base_url}/jobs/{existing_run}',
        headers={'User-Agent': f'{DIST_NAME} {__version__}, some-client-signature'},
        timeout=REQUESTS_TIMEOUT,
    )


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
    """Test that a warning is emitted when warnings are present in the response"""
    client = IQMClient(base_url)
    msg = 'This is a warning msg'
    with when(requests).get(f'{base_url}/jobs/{existing_run}', headers=ANY, timeout=ANY).thenReturn(
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
    """Test that an exception is raised when the base URL is invalid"""
    invalid_base_url = 'https//example.com'
    with pytest.raises(ClientConfigurationError) as exc:
        IQMClient(invalid_base_url)
    assert f'The URL schema has to be http or https. Incorrect schema in URL: {invalid_base_url}' == str(exc.value)


def test_tokens_file_not_found():
    """Test that an exception is raised when the tokens file is not found"""
    base_url = 'https://example.com'
    tokens_file = '/home/iqm/tokens.json'
    with pytest.raises(ClientConfigurationError) as exc:
        IQMClient(base_url, tokens_file=tokens_file)
    assert f'File not found: {tokens_file}' == str(exc.value)


def test_tokens_and_credentials_combo_invalid(credentials):
    """Test that an exception is raised when both tokens and credentials are provided"""
    tokens_file = '/home/iqm/tokens.json'
    base_url = 'https://example.com'
    with pytest.raises(ClientConfigurationError) as exc:
        IQMClient(base_url, tokens_file=tokens_file, **credentials)
    assert 'Either external token or credentials must be provided. Both were provided.' == str(exc.value)


def test_run_result_throws_json_decode_error_if_received_not_json(base_url):
    """Test that an exception is raised when the response is not a valid JSON"""
    client = IQMClient(base_url)
    with when(requests).get(f'{base_url}/jobs/{existing_run}', headers=ANY, timeout=ANY).thenReturn(
        MockTextResponse(200, 'not a valid json')
    ):
        with pytest.raises(CircuitExecutionError):
            client.get_run(existing_run)


def test_run_result_status_throws_json_decode_error_if_received_not_json(base_url):
    """Test that an exception is raised when the response is not a valid JSON"""
    client = IQMClient(base_url)
    with when(requests).get(f'{base_url}/jobs/{existing_run}/status', headers=ANY, timeout=ANY).thenReturn(
        MockTextResponse(200, 'not a valid json')
    ):
        with pytest.raises(CircuitExecutionError):
            client.get_run_status(existing_run)


def test_quantum_architecture_throws_json_decode_error_if_received_not_json(base_url):
    """Test that an exception is raised when the response is not a valid JSON"""
    client = IQMClient(base_url)
    with when(requests).get(f'{base_url}/quantum-architecture', headers=ANY, timeout=ANY).thenReturn(
        MockTextResponse(200, 'not a valid json')
    ):
        with pytest.raises(CircuitExecutionError):
            client.get_quantum_architecture()


def test_submit_circuits_throws_json_decode_error_if_received_not_json(base_url):
    """Test that an exception is raised when the response is not a valid JSON"""
    client = IQMClient(base_url)
    with when(requests).post(f'{base_url}/jobs', json=ANY, headers=ANY, timeout=ANY).thenReturn(
        MockTextResponse(200, 'not a valid json')
    ):
        with pytest.raises(CircuitExecutionError):
            client.submit_circuits([])


def test_submit_circuits_validates_circuits(base_url, sample_circuit):
    """
    Tests that <submit_circuits> validates the batch of provided circuits
    before submitting them for execution
    """
    client = IQMClient(base_url)
    valid_circuit = Circuit.parse_obj(sample_circuit)
    invalid_circuit = Circuit.parse_obj(sample_circuit)
    invalid_circuit.name = ''  # Invalidate the circuit on purpose
    with pytest.raises(CircuitValidationError, match='The circuit at index 1 failed the validation'):
        client.submit_circuits(circuits=[valid_circuit, invalid_circuit])


def test_validate_circuit_detects_circuit_name_is_empty_string(sample_circuit):
    """
    Tests that custom Pydantic validator (triggered via <validate_circuit>)
    catches empty name of a circuit
    """
    circuit = Circuit.parse_obj(sample_circuit)
    circuit.name = ''
    with pytest.raises(ValueError, match='A circuit should have a non-empty string for a name'):
        validate_circuit(circuit)


def test_validate_circuit_detects_circuit_metadata_is_wrong_type(sample_circuit):
    """
    Tests that custom Pydantic validator (triggered via <validate_circuit>)
    catches invalid type of circuit metadata
    """
    circuit = Circuit.parse_obj(sample_circuit)
    circuit.metadata = []
    with pytest.raises(ValueError, match='Circuit metadata should be a dictionary'):
        validate_circuit(circuit)


def test_validate_circuit_detects_circuit_metadata_keys_are_wrong_type(sample_circuit):
    """
    Tests that custom Pydantic validator (triggered via <validate_circuit>)
    catches invalid type of circuit metadata
    """
    circuit = Circuit.parse_obj(sample_circuit)
    circuit.metadata = {'1': 'string key is ok', 2: 'int key is not ok'}
    with pytest.raises(ValueError, match='Metadata dictionary should use strings for all root-level keys'):
        validate_circuit(circuit)


def test_validate_circuit_checks_circuit_instructions_container_type(sample_circuit):
    """
    Tests that custom Pydantic validator (triggered via <validate_circuit>)
    catches invalid type of instruction container of a circuit
    """
    circuit = Circuit.parse_obj(sample_circuit)
    circuit.instructions = {}
    with pytest.raises(ValueError, match='Instructions of a circuit should be packed in a tuple'):
        validate_circuit(circuit)


def test_validate_circuit_checks_circuit_has_at_least_one_instruction(sample_circuit):
    """
    Tests that custom Pydantic validator (triggered via <validate_circuit>)
    catches when circuit instructions container has 0 instructions
    """
    circuit = Circuit.parse_obj(sample_circuit)
    circuit.instructions = tuple()
    with pytest.raises(ValueError, match='Each circuit should have at least one instruction'):
        validate_circuit(circuit)


def test_validate_circuit_checks_circuit_instructions_container_content(sample_circuit):
    """
    Tests that custom Pydantic validator (triggered via <validate_circuit>)
    catches when circuit instructions container has items of incorrect type
    """
    circuit = Circuit.parse_obj(sample_circuit)
    circuit.instructions += ('I am not an instruction!',)
    with pytest.raises(ValueError, match='Every instruction in a circuit should be of type <Instruction>'):
        validate_circuit(circuit)


def test_validate_circuit_checks_instruction_name_is_supported(sample_circuit):
    """
    Tests that custom Pydantic validator (triggered via <validate_circuit>)
    catches when instruction name is set to an unknown instruction type
    """
    circuit = Circuit.parse_obj(sample_circuit)
    circuit.instructions[0].name = 'kaboom'
    with pytest.raises(ValueError, match='Unknown instruction "kaboom"'):
        validate_circuit(circuit)


def test_validate_circuit_checks_instruction_implementation_is_string(sample_circuit):
    """
    Tests that custom Pydantic validator (triggered via <validate_circuit>)
    catches when instruction implementation is set to an empty string
    """
    circuit = Circuit.parse_obj(sample_circuit)
    circuit.instructions[0].implementation = ''
    with pytest.raises(ValueError, match='Implementation of the instruction should be set to a non-empty string'):
        validate_circuit(circuit)


def test_validate_circuit_checks_instruction_qubit_count(sample_circuit):
    """
    Tests that custom Pydantic validator (triggered via <validate_circuit>)
    catches when qubit count of the instruction does not match the arity of
    that instruction
    """
    circuit = Circuit.parse_obj(sample_circuit)
    circuit.instructions[0].qubits += ('Qubit C',)
    with pytest.raises(ValueError, match=r'The "cz" instruction acts on 2 qubit\(s\), but 3 were given'):
        validate_circuit(circuit)


def test_validate_circuit_checks_instruction_argument_names(sample_circuit):
    """
    Tests that custom Pydantic validator (triggered via <validate_circuit>)
    catches when submitted argument names of the instruction are not supported
    """
    circuit = Circuit.parse_obj(sample_circuit)
    circuit.instructions[1].args['arg_x'] = 'This argument name is not supported by the instruction'
    with pytest.raises(ValueError, match='The instruction "phased_rx" requires'):
        validate_circuit(circuit)


def test_validate_circuit_checks_instruction_argument_types(sample_circuit):
    """
    Tests that custom Pydantic validator (triggered via <validate_circuit>)
    catches when submitted argument types of the instruction are not supported
    """
    circuit = Circuit.parse_obj(sample_circuit)
    circuit.instructions[1].args['phase_t'] = '0.7'
    with pytest.raises(ValueError, match='The argument "phase_t" should be of one of the following supported types'):
        validate_circuit(circuit)
