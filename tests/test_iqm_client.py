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
# pylint: disable=too-many-arguments
from mockito import expect, unstub, verifyNoUnwantedInteractions, when
import pytest
import requests
from requests import HTTPError

from iqm.iqm_client import (
    CircuitExecutionError,
    CircuitValidationError,
    ClientConfigurationError,
    HeraldingMode,
    IQMClient,
    JobAbortionError,
    QuantumArchitectureSpecification,
    SingleQubitMapping,
    Status,
    serialize_qubit_mapping,
    validate_circuit,
)
from tests.conftest import MockJsonResponse, get_jobs_args, post_jobs_args, submit_circuits_args


def test_serialize_qubit_mapping():
    """
    Tests that serialize_qubit_mapping returns a list of SingleQubitMapping objects
    """
    qm_dict = {'Alice': 'QB1', 'Bob': 'qubit_3', 'Charlie': 'physical 0'}
    assert serialize_qubit_mapping(qm_dict) == [
        SingleQubitMapping(logical_name='Alice', physical_name='QB1'),
        SingleQubitMapping(logical_name='Bob', physical_name='qubit_3'),
        SingleQubitMapping(logical_name='Charlie', physical_name='physical 0'),
    ]


def test_submit_circuits_adds_user_agent(
    sample_client, jobs_url, minimal_run_request, submit_success, quantum_architecture_url, quantum_architecture_success
):
    """
    Tests that submit_circuit without client signature adds correct User-Agent header
    """
    expect(requests, times=1).post(jobs_url, **post_jobs_args(minimal_run_request)).thenReturn(submit_success)
    expect(requests, times=1).get(quantum_architecture_url, ...).thenReturn(quantum_architecture_success)

    sample_client.submit_circuits(**submit_circuits_args(minimal_run_request))

    verifyNoUnwantedInteractions()
    unstub()


def test_submit_circuits_adds_user_agent_with_client_signature(
    client_with_signature,
    jobs_url,
    minimal_run_request,
    submit_success,
    quantum_architecture_url,
    quantum_architecture_success,
):
    """
    Tests that submit_circuit with client signature adds correct User-Agent header
    """
    expect(requests, times=1).post(
        jobs_url, **post_jobs_args(minimal_run_request, user_agent=client_with_signature._signature)
    ).thenReturn(submit_success)
    expect(requests, times=1).get(quantum_architecture_url, ...).thenReturn(quantum_architecture_success)

    client_with_signature.submit_circuits(**submit_circuits_args(minimal_run_request))

    verifyNoUnwantedInteractions()
    unstub()


@pytest.mark.parametrize(
    'run_request_name, valid_request, error_message',
    [
        ('minimal_run_request', True, None),
        ('run_request_with_heralding', True, None),
        ('run_request_with_custom_settings', True, None),
        ('run_request_with_invalid_qubit_mapping', False, 'Multiple logical qubits map to the same physical qubit.'),
        (
            'run_request_with_incomplete_qubit_mapping',
            False,
            "The qubits {'Qubit B'} in circuit 'The circuit' "
            + 'at index 0 are not found in the provided qubit mapping.',
        ),
        ('run_request_without_qubit_mapping', True, None),
        ('run_request_with_calibration_set_id', True, None),
        ('run_request_with_duration_check_disabled', True, None),
    ],
)
def test_submit_circuits_returns_id(
    sample_client,
    jobs_url,
    run_request_name,
    valid_request,
    error_message,
    request,
    submit_success,
    existing_run_id,
    quantum_architecture_url,
    quantum_architecture_success,
):
    """
    Tests submitting circuits for execution
    """
    run_request = request.getfixturevalue(run_request_name)
    when(requests).get(quantum_architecture_url, ...).thenReturn(quantum_architecture_success)

    if valid_request:
        expect(requests, times=1).post(jobs_url, **post_jobs_args(run_request)).thenReturn(submit_success)

    if error_message is None:
        assert sample_client.submit_circuits(**submit_circuits_args(run_request)) == existing_run_id
    else:
        with pytest.raises(ValueError, match=error_message):
            sample_client.submit_circuits(**submit_circuits_args(run_request))

    verifyNoUnwantedInteractions()
    unstub()


def test_submit_circuits_does_not_activate_heralding_by_default(
    sample_client, jobs_url, minimal_run_request, submit_success, quantum_architecture_url, quantum_architecture_success
):
    """
    Test submitting run request without heralding
    """
    # Expect request to have heralding mode NONE by default
    assert post_jobs_args(minimal_run_request)['json']['heralding_mode'] == HeraldingMode.NONE.value
    expect(requests, times=1).post(jobs_url, **post_jobs_args(minimal_run_request)).thenReturn(submit_success)
    when(requests).get(quantum_architecture_url, ...).thenReturn(quantum_architecture_success)

    # Specify no heralding mode in submit_circuits
    sample_client.submit_circuits(circuits=minimal_run_request.circuits, shots=minimal_run_request.shots)

    verifyNoUnwantedInteractions()
    unstub()


def test_submit_circuits_raises_with_invalid_shots(sample_client, minimal_run_request):
    """
    Test that submitting run request with invalid number of shots raises ValueError
    """
    args = submit_circuits_args(minimal_run_request)
    args['shots'] = 0
    with pytest.raises(ValueError, match='Number of shots must be greater than zero.'):
        sample_client.submit_circuits(**args)


def test_submit_circuits_sets_heralding_mode_in_run_request(
    sample_client,
    jobs_url,
    run_request_with_heralding,
    submit_success,
    quantum_architecture_url,
    quantum_architecture_success,
):
    """
    Test submitting run request with heralding
    """
    # Expect heralding mode to be the same as in run request
    expected_heralding_mode = run_request_with_heralding.heralding_mode.value
    assert post_jobs_args(run_request_with_heralding)['json']['heralding_mode'] == expected_heralding_mode
    expect(requests, times=1).post(jobs_url, **post_jobs_args(run_request_with_heralding)).thenReturn(submit_success)
    expect(requests, times=1).get(quantum_architecture_url, ...).thenReturn(quantum_architecture_success)

    assert submit_circuits_args(run_request_with_heralding)['heralding_mode'] == expected_heralding_mode
    sample_client.submit_circuits(**submit_circuits_args(run_request_with_heralding))

    verifyNoUnwantedInteractions()
    unstub()


def test_submit_circuits_gets_architecture_once(
    sample_client,
    jobs_url,
    minimal_run_request,
    submit_success,
    quantum_architecture_url,
    quantum_architecture_success,
):
    """
    Test that quantum architecture specification is only requested once from the QC
    """
    expect(requests, times=1).get(quantum_architecture_url, ...).thenReturn(quantum_architecture_success)
    expect(requests, times=1).post(jobs_url, **post_jobs_args(minimal_run_request)).thenReturn(submit_success)
    # Get architecture explicitly and then submit job
    sample_client.get_quantum_architecture()
    sample_client.submit_circuits(**submit_circuits_args(minimal_run_request))
    verifyNoUnwantedInteractions()
    unstub()


def test_submit_circuits_raises_with_invalid_heralding_mode(
    sample_client,
    quantum_architecture_url,
    quantum_architecture_success,
):
    """
    Test that submitting run request with invalid heralding mode raises an error
    """
    when(requests).get(quantum_architecture_url, ...).thenReturn(quantum_architecture_success)
    with pytest.raises(ValueError, match="Input should be 'none' or 'zeros'"):
        sample_client.submit_circuits(circuits=[], shots=10, heralding_mode='invalid')


def test_get_run_adds_user_agent(
    sample_client,
    existing_job_url,
    existing_run_id,
    pending_compilation_job_result,
    quantum_architecture_url,
    quantum_architecture_success,
):
    """
    Tests that get_run without client signature adds the correct User-Agent header
    """
    expect(requests, times=1).get(existing_job_url, **get_jobs_args()).thenReturn(pending_compilation_job_result)
    when(requests).get(quantum_architecture_url, ...).thenReturn(quantum_architecture_success)

    sample_client.get_run(existing_run_id)

    verifyNoUnwantedInteractions()
    unstub()


def test_get_run_adds_user_agent_with_client_signature(
    client_with_signature, client_signature, existing_job_url, existing_run_id, pending_compilation_job_result
):
    """
    Tests that get_run with client signature adds the correct User-Agent header
    """
    assert client_signature in client_with_signature._signature
    expect(requests, times=1).get(
        existing_job_url,
        **get_jobs_args(user_agent=client_with_signature._signature),
    ).thenReturn(pending_compilation_job_result)

    client_with_signature.get_run(existing_run_id)

    verifyNoUnwantedInteractions()
    unstub()


def test_get_run_status_and_results_for_existing_run(
    sample_client,
    existing_job_url,
    sample_circuit_metadata,
    sample_calibration_set_id,
    pending_compilation_job_result,
    pending_execution_job_result,
    pending_deletion_job_result,
    deleted_job_result,
    ready_job_result,
    existing_run_id,
):
    """
    Tests getting the run status
    """
    expect(requests, times=5).get(existing_job_url, **get_jobs_args()).thenReturn(
        pending_compilation_job_result
    ).thenReturn(pending_execution_job_result).thenReturn(ready_job_result).thenReturn(
        pending_deletion_job_result
    ).thenReturn(
        deleted_job_result
    )

    # First request gets status 'pending compilation'
    assert sample_client.get_run(existing_run_id).status == Status.PENDING_COMPILATION

    # Second requests gets status 'pending execution'
    assert sample_client.get_run(existing_run_id).status == Status.PENDING_EXECUTION

    # Third request gets status 'ready'
    job_result = sample_client.get_run(existing_run_id)
    assert job_result.status == Status.READY
    assert job_result.measurements is not None
    assert job_result.metadata.request.calibration_set_id == sample_calibration_set_id
    assert job_result.metadata.request.circuits[0].metadata == sample_circuit_metadata

    # Fourth request gets status 'pending deletion'
    assert sample_client.get_run(existing_run_id).status == Status.PENDING_DELETION

    # Fifth request gets status 'deleted'
    job_result = sample_client.get_run(existing_run_id)
    assert job_result.status == Status.DELETED
    assert job_result.measurements is None
    assert job_result.metadata.request.circuits == []
    assert job_result.metadata.request.shots == 1

    verifyNoUnwantedInteractions()
    unstub()


def test_get_run_status_for_existing_run(
    sample_client,
    existing_job_status_url,
    pending_compilation_status,
    pending_execution_status,
    ready_status,
    pending_deletion_status,
    deleted_status,
    existing_run_id,
):
    """
    Tests getting the run status
    """
    expect(requests, times=5).get(existing_job_status_url, **get_jobs_args()).thenReturn(
        pending_compilation_status
    ).thenReturn(pending_execution_status).thenReturn(ready_status).thenReturn(pending_deletion_status).thenReturn(
        deleted_status
    )

    # First request gets status 'pending compilation'
    assert sample_client.get_run_status(existing_run_id).status == Status.PENDING_COMPILATION
    # Second request gets status 'pending execution'
    assert sample_client.get_run_status(existing_run_id).status == Status.PENDING_EXECUTION
    # Third request gets status 'ready'
    assert sample_client.get_run_status(existing_run_id).status == Status.READY
    # Fourth request gets status 'pending deletion'
    assert sample_client.get_run_status(existing_run_id).status == Status.PENDING_DELETION
    # Fifth request gets status 'deleted'
    assert sample_client.get_run_status(existing_run_id).status == Status.DELETED

    verifyNoUnwantedInteractions()
    unstub()


def test_get_run_status_and_results_for_missing_run(sample_client, jobs_url, missing_run_id):
    """
    Tests getting a task that was not created
    """
    expect(requests, times=1).get(f'{jobs_url}/{missing_run_id}', **get_jobs_args()).thenReturn(
        MockJsonResponse(404, {'detail': 'not found'})
    )

    with pytest.raises(HTTPError) as e:
        sample_client.get_run(missing_run_id)
    assert e.value.response.status_code == 404

    verifyNoUnwantedInteractions()
    unstub()


def test_get_run_status_for_missing_run(sample_client, jobs_url, missing_run_id):
    """
    Tests getting a task that was not created
    """
    expect(requests, times=1).get(f'{jobs_url}/{missing_run_id}/status', **get_jobs_args()).thenReturn(
        MockJsonResponse(404, {'detail': 'not found'})
    )

    with pytest.raises(HTTPError) as e:
        sample_client.get_run_status(missing_run_id)
    assert e.value.response.status_code == 404

    verifyNoUnwantedInteractions()
    unstub()


def test_waiting_for_compilation(
    sample_client,
    existing_job_status_url,
    pending_compilation_status,
    pending_execution_status,
    existing_job_url,
    pending_execution_job_result,
    existing_run_id,
):
    """
    Tests waiting for compilation for an existing task
    """
    expect(requests, times=3).get(existing_job_status_url, **get_jobs_args()).thenReturn(
        pending_compilation_status
    ).thenReturn(pending_compilation_status).thenReturn(pending_execution_status)
    expect(requests, times=1).get(existing_job_url, **get_jobs_args()).thenReturn(pending_execution_job_result)

    assert sample_client.wait_for_compilation(existing_run_id).status == Status.PENDING_EXECUTION

    verifyNoUnwantedInteractions()
    unstub()


def test_wait_for_compilation_adds_user_agent_with_signature(
    client_with_signature,
    client_signature,
    existing_job_status_url,
    pending_compilation_status,
    pending_execution_status,
    existing_job_url,
    pending_execution_job_result,
    existing_run_id,
):
    """
    Tests that wait_for_compilation with client signature adds the correct User-Agent header
    """
    assert client_signature in client_with_signature._signature
    expect(requests, times=3).get(
        existing_job_status_url, **get_jobs_args(user_agent=client_with_signature._signature)
    ).thenReturn(pending_compilation_status).thenReturn(pending_compilation_status).thenReturn(pending_execution_status)
    expect(requests, times=1).get(
        existing_job_url, **get_jobs_args(user_agent=client_with_signature._signature)
    ).thenReturn(pending_execution_job_result)

    assert client_with_signature.wait_for_compilation(existing_run_id).status == Status.PENDING_EXECUTION

    verifyNoUnwantedInteractions()
    unstub()


def test_waiting_for_results(
    sample_client,
    existing_job_status_url,
    pending_compilation_status,
    pending_execution_status,
    ready_status,
    existing_job_url,
    ready_job_result,
    existing_run_id,
):
    """
    Tests waiting for results for an existing task
    """
    expect(requests, times=3).get(existing_job_status_url, **get_jobs_args()).thenReturn(
        pending_compilation_status
    ).thenReturn(pending_execution_status).thenReturn(ready_status)
    expect(requests, times=1).get(existing_job_url, **get_jobs_args()).thenReturn(ready_job_result)

    assert sample_client.wait_for_results(existing_run_id).status == Status.READY

    verifyNoUnwantedInteractions()
    unstub()


def test_wait_for_results_adds_user_agent_with_signature(
    client_with_signature,
    client_signature,
    existing_job_status_url,
    pending_compilation_status,
    pending_execution_status,
    ready_status,
    existing_job_url,
    ready_job_result,
    existing_run_id,
):
    """
    Tests that wait_for_results without client signature adds the correct User-Agent header
    """
    assert client_signature in client_with_signature._signature
    expect(requests, times=3).get(
        existing_job_status_url, **get_jobs_args(user_agent=client_with_signature._signature)
    ).thenReturn(pending_compilation_status).thenReturn(pending_execution_status).thenReturn(ready_status)
    expect(requests, times=1).get(
        existing_job_url, **get_jobs_args(user_agent=client_with_signature._signature)
    ).thenReturn(ready_job_result)

    assert client_with_signature.wait_for_results(existing_run_id).status == Status.READY

    verifyNoUnwantedInteractions()
    unstub()


def test_get_quantum_architecture(
    sample_client, quantum_architecture_url, sample_quantum_architecture, quantum_architecture_success
):
    """Test retrieving the quantum architecture"""
    expect(requests, times=1).get(quantum_architecture_url, ...).thenReturn(quantum_architecture_success)

    assert sample_client.get_quantum_architecture() == QuantumArchitectureSpecification(
        **sample_quantum_architecture['quantum_architecture']
    )

    verifyNoUnwantedInteractions()
    unstub()


def test_user_warning_is_emitted_when_warnings_in_response(
    sample_client, existing_job_url, job_result_with_warnings, existing_run_id
):
    """Test that a warning is emitted when warnings are present in the response"""
    expect(requests, times=1).get(existing_job_url, ...).thenReturn(job_result_with_warnings)

    expected_message = job_result_with_warnings.json()['warnings'][0]
    with pytest.warns(UserWarning, match=expected_message):
        sample_client.get_run(existing_run_id)

    verifyNoUnwantedInteractions()
    unstub()


def test_base_url_is_invalid():
    """Test that an exception is raised when the base URL is invalid"""
    invalid_base_url = 'xyz://example.com'
    with pytest.raises(ClientConfigurationError) as exc:
        IQMClient(invalid_base_url)
    assert f'The URL schema has to be http or https. Incorrect schema in URL: {invalid_base_url}' == str(exc.value)


def test_run_result_throws_json_decode_error_if_received_not_json(
    sample_client, existing_job_url, existing_run_id, not_valid_json_response
):
    """Test that an exception is raised when the response is not a valid JSON"""
    expect(requests, times=1).get(existing_job_url, ...).thenReturn(not_valid_json_response)

    with pytest.raises(CircuitExecutionError):
        sample_client.get_run(existing_run_id)

    verifyNoUnwantedInteractions()
    unstub()


def test_run_result_status_throws_json_decode_error_if_received_not_json(
    sample_client, existing_job_status_url, existing_run_id, not_valid_json_response
):
    """Test that an exception is raised when the response is not a valid JSON"""
    expect(requests, times=1).get(existing_job_status_url, ...).thenReturn(not_valid_json_response)

    with pytest.raises(CircuitExecutionError):
        sample_client.get_run_status(existing_run_id)

    verifyNoUnwantedInteractions()
    unstub()


def test_quantum_architecture_throws_json_decode_error_if_received_not_json(
    sample_client, quantum_architecture_url, not_valid_json_response
):
    """Test that an exception is raised when the response is not a valid JSON"""
    expect(requests, times=1).get(quantum_architecture_url, ...).thenReturn(not_valid_json_response)

    with pytest.raises(CircuitExecutionError):
        sample_client.get_quantum_architecture()

    verifyNoUnwantedInteractions()
    unstub()


def test_submit_circuits_throws_json_decode_error_if_received_not_json(
    sample_client, jobs_url, not_valid_json_response, quantum_architecture_url, quantum_architecture_success
):
    """Test that an exception is raised when the response is not a valid JSON"""
    expect(requests, times=1).post(jobs_url, ...).thenReturn(not_valid_json_response)
    expect(requests, times=1).get(quantum_architecture_url, ...).thenReturn(quantum_architecture_success)

    with pytest.raises(CircuitExecutionError):
        sample_client.submit_circuits([])

    verifyNoUnwantedInteractions()
    unstub()


def test_submit_circuits_throws_client_configuration_error_on_400(
    sample_client,
    jobs_url,
    not_valid_client_configuration_response,
    quantum_architecture_url,
    quantum_architecture_success,
):
    """Test that an exception is raised when the response is 400"""
    expect(requests, times=1).post(jobs_url, ...).thenReturn(not_valid_client_configuration_response)
    expect(requests, times=1).get(quantum_architecture_url, ...).thenReturn(quantum_architecture_success)

    with pytest.raises(ClientConfigurationError):
        sample_client.submit_circuits([])

    verifyNoUnwantedInteractions()
    unstub()


def test_submit_circuits_validates_circuits(sample_client, sample_circuit):
    """
    Tests that <submit_circuits> validates the batch of provided circuits
    before submitting them for execution
    """
    invalid_circuit = sample_circuit.model_copy()
    invalid_circuit.name = ''  # Invalidate the circuit on purpose
    with pytest.raises(CircuitValidationError, match='The circuit at index 1 failed the validation'):
        sample_client.submit_circuits(circuits=[sample_circuit, invalid_circuit], shots=10)


def test_validate_circuit_accepts_valid_circuit(sample_circuit):
    """
    Tests that custom Pydantic validator (triggered via <validate_circuit>)
    accepts a valid circuit.
    """
    circuit = sample_circuit.model_copy()
    validate_circuit(circuit)


def test_validate_circuit_detects_circuit_name_is_empty_string(sample_circuit):
    """
    Tests that custom Pydantic validator (triggered via <validate_circuit>)
    catches empty name of a circuit
    """
    circuit = sample_circuit.model_copy()
    circuit.name = ''
    with pytest.raises(ValueError, match='A circuit should have a non-empty string for a name'):
        validate_circuit(circuit)


def test_validate_circuit_checks_circuit_has_at_least_one_instruction(sample_circuit):
    """
    Tests that custom Pydantic validator (triggered via <validate_circuit>)
    catches when circuit instructions container has 0 instructions
    """
    circuit = sample_circuit.model_copy()
    circuit.instructions = tuple()
    with pytest.raises(ValueError, match='Each circuit should have at least one instruction'):
        validate_circuit(circuit)


def test_validate_circuit_checks_instruction_name_is_supported(sample_circuit):
    """
    Tests that custom Pydantic validator (triggered via <validate_circuit>)
    catches when instruction name is set to an unknown instruction type
    """
    circuit = sample_circuit.model_copy()
    circuit.instructions[0].name = 'kaboom'
    with pytest.raises(ValueError, match='Unknown instruction "kaboom"'):
        validate_circuit(circuit)


def test_validate_circuit_checks_instruction_implementation_is_string(sample_circuit):
    """
    Tests that custom Pydantic validator (triggered via <validate_circuit>)
    catches when instruction implementation is set to an empty string
    """
    circuit = sample_circuit.model_copy()
    circuit.instructions[0].implementation = ''
    with pytest.raises(ValueError, match='Implementation of the instruction should be None, or a non-empty string'):
        validate_circuit(circuit)


def test_validate_circuit_checks_instruction_qubit_count(sample_circuit):
    """
    Tests that custom Pydantic validator (triggered via <validate_circuit>)
    catches when qubit count of the instruction does not match the arity of
    that instruction
    """
    circuit = sample_circuit.model_copy()
    circuit.instructions[0].qubits += ('Qubit C',)
    with pytest.raises(ValueError, match=r'The "cz" instruction acts on 2 qubit\(s\), but 3 were given'):
        validate_circuit(circuit)


def test_validate_circuit_checks_instruction_argument_names(sample_circuit):
    """
    Tests that custom Pydantic validator (triggered via <validate_circuit>)
    catches when submitted argument names of the instruction are not supported
    """
    circuit = sample_circuit.model_copy()
    circuit.instructions[1].args['arg_x'] = 'This argument name is not supported by the instruction'
    with pytest.raises(ValueError, match='The instruction "prx" requires'):
        validate_circuit(circuit)


def test_validate_circuit_checks_instruction_argument_types(sample_circuit):
    """
    Tests that custom Pydantic validator (triggered via <validate_circuit>)
    catches when submitted argument types of the instruction are not supported
    """
    circuit = sample_circuit.model_copy()
    circuit.instructions[1].args['phase_t'] = '0.7'
    with pytest.raises(TypeError, match='The argument "phase_t" should be of one of the following supported types'):
        validate_circuit(circuit)


def test_validate_circuit_can_handle_raw_instructions(sample_circuit_with_raw_instructions):
    """
    Tests that custom Pydantic validator (triggered via <validate_circuit>)
    accepts a circuit with raw instructions
    """
    circuit = sample_circuit_with_raw_instructions.model_copy()
    validate_circuit(circuit)


def test_abort_job_successful(sample_client, existing_job_url, existing_run_id, abort_job_success):
    """
    Tests aborting a job
    """
    expect(requests, times=1).post(f'{existing_job_url}/abort', **post_jobs_args()).thenReturn(abort_job_success)

    sample_client.abort_job(existing_run_id)

    verifyNoUnwantedInteractions()
    unstub()


@pytest.mark.parametrize('status_code', [404, 409])
def test_abort_job_failed(status_code, sample_client, existing_job_url, existing_run_id, abort_job_failed):
    """
    Tests aborting a job raises JobAbortionError if server returned error response
    """
    response = abort_job_failed
    response.status_code = status_code
    expect(requests, times=1).post(f'{existing_job_url}/abort', **post_jobs_args()).thenReturn(response)

    with pytest.raises(JobAbortionError):
        sample_client.abort_job(existing_run_id)

    verifyNoUnwantedInteractions()
    unstub()
