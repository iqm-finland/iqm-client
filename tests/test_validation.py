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
import re

import pytest

from iqm.iqm_client import Circuit, CircuitExecutionError, Instruction, IQMClient, QuantumArchitecture

sample_qb_mapping = {'0': 'COMP_R', '1': 'QB1', '2': 'QB2', '3': 'QB3'}
reverse_qb_mapping = {value: key for key, value in sample_qb_mapping.items()}


@pytest.mark.parametrize('instruction', [
    Instruction(name='barrier', qubits=['QB1'], args={}),
    Instruction(name='barrier', qubits=['QB1', 'QB2'], args={}),
    Instruction(name='barrier', qubits=['QB2', 'QB1'], args={}),  # barrier can use any loci
    Instruction(name='prx', qubits=['QB1'], args={'phase_t': 0.3, 'angle_t': -0.2}),
    Instruction(name='cz', qubits=['QB1', 'QB2'], args={}),
    Instruction(name='cz', qubits=['QB2', 'QB1'], args={}),  # CZ is symmetric
    Instruction(name='measure', qubits=['QB1'], args={'key': 'm'}),
    Instruction(name='measure', qubits=['QB1', 'QB2'], args={'key': 'm'}),  # measure is factorizable
    Instruction(name='measure', qubits=['QB2', 'QB1'], args={'key': 'm'}),  # measure is factorizable
])
def test_valid_instruction(sample_quantum_architecture, instruction):
    """Valid instructions must pass validation.
    """
    arch = QuantumArchitecture(**sample_quantum_architecture).quantum_architecture
    IQMClient._validate_instruction(arch, instruction, None)


@pytest.mark.parametrize('instruction,match', [
    [Instruction(name='barrier', qubits=['QB1', 'QB2', 'XXX'], args={}), 'does not exist'],
    [Instruction(name='prx', qubits=['QB3'], args={'phase_t': 0.3, 'angle_t': -0.2}), 'not allowed as locus'],
    [Instruction(name='cz', qubits=['QB2', 'QB3'], args={}), 'not allowed as locus'],
    [Instruction(name='measure', qubits=['QB1', 'QB3'], args={'key': 'm'}), 'is not allowed as locus'],
    [Instruction(name='measure', qubits=['QB3'], args={'key': 'm'}), 'is not allowed as locus'],
])
def test_invalid_instruction(sample_quantum_architecture, instruction, match):
    """Invalid instructions must not pass validation.
    """
    arch = QuantumArchitecture(**sample_quantum_architecture).quantum_architecture
    with pytest.raises(CircuitExecutionError, match=match):
        IQMClient._validate_instruction(arch, instruction, None)


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
    def make_circuit_and_check(instructions: tuple[Instruction], arch: QuantumArchitecture, qubit_mapping=None):
        circuit = Circuit(name='Move validation circuit', instructions=instructions)
        IQMClient._validate_circuit_moves(arch.quantum_architecture, circuit, qubit_mapping)

    def test_moves_paired(self, sample_move_architecture):
        arch = QuantumArchitecture(**sample_move_architecture)
        instructions = (TestMoveSafetyValidation.move,)
        with pytest.raises(CircuitExecutionError):
            TestMoveSafetyValidation.make_circuit_and_check(instructions, arch)
        with pytest.raises(CircuitExecutionError):
            TestMoveSafetyValidation.make_circuit_and_check(
                (
                    TestMoveSafetyValidation.move,
                    Instruction(name='move', qubits=['QB2', 'COMP_R'], args={}),
                ),
                arch,
            )
        with pytest.raises(CircuitExecutionError):
            TestMoveSafetyValidation.make_circuit_and_check(
                (
                    TestMoveSafetyValidation.move,
                    Instruction(name='move', qubits=['COMP_R', 'QB3'], args={}),
                ),
                arch,
            )
        TestMoveSafetyValidation.make_circuit_and_check(instructions * 2, arch)

    def test_gates_between_moves(self, sample_move_architecture):
        arch = QuantumArchitecture(**sample_move_architecture)
        with pytest.raises(CircuitExecutionError):
            TestMoveSafetyValidation.make_circuit_and_check(
                (TestMoveSafetyValidation.move, TestMoveSafetyValidation.gate, TestMoveSafetyValidation.move), arch
            )
        TestMoveSafetyValidation.make_circuit_and_check(
            (
                TestMoveSafetyValidation.gate,
                TestMoveSafetyValidation.move,
                TestMoveSafetyValidation.cz,
                TestMoveSafetyValidation.move,
            ),
            arch,
        )

    def test_device_without_resonator(self, sample_quantum_architecture, sample_circuit):
        arch = QuantumArchitecture(**sample_quantum_architecture)
        with pytest.raises(CircuitExecutionError):
            TestMoveSafetyValidation.make_circuit_and_check((TestMoveSafetyValidation.move,), arch)
        TestMoveSafetyValidation.make_circuit_and_check(sample_circuit.instructions, arch)

    def test_qubit_mapping(self, sample_move_architecture):
        arch = QuantumArchitecture(**sample_move_architecture)
        move = Instruction(name='move', qubits=[reverse_qb_mapping[qb] for qb in ['QB3', 'COMP_R']], args={})
        gate = Instruction(
            name='prx', qubits=[reverse_qb_mapping[qb] for qb in ['QB3']], args={'phase_t': 0.3, 'angle_t': -0.2}
        )
        cz = Instruction(name='cz', qubits=[reverse_qb_mapping[qb] for qb in ['QB2', 'COMP_R']], args={})
        TestMoveSafetyValidation.make_circuit_and_check((move, move), arch, sample_qb_mapping)
        TestMoveSafetyValidation.make_circuit_and_check((gate, move, cz, move), arch, sample_qb_mapping)
