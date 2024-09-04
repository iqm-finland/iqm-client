import re

import pytest

from iqm.iqm_client import (
    Circuit,
    CircuitExecutionError,
    Instruction,
    IQMClient,
    MoveGateValidationMode,
    QuantumArchitecture,
)

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


class TestMoveSafetyValidation:
    """Tests the validation of safe Move instructions"""

    move = Instruction(name='move', qubits=['QB3', 'COMP_R'], args={})
    gate = Instruction(name='prx', qubits=['QB3'], args={'phase_t': 0.3, 'angle_t': -0.2})
    cz = Instruction(name='cz', qubits=['QB2', 'COMP_R'], args={})

    @staticmethod
    def make_circuit_and_check(
        instructions: tuple[Instruction],
        arch: QuantumArchitecture,
        validate_moves: MoveGateValidationMode,
        qubit_mapping=None,
    ):
        circuit = Circuit(name='Move validation circuit', instructions=instructions)
        IQMClient._validate_circuit_instructions(
            arch.quantum_architecture, [circuit], qubit_mapping, validate_moves=validate_moves
        )

    @pytest.mark.parametrize('validate_moves', list(MoveGateValidationMode))
    def test_moves_paired(self, sample_move_architecture, validate_moves):
        arch = QuantumArchitecture(**sample_move_architecture)
        instructions = (TestMoveSafetyValidation.move,)
        # Single MOVE is not allowed
        if validate_moves != MoveGateValidationMode.NONE:
            with pytest.raises(CircuitExecutionError):
                TestMoveSafetyValidation.make_circuit_and_check(instructions, arch, validate_moves)
        else:
            TestMoveSafetyValidation.make_circuit_and_check(instructions, arch, validate_moves)

        # MOVEs must be paired
        invalid_sandwich_circuit = Circuit(
            name='Move validation circuit',
            instructions=(
                TestMoveSafetyValidation.move,
                Instruction(name='move', qubits=['QB2', 'COMP_R'], args={}),
            ),  # Invalid MOVE gate, but only checking MOVE validation here
        )
        if validate_moves != MoveGateValidationMode.NONE:
            with pytest.raises(CircuitExecutionError):
                IQMClient._validate_circuit_moves(
                    arch.quantum_architecture, invalid_sandwich_circuit, validate_moves=validate_moves
                )
        else:
            IQMClient._validate_circuit_moves(
                arch.quantum_architecture, invalid_sandwich_circuit, validate_moves=validate_moves
            )
        # Normal use of MOVE sandwich is fine.
        TestMoveSafetyValidation.make_circuit_and_check(instructions * 2, arch, validate_moves)

        # Resonator is the second argument - Regardless of validation mode, this is not allowed
        with pytest.raises(CircuitExecutionError):
            TestMoveSafetyValidation.make_circuit_and_check(
                (
                    TestMoveSafetyValidation.move,
                    Instruction(name='move', qubits=['COMP_R', 'QB3'], args={}),
                ),
                arch,
                validate_moves,
            )
        # MOVE needs to have valid loci
        with pytest.raises(CircuitExecutionError):
            TestMoveSafetyValidation.make_circuit_and_check(
                (
                    Instruction(name='move', qubits=['QB1', 'COMP_R'], args={}),
                    Instruction(name='move', qubits=['QB1', 'COMP_R'], args={}),
                ),
                arch,
                validate_moves,
            )

    @pytest.mark.parametrize('validate_moves', list(MoveGateValidationMode))
    def test_gates_between_moves(self, sample_move_architecture, validate_moves):
        arch = QuantumArchitecture(**sample_move_architecture)
        # PRX is not allowed between moves
        if validate_moves == MoveGateValidationMode.STRICT:
            with pytest.raises(CircuitExecutionError):
                TestMoveSafetyValidation.make_circuit_and_check(
                    (TestMoveSafetyValidation.move, TestMoveSafetyValidation.gate, TestMoveSafetyValidation.move),
                    arch,
                    validate_moves,
                )
        elif validate_moves in [MoveGateValidationMode.ALLOW_PRX, MoveGateValidationMode.NONE]:
            TestMoveSafetyValidation.make_circuit_and_check(
                (TestMoveSafetyValidation.move, TestMoveSafetyValidation.gate, TestMoveSafetyValidation.move),
                arch,
                validate_moves,
            )
        else:
            raise ValueError(f'Unexpected validation mode: {validate_moves}')
        # CZ is allowed between moves
        TestMoveSafetyValidation.make_circuit_and_check(
            (
                TestMoveSafetyValidation.gate,
                TestMoveSafetyValidation.move,
                TestMoveSafetyValidation.cz,
                TestMoveSafetyValidation.move,
            ),
            arch,
            validate_moves,
        )

    @pytest.mark.parametrize('validate_moves', list(MoveGateValidationMode))
    def test_device_without_resonator(self, sample_quantum_architecture, sample_circuit, validate_moves):
        arch = QuantumArchitecture(**sample_quantum_architecture)
        # Cannot use a MOVE gate on a device that does not support it
        with pytest.raises(ValueError):
            TestMoveSafetyValidation.make_circuit_and_check((TestMoveSafetyValidation.move,), arch, validate_moves)
        # But validation passes if there are no MOVE gates
        TestMoveSafetyValidation.make_circuit_and_check(sample_circuit.instructions, arch, validate_moves)

    @pytest.mark.parametrize('validate_moves', list(MoveGateValidationMode))
    def test_qubit_mapping(self, sample_move_architecture, validate_moves):
        arch = QuantumArchitecture(**sample_move_architecture)
        move = Instruction(name='move', qubits=[reverse_qb_mapping[qb] for qb in ['QB3', 'COMP_R']], args={})
        gate = Instruction(
            name='prx', qubits=[reverse_qb_mapping[qb] for qb in ['QB3']], args={'phase_t': 0.3, 'angle_t': -0.2}
        )
        cz = Instruction(name='cz', qubits=[reverse_qb_mapping[qb] for qb in ['QB2', 'COMP_R']], args={})
        TestMoveSafetyValidation.make_circuit_and_check((move, move), arch, validate_moves, sample_qb_mapping)
        TestMoveSafetyValidation.make_circuit_and_check((gate, move, cz, move), arch, validate_moves, sample_qb_mapping)
