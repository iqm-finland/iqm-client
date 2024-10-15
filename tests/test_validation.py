# Copyright 2024 IQM client developers
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
"""Tests for circuit validation.
"""
import pytest

from iqm.iqm_client import (
    Circuit,
    CircuitValidationError,
    Instruction,
    IQMClient,
    MoveGateValidationMode,
    QuantumArchitecture,
)

sample_qb_mapping = {'0': 'COMP_R', '1': 'QB1', '2': 'QB2', '3': 'QB3', '100': 'COMP_R2'}
reverse_qb_mapping = {value: key for key, value in sample_qb_mapping.items()}


@pytest.mark.parametrize('qubit_mapping', [None, sample_qb_mapping])
@pytest.mark.parametrize('qubits', [['QB1', 'COMP_R'], ['COMP_R', 'QB1'], ['COMP_R', 'QB2']])
def test_allowed_cz_qubits(sample_move_architecture, qubits, qubit_mapping):
    """
    Tests that instruction validation passes for allowed CZ loci
    """
    arch = QuantumArchitecture(**sample_move_architecture).quantum_architecture
    if qubit_mapping:
        qubits = [reverse_qb_mapping[q] for q in qubits]
    IQMClient._validate_instruction(arch, Instruction(name='cz', qubits=qubits, args={}), qubit_mapping)


@pytest.mark.parametrize('qubit_mapping', [None, sample_qb_mapping])
@pytest.mark.parametrize(
    'qubits', [['QB1', 'QB2'], ['QB2', 'QB1'], ['QB1', 'QB1'], ['QB3', 'QB1'], ['COMP_R', 'COMP_R'], ['COMP_R', 'QB3']]
)
def test_disallowed_cz_qubits(sample_move_architecture, qubits, qubit_mapping):
    """
    Tests that instruction validation fails for loci that are not allowed for CZ by the quantum architecture
    """
    arch = QuantumArchitecture(**sample_move_architecture).quantum_architecture
    if qubit_mapping:
        qubits = [reverse_qb_mapping[q] for q in qubits]
    with pytest.raises(CircuitValidationError, match='not allowed as locus for cz'):
        IQMClient._validate_instruction(arch, Instruction(name='cz', qubits=qubits, args={}), qubit_mapping)


@pytest.mark.parametrize('qubit_mapping', [None, sample_qb_mapping])
@pytest.mark.parametrize('qubits', [['QB3', 'COMP_R']])
def test_allowed_move_qubits(sample_move_architecture, qubits, qubit_mapping):
    """
    Tests that instruction validation passes for allowed MOVE loci
    """
    arch = QuantumArchitecture(**sample_move_architecture).quantum_architecture
    if qubit_mapping:
        qubits = [reverse_qb_mapping[q] for q in qubits]

    IQMClient._validate_instruction(arch, Instruction(name='move', qubits=qubits, args={}), qubit_mapping)


@pytest.mark.parametrize('qubit_mapping', [None, sample_qb_mapping])
@pytest.mark.parametrize(
    'qubits',
    [['QB1', 'QB2'], ['QB2', 'QB1'], ['QB1', 'QB1'], ['QB1', 'COMP_R'], ['COMP_R', 'COMP_R'], ['COMP_R', 'QB3']],
)
def test_disallowed_move_qubits(sample_move_architecture, qubits, qubit_mapping):
    """
    Tests that instruction validation fails for loci that are not allowed for MOVE by the quantum architecture
    """
    arch = QuantumArchitecture(**sample_move_architecture).quantum_architecture
    if qubit_mapping:
        qubits = [reverse_qb_mapping[q] for q in qubits]

    with pytest.raises(CircuitValidationError, match='not allowed as locus for move'):
        IQMClient._validate_instruction(arch, Instruction(name='move', qubits=qubits, args={}), qubit_mapping)


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
    with pytest.raises(CircuitValidationError, match='Qubit (.+) is not allowed as locus for measure'):
        IQMClient._validate_instruction(
            arch, Instruction(name='measure', qubits=qubits, args={'key': 'measure_1'}), None
        )


def test_measurement_keys_must_be_unique(sample_move_architecture):
    """
    Tests that all measure instructions in a circuit must have unique keys.
    """
    arch = QuantumArchitecture(**sample_move_architecture)
    circuit = Circuit(
        name='Test circuit',
        instructions=[
            Instruction(name='measure', qubits=['QB1'], args={'key': 'a'}),
            Instruction(name='measure', qubits=['QB2'], args={'key': 'a'}),
        ],
    )
    with pytest.raises(CircuitValidationError, match='has a non-unique measurement key'):
        IQMClient._validate_circuit_instructions(
            arch.quantum_architecture,
            [circuit],
        )


def test_same_measurement_key_in_different_circuits(sample_move_architecture):
    """
    Tests that the same measurement key can be used in different circuits.
    """
    arch = QuantumArchitecture(**sample_move_architecture)
    circuits = [
        Circuit(
            name='Test circuit 1',
            instructions=[
                Instruction(name='measure', qubits=['QB1'], args={'key': 'a'}),
            ],
        ),
        Circuit(
            name='Test circuit 2',
            instructions=[
                Instruction(name='measure', qubits=['QB1'], args={'key': 'a'}),
            ],
        ),
    ]
    IQMClient._validate_circuit_instructions(
        arch.quantum_architecture,
        circuits,
    )


@pytest.mark.parametrize(
    'qubits',
    [
        ['COMP_R', 'QB1', 'QB2', 'QB3'],
        ['QB1', 'COMP_R', 'QB2', 'QB3'],
        ['QB1', 'COMP_R', 'QB2'],
    ],
)
def test_barrier(sample_move_architecture, qubits):
    """
    Tests that instruction validation passes for the barrier operation
    """
    arch = QuantumArchitecture(**sample_move_architecture).quantum_architecture
    IQMClient._validate_instruction(arch, Instruction(name='barrier', qubits=qubits, args={}), None)


class TestMoveValidation:
    """Tests the validation of MOVE instructions."""

    @staticmethod
    def make_circuit_and_check(
        instructions: tuple[Instruction],
        arch: QuantumArchitecture,
        validate_moves: MoveGateValidationMode,
        qubit_mapping=None,
    ):
        """Validate the given instructions (as a circuit)."""
        circuit = Circuit(name='Move validation circuit', instructions=instructions)
        IQMClient._validate_circuit_instructions(
            arch.quantum_architecture, [circuit], qubit_mapping, validate_moves=validate_moves
        )

    @pytest.mark.parametrize('validate_moves', list(MoveGateValidationMode))
    @pytest.mark.parametrize(
        'instructions',
        [
            (Instruction(name='move', qubits=['QB3', 'COMP_R'], args={}),),
            (Instruction(name='move', qubits=['QB3', 'COMP_R'], args={}),) * 3,
        ],
    )
    def test_non_sandwich_move(self, sample_move_architecture, validate_moves, instructions):
        """Non-sandwich MOVEs are not allowed."""
        arch = QuantumArchitecture(**sample_move_architecture)
        if validate_moves != MoveGateValidationMode.NONE:
            with pytest.raises(CircuitValidationError, match=r'qubit state\(s\) are still in a resonator'):
                TestMoveValidation.make_circuit_and_check(instructions, arch, validate_moves)
        else:
            TestMoveValidation.make_circuit_and_check(instructions, arch, validate_moves)

    @pytest.mark.parametrize('validate_moves', list(MoveGateValidationMode))
    def test_move_sandwich(self, sample_move_architecture, validate_moves):
        """Valid pair of MOVEs."""
        arch = QuantumArchitecture(**sample_move_architecture)
        move = Instruction(name='move', qubits=['QB3', 'COMP_R'], args={})
        TestMoveValidation.make_circuit_and_check((move, move), arch, validate_moves)

    @pytest.mark.parametrize('validate_moves', list(MoveGateValidationMode))
    def test_bad_move_occupied_resonator(self, sample_move_architecture, validate_moves):
        """Moving a qubit state into an occupied resonator."""
        arch = QuantumArchitecture(**sample_move_architecture)
        move = Instruction(name='move', qubits=['QB3', 'COMP_R'], args={})
        invalid_sandwich_circuit = Circuit(
            name='Move validation circuit',
            instructions=(
                move,
                Instruction(name='move', qubits=['QB2', 'COMP_R'], args={}),
            ),  # this MOVE locus is not in the architecture, but only checking MOVE validation
        )
        if validate_moves != MoveGateValidationMode.NONE:
            with pytest.raises(CircuitValidationError, match='already occupied resonator'):
                IQMClient._validate_circuit_moves(
                    arch.quantum_architecture, invalid_sandwich_circuit, validate_moves=validate_moves
                )
        else:
            IQMClient._validate_circuit_moves(
                arch.quantum_architecture, invalid_sandwich_circuit, validate_moves=validate_moves
            )

    @pytest.mark.parametrize('validate_moves', list(MoveGateValidationMode))
    def test_bad_move_qubit_already_moved(self, sample_move_architecture, validate_moves):
        """Moving the state of a qubit which is already moved to another resonator."""
        arch = QuantumArchitecture(**sample_move_architecture)
        move = Instruction(name='move', qubits=['QB3', 'COMP_R'], args={})
        invalid_sandwich_circuit = Circuit(
            name='Move validation circuit',
            instructions=(
                move,
                Instruction(name='move', qubits=['QB3', 'COMP_R2'], args={}),
            ),  # this MOVE locus is not in the architecture, but only checking MOVE validation
        )
        if validate_moves != MoveGateValidationMode.NONE:
            with pytest.raises(CircuitValidationError, match='is in another resonator'):
                IQMClient._validate_circuit_moves(
                    arch.quantum_architecture, invalid_sandwich_circuit, validate_moves=validate_moves
                )
        else:
            IQMClient._validate_circuit_moves(
                arch.quantum_architecture, invalid_sandwich_circuit, validate_moves=validate_moves
            )

    @pytest.mark.parametrize('validation_mode', list(MoveGateValidationMode))
    @pytest.mark.parametrize(
        'gate, allowed_modes, disallowed_modes',
        [
            (
                Instruction(name='prx', qubits=['QB3'], args={'phase_t': 0.3, 'angle_t': -0.2}),
                (MoveGateValidationMode.ALLOW_PRX, MoveGateValidationMode.NONE),
                (MoveGateValidationMode.STRICT,),
            ),
            (
                Instruction(name='cz', qubits=['QB2', 'COMP_R'], args={}),
                (MoveGateValidationMode.STRICT, MoveGateValidationMode.ALLOW_PRX, MoveGateValidationMode.NONE),
                (),
            ),
        ],
    )
    def test_gates_in_move_sandwich(
        self, sample_move_architecture, validation_mode, gate, allowed_modes, disallowed_modes
    ):
        """Only some gates can be applied on the qubit or resonator inside a MOVE sandwich."""
        # pylint: disable=too-many-arguments
        arch = QuantumArchitecture(**sample_move_architecture)
        move = Instruction(name='move', qubits=['QB3', 'COMP_R'], args={})
        instructions = (move, gate, move)
        if validation_mode in disallowed_modes:
            with pytest.raises(CircuitValidationError, match=r'while the state\(s\) of (.+) are in a resonator'):
                TestMoveValidation.make_circuit_and_check(
                    instructions,
                    arch,
                    validation_mode,
                )
        elif validation_mode in allowed_modes:
            TestMoveValidation.make_circuit_and_check(
                instructions,
                arch,
                validation_mode,
            )
        else:
            raise ValueError(f'Unexpected validation mode: {validation_mode}')

    @pytest.mark.parametrize('validation_mode', list(MoveGateValidationMode))
    def test_device_without_resonator(self, sample_quantum_architecture, sample_circuit, validation_mode):
        """MOVEs cannot be used on a device that does not support them."""
        arch = QuantumArchitecture(**sample_quantum_architecture)
        move = Instruction(name='move', qubits=['QB3', 'COMP_R'], args={})
        with pytest.raises(CircuitValidationError, match="'move' is not supported"):
            TestMoveValidation.make_circuit_and_check((move,), arch, validation_mode)
        # But validation passes if there are no MOVE gates
        TestMoveValidation.make_circuit_and_check(sample_circuit.instructions, arch, validation_mode)

    @pytest.mark.parametrize('validation_mode', list(MoveGateValidationMode))
    def test_qubit_mapping(self, sample_move_architecture, validation_mode):
        """Test that MOVE circuit validation works with an explicit qubit mapping given."""
        arch = QuantumArchitecture(**sample_move_architecture)
        move = Instruction(name='move', qubits=[reverse_qb_mapping[qb] for qb in ['QB3', 'COMP_R']], args={})
        prx = Instruction(
            name='prx', qubits=[reverse_qb_mapping[qb] for qb in ['QB3']], args={'phase_t': 0.3, 'angle_t': -0.2}
        )
        cz = Instruction(name='cz', qubits=[reverse_qb_mapping[qb] for qb in ['QB2', 'COMP_R']], args={})
        TestMoveValidation.make_circuit_and_check((move, move), arch, validation_mode, sample_qb_mapping)
        TestMoveValidation.make_circuit_and_check((prx, move, cz, move), arch, validation_mode, sample_qb_mapping)
        # qubit mapping without all qubits/resonators in the architecture
        partial_qb_mapping = {k: v for k, v in sample_qb_mapping.items() if v in ['QB2', 'QB3', 'COMP_R']}
        TestMoveValidation.make_circuit_and_check((move, move), arch, validation_mode, partial_qb_mapping)
        TestMoveValidation.make_circuit_and_check((prx, move, cz, move), arch, validation_mode, partial_qb_mapping)
