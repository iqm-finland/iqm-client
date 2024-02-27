import re

import pytest

from iqm.iqm_client import CircuitExecutionError, Instruction, IQMClient, QuantumArchitecture

sample_qb_mapping = {'0': 'COMP_R', '1': 'QB1', '2': 'QB2', '3': 'QB3'}
reverse_qb_mapping = {value: key for key, value in sample_qb_mapping.items()}


@pytest.mark.parametrize('qubits', [['QB1', 'COMP_R'], ['COMP_R', 'QB1'], ['COMP_R', 'QB2']])
def test_allowed_cz_qubits(sample_move_architecture, qubits):
    """
    Tests that instruction validation passes for allowed CZ loci
    """
    arch = QuantumArchitecture(**sample_move_architecture).quantum_architecture
    IQMClient._validate_instruction(arch, Instruction(name='cz', qubits=qubits, args={}), None)
    IQMClient._validate_instruction(
        arch, Instruction(name='cz', qubits=[reverse_qb_mapping[q] for q in qubits], args={}), sample_qb_mapping
    )


@pytest.mark.parametrize(
    'qubits', [['QB1', 'QB2'], ['QB2', 'QB1'], ['QB1', 'QB1'], ['QB3', 'QB1'], ['COMP_R', 'COMP_R'], ['COMP_R', 'QB3']]
)
def test_disallowed_cz_qubits(sample_move_architecture, qubits):
    """
    Tests that instruction validation fails for loci that are not allowed for CZ by the quantum architecture
    """
    arch = QuantumArchitecture(**sample_move_architecture).quantum_architecture
    with pytest.raises(CircuitExecutionError) as err:
        IQMClient._validate_instruction(arch, Instruction(name='cz', qubits=qubits, args={}), None)
    assert str(err.value) == f"('{qubits[0]}', '{qubits[1]}') not allowed as locus for cz"

    reversed_qb = [reverse_qb_mapping[q] for q in qubits]
    with pytest.raises(CircuitExecutionError) as err2:
        IQMClient._validate_instruction(arch, Instruction(name='cz', qubits=reversed_qb, args={}), sample_qb_mapping)
    assert (
        str(err2.value)
        == f"('{reversed_qb[0]}', '{reversed_qb[1]}') = ('{qubits[0]}', '{qubits[1]}') not allowed as locus for cz"
    )


def test_allowed_move_qubits(sample_move_architecture):
    """
    Tests that instruction validation passes for allowed MOVE loci
    """
    arch = QuantumArchitecture(**sample_move_architecture).quantum_architecture
    IQMClient._validate_instruction(arch, Instruction(name='move', qubits=['QB3', 'COMP_R'], args={}), None)
    IQMClient._validate_instruction(
        arch, Instruction(name='move', qubits=['3', '0'], args={}), qubit_mapping={'3': 'QB3', '0': 'COMP_R'}
    )
    IQMClient._validate_instruction(
        arch, Instruction(name='move', qubits=['0', '1'], args={}), qubit_mapping={'0': 'QB3', '1': 'COMP_R'}
    )


@pytest.mark.parametrize(
    'qubits', [['QB1', 'QB2'], ['QB2', 'QB1'], ['QB1', 'QB1'], ['QB3', 'QB1'], ['COMP_R', 'COMP_R'], ['COMP_R', 'QB3']]
)
def test_disallowed_move_qubits(sample_move_architecture, qubits):
    """
    Tests that instruction validation fails for loci that are not allowed for MOVE by the quantum architecture
    """
    arch = QuantumArchitecture(**sample_move_architecture).quantum_architecture
    with pytest.raises(CircuitExecutionError) as err:
        IQMClient._validate_instruction(arch, Instruction(name='move', qubits=qubits, args={}), None)
    assert str(err.value) == f"('{qubits[0]}', '{qubits[1]}') not allowed as locus for move"


@pytest.mark.parametrize('qubits', [['QB1', 'QB2'], ['QB2'], ['QB1', 'QB2', 'QB3'], ['QB3', 'QB1'], ['QB1']])
def test_allowed_measure_qubits(sample_move_architecture, qubits):
    """
    Tests that instruction validation succeeds for loci that are any combination of valid measure qubits
    """
    arch = QuantumArchitecture(**sample_move_architecture).quantum_architecture
    IQMClient._validate_instruction(arch, Instruction(name='measure', qubits=qubits, args={'key': 'measure_1'}), None)


@pytest.mark.parametrize('qubits', [['QB1', 'COMP_R'], ['COMP_R'], ['QB1', 'QB2', 'QB4'], ['QB4']])
def test_disallowed_measure_qubits(sample_move_architecture, qubits):
    """
    Tests that instruction validation fails for loci containing any qubits that are not valid measure qubits
    """
    arch = QuantumArchitecture(**sample_move_architecture).quantum_architecture
    with pytest.raises(CircuitExecutionError) as err:
        IQMClient._validate_instruction(
            arch, Instruction(name='measure', qubits=qubits, args={'key': 'measure_1'}), None
        )
    assert re.match(r'Qubit (.+) is not allowed as locus for measure', str(err.value))


def test_barrier(sample_move_architecture):
    """
    Tests that instruction validation passes for the barrier operation
    """
    arch = QuantumArchitecture(**sample_move_architecture).quantum_architecture
    IQMClient._validate_instruction(
        arch, Instruction(name='barrier', qubits=['COMP_R', 'QB1', 'QB2', 'QB3'], args={}), None
    )
    IQMClient._validate_instruction(
        arch, Instruction(name='barrier', qubits=['QB1', 'COMP_R', 'QB2', 'QB3'], args={}), None
    )
