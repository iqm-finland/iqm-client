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
import re
from uuid import UUID

import pytest

from iqm.iqm_client import (
    Circuit,
    CircuitTranspilationError,
    DynamicQuantumArchitecture,
    ExistingMoveHandlingOptions,
    GateImplementationInfo,
    GateInfo,
    Instruction,
    IQMClient,
    simplified_architecture,
    transpile_insert_moves,
    transpile_remove_moves,
)
from iqm.iqm_client.transpile import _ResonatorStateTracker as ResonatorStateTracker


class TestNaiveMoveTranspiler:
    # pylint: disable=too-many-public-methods

    @pytest.fixture(autouse=True)
    def init_arch(self, sample_move_architecture):
        # pylint: disable=attribute-defined-outside-init
        self.arch: DynamicQuantumArchitecture = sample_move_architecture

    @property
    def unsafe_circuit(self):
        """A circuit with moves and an unsafe prx"""
        instructions = (
            Instruction(
                name='prx',
                qubits=('QB1',),
                args={'phase_t': 0.3, 'angle_t': -0.2},
            ),
            Instruction(
                name='move',
                qubits=('QB3', 'COMP_R'),
                args={},
            ),
            Instruction(
                name='prx',
                qubits=('QB3',),
                args={'phase_t': 0.3, 'angle_t': -0.2},
            ),
            Instruction(
                name='move',
                qubits=('QB3', 'COMP_R'),
                args={},
            ),
        )
        return Circuit(name='unsafe', instructions=instructions)

    @property
    def safe_circuit(self):
        """A partially transpiled circuit."""
        instructions = (
            Instruction(
                name='prx',
                qubits=('QB1',),
                args={'phase_t': 0.3, 'angle_t': -0.2},
            ),
            Instruction(
                name='cz',
                qubits=('QB1', 'COMP_R'),
                args={},
            ),
            Instruction(
                name='move',
                qubits=('QB3', 'COMP_R'),
                args={},
            ),
            Instruction(
                name='cz',
                qubits=('QB2', 'COMP_R'),
                args={},
            ),
            Instruction(
                name='move',
                qubits=('QB3', 'COMP_R'),
                args={},
            ),
            Instruction(
                name='cz',
                qubits=('QB3', 'QB1'),
                args={},
            ),
        )
        return Circuit(name='safe', instructions=instructions)

    @property
    def simple_circuit(self):
        """An untranspiled circuit."""
        instructions = (
            Instruction(
                name='prx',
                qubits=('QB1',),
                args={'phase_t': 0.3, 'angle_t': -0.2},
            ),
            Instruction(
                name='cz',
                qubits=('QB1', 'COMP_R'),
                args={},
            ),
            Instruction(
                name='cz',
                qubits=('QB2', 'COMP_R'),
                args={},
            ),
            Instruction(
                name='cz',
                qubits=('QB3', 'QB1'),
                args={},
            ),
            Instruction(
                name='prx',
                qubits=('QB3',),
                args={'phase_t': 0.3, 'angle_t': -0.2},
            ),
        )
        return Circuit(name='safe', instructions=instructions)

    @property
    def mapped_circuit(self):
        """A circuit with different qubit names and a qubit mapping."""
        instructions = (
            Instruction(
                name='prx',
                qubits=('A',),
                args={'phase_t': 0.3, 'angle_t': -0.2},
            ),
            Instruction(
                name='cz',
                qubits=('A', 'B'),
                args={},
            ),
        )
        return Circuit(name='mapped', instructions=instructions), {'A': 'QB3', 'B': 'QB1'}

    @property
    def ambiguous_circuit(self):
        """A circuit that is unclear how to compile it because there is only one move"""
        instructions = (
            Instruction(
                name='prx',
                qubits=('QB1',),
                args={'phase_t': 0.3, 'angle_t': -0.2},
            ),
            Instruction(
                name='cz',
                qubits=('QB1', 'COMP_R'),
                args={},
            ),
            Instruction(
                name='move',
                qubits=('QB3', 'COMP_R'),
                args={},
            ),
            Instruction(
                name='cz',
                qubits=('QB2', 'COMP_R'),
                args={},
            ),
            Instruction(
                name='cz',
                qubits=('QB3', 'QB1'),
                args={},
            ),
        )
        return Circuit(name='ambiguous', instructions=instructions)

    def insert(
        self,
        circuit: Circuit,
        arg=None,
        qb_map=None,
    ):
        kwargs = {} if arg is None else {'existing_moves': arg}
        return transpile_insert_moves(circuit, arch=self.arch, qubit_mapping=qb_map, **kwargs)

    def check_equiv_without_moves(self, c1: Circuit, c2: Circuit):
        c1 = transpile_remove_moves(c1)
        c2 = transpile_remove_moves(c2)
        for i1, i2 in zip(c1.instructions, c2.instructions):
            if i1.name != i2.name or i1.args != i2.args:
                return False
            if i1.qubits != i2.qubits:
                if i1.name != 'cz':
                    return False
                if not all(q1 == q2 for q1, q2 in zip(i1.qubits, reversed(i2.qubits))):
                    return False
        return True

    def assert_valid_circuit(self, circuit: Circuit, qb_map=None):
        # pylint: disable=no-member
        if qb_map:
            for q in self.arch.qubits:
                if q not in qb_map.values():
                    qb_map[q] = q
        IQMClient._validate_circuit_instructions(self.arch, [circuit], qubit_mapping=qb_map)

    def check_moves_in_circuit(self, circuit: Circuit, moves: tuple[Instruction]):
        idx = 0
        for instr in circuit.instructions:
            if idx < len(moves) and moves[idx] == instr:
                idx += 1
        return idx == len(moves)

    @pytest.mark.parametrize('option', ExistingMoveHandlingOptions)
    def test_no_moves_supported(self, sample_dynamic_architecture, option):
        """Tests transpiler for architectures without a resonator"""
        c1 = transpile_insert_moves(self.simple_circuit, sample_dynamic_architecture, existing_moves=option)
        # no changes
        assert c1 == self.simple_circuit
        # MOVEs in the circuit cause an error
        with pytest.raises(ValueError):
            _ = transpile_insert_moves(self.safe_circuit, sample_dynamic_architecture, existing_moves=option)

    def test_unspecified(self):
        """Tests transpiler in case the handling option is not specified."""
        c1 = self.insert(self.simple_circuit)
        self.assert_valid_circuit(c1)
        assert self.check_equiv_without_moves(c1, self.simple_circuit)

        c2 = self.insert(self.safe_circuit)
        assert self.check_equiv_without_moves(c2, self.safe_circuit)

    def test_normal_usage(self, sample_circuit: Circuit):
        """Tests basic usage of the transpile method"""
        for handling_option in ExistingMoveHandlingOptions:
            c1 = self.insert(self.simple_circuit, handling_option)
            self.assert_valid_circuit(c1)
            assert self.check_equiv_without_moves(c1, self.simple_circuit)
            with pytest.raises(CircuitTranspilationError):
                self.insert(sample_circuit, handling_option)  # untranspiled circuit

    def test_keep(self):
        """Tests special cases for the KEEP option"""
        moves = tuple(i for i in self.safe_circuit.instructions if i.name == 'move')
        c1 = self.insert(self.safe_circuit, ExistingMoveHandlingOptions.KEEP)
        self.assert_valid_circuit(c1)
        assert self.check_moves_in_circuit(c1, moves)

        with pytest.raises(CircuitTranspilationError):
            self.insert(self.unsafe_circuit, ExistingMoveHandlingOptions.KEEP)

        with pytest.raises(CircuitTranspilationError):
            self.insert(self.ambiguous_circuit, ExistingMoveHandlingOptions.KEEP)

    def test_remove(self):
        """Tests if removing works as intended."""
        for c in [self.safe_circuit, self.unsafe_circuit, self.ambiguous_circuit]:
            moves = tuple(i for i in c.instructions if i.name == 'move')
            c1 = transpile_remove_moves(c)
            assert not self.check_moves_in_circuit(c1, moves)
            c1_with = self.insert(c1, ExistingMoveHandlingOptions.REMOVE)
            c1_direct = self.insert(c, ExistingMoveHandlingOptions.REMOVE)
            assert c1_with == c1_direct
            assert self.check_equiv_without_moves(c1, c1_with)
            assert self.check_equiv_without_moves(c1, c1_direct)

    def test_trust(self):
        """Tests if trust works as intended"""
        moves = tuple(i for i in self.safe_circuit.instructions if i.name == 'move')
        c1 = self.insert(self.safe_circuit, ExistingMoveHandlingOptions.TRUST)
        self.assert_valid_circuit(c1)
        assert self.check_moves_in_circuit(c1, moves)

        moves2 = tuple(i for i in self.unsafe_circuit.instructions if i.name == 'move')
        c2 = self.insert(self.unsafe_circuit, ExistingMoveHandlingOptions.TRUST)
        self.assert_valid_circuit(c2)
        assert self.check_moves_in_circuit(c2, moves2)

        moves3 = tuple(i for i in self.ambiguous_circuit.instructions if i.name == 'move')
        c3 = self.insert(self.ambiguous_circuit, ExistingMoveHandlingOptions.TRUST)
        self.assert_valid_circuit(c3)
        assert self.check_moves_in_circuit(c3, moves3)

    def test_with_qubit_map(self):
        """Test if qubit mapping works as intended"""
        for handling_option in ExistingMoveHandlingOptions:
            circuit, qb_map = self.mapped_circuit
            c1 = self.insert(circuit, handling_option, qb_map)
            self.assert_valid_circuit(c1, qb_map)
            assert self.check_equiv_without_moves(c1, circuit)

    def test_multiple_resonators(self, sample_move_architecture):
        """Test if multiple resonators works."""
        # add MOVE loci to the architecture
        default_move_impl = sample_move_architecture.gates['move'].default_implementation
        sample_move_architecture.gates['move'].implementations[default_move_impl].loci += (('QB1', 'COMP_R2'),)

        # Test with bad architecture
        circuit = Circuit(
            name='multi resonators',
            instructions=(
                Instruction(name='cz', qubits=('QB1', 'QB2'), args={}),
                Instruction(name='cz', qubits=('QB2', 'QB3'), args={}),
                Instruction(name='cz', qubits=('QB1', 'QB3'), args={}),
            ),
        )
        with pytest.raises(CircuitTranspilationError, match='Unable to find a valid resonator-qubit pair'):
            # CZ(QB1, QB2) is not possible
            # Create a new copy of the DQA to ensure the cached properties are computed only for this architecture.
            bad_architecture = sample_move_architecture.model_copy(deep=True)
            transpiled_circuit = transpile_insert_moves(circuit, bad_architecture)

        # Add the CZ loci to the architecture make it ok for this circuit.
        default_cz_impl = sample_move_architecture.gates['cz'].default_implementation
        sample_move_architecture.gates['cz'].implementations[default_cz_impl].loci += tuple(
            (qb, 'COMP_R2') for qb in sample_move_architecture.components
        )

        # Create a new copy of the DQA to ensure the cached properties are computed only for this architecture.
        good_architecture = sample_move_architecture.model_copy(deep=True)
        transpiled_circuit = transpile_insert_moves(circuit, good_architecture)
        IQMClient._validate_circuit_instructions(good_architecture, [transpiled_circuit])

        print(transpiled_circuit)

        assert self.check_equiv_without_moves(circuit, transpiled_circuit)

    def test_circuit_on_nonexisting_qubits(self):
        """Test for a broken circuit on a non-existing qubit in the architecture."""
        c = Circuit(
            name='QB5 does not exist',
            instructions=(
                Instruction(
                    name='prx',
                    qubits=('QB5',),
                    args={'phase_t': 0.3, 'angle_t': -0.2},
                ),
            ),
        )
        with pytest.raises(CircuitTranspilationError):
            self.insert(c, qb_map={'QB5': 'QB5'})

    def test_unavailable_cz(self):
        """Test for unavailable CZ gates. This test reproduces the bug COMP-1485."""
        c = Circuit(
            name='bell',
            instructions=(  # prx uses wrong values for the H gate, but that's not the point of this test
                Instruction(
                    name='prx',
                    qubits=('QB1',),
                    args={'phase_t': 0.3, 'angle_t': -0.2},
                ),
                Instruction(
                    name='prx',
                    qubits=('QB2',),
                    args={'phase_t': 0.3, 'angle_t': -0.2},
                ),
                Instruction(
                    name='cz',
                    qubits=('QB1', 'QB2'),
                    args={},
                ),
                Instruction(
                    name='prx',
                    qubits=('QB2',),
                    args={'phase_t': 0.3, 'angle_t': -0.2},
                ),
            ),
        )
        c2 = Circuit(
            name='bell',
            instructions=(  # prx uses wrong values for the H gate, but that's not the point of this test
                Instruction(
                    name='prx',
                    qubits=('QB1',),
                    args={'phase_t': 0.3, 'angle_t': -0.2},
                ),
                Instruction(
                    name='prx',
                    qubits=('QB2',),
                    args={'phase_t': 0.3, 'angle_t': -0.2},
                ),
                Instruction(
                    name='cz',
                    qubits=('QB2', 'QB1'),  # Swapped qubits
                    args={},
                ),
                Instruction(
                    name='prx',
                    qubits=('QB2',),
                    args={'phase_t': 0.3, 'angle_t': -0.2},
                ),
            ),
        )
        arch = DynamicQuantumArchitecture(
            calibration_set_id=UUID('0c5a5624-2faf-4885-888c-805af891479c'),
            qubits=['QB1', 'QB2'],
            computational_resonators=['COMP_R'],
            gates={
                'prx': GateInfo(
                    implementations={'drag_gaussian': GateImplementationInfo(loci=(('QB1',), ('QB2',)))},
                    default_implementation='drag_gaussian',
                    override_default_implementation={},
                ),
                'cz': GateInfo(
                    implementations={'tgss': GateImplementationInfo(loci=(('QB2', 'COMP_R'),))},
                    default_implementation='tgss',
                    override_default_implementation={},
                ),
                'move': GateInfo(
                    implementations={'tgss_crf': GateImplementationInfo(loci=(('QB1', 'COMP_R'), ('QB2', 'COMP_R')))},
                    default_implementation='tgss_crf',
                    override_default_implementation={},
                ),
                'measure': GateInfo(
                    implementations={'constant': GateImplementationInfo(loci=(('QB1',), ('QB2',)))},
                    default_implementation='constant',
                    override_default_implementation={},
                ),
            },
        )
        circuits = [transpile_insert_moves(c, arch=arch), transpile_insert_moves(c2, arch=arch)]
        IQMClient._validate_circuit_instructions(arch, circuits)

    @pytest.mark.parametrize(
        'loci', [(qb1, qb2) for qb1 in ['QB1', 'QB2', 'QB3'] for qb2 in ['QB1', 'QB2', 'QB3'] if qb1 != qb2]
    )
    def test_pass_always_picks_correct_move_gate(self, loci):
        circuit = Circuit(
            name='test',
            instructions=(Instruction(name='cz', qubits=loci, args={}),),
        )
        if set(loci) == {'QB1', 'QB2'}:
            # There is no MOVE gate available between this pair of qubits
            with pytest.raises(
                CircuitTranspilationError,
                match=re.escape(
                    f'Unable to insert MOVE gates because none of the qubits {loci} share a resonator. This can be '
                    + 'resolved by routing the circuit first without resonators.'
                ),
            ):
                transpile_insert_moves(circuit, self.arch)
        else:
            transpiled_circuit = transpile_insert_moves(circuit, self.arch)
            IQMClient._validate_circuit_instructions(self.arch, [transpiled_circuit])


class TestResonatorStateTracker:
    def test_apply_move(self, sample_dynamic_architecture, sample_move_architecture):
        # Check handling of an architecture without a resonator
        no_move_status = ResonatorStateTracker.from_dynamic_architecture(sample_dynamic_architecture)
        assert not no_move_status.supports_move
        with pytest.raises(CircuitTranspilationError):
            no_move_status.apply_move('QB1', 'QB2')
        # Check handling of an architecture with resonator
        status = ResonatorStateTracker.from_dynamic_architecture(sample_move_architecture)
        assert status.supports_move
        status.apply_move('QB3', 'COMP_R')
        assert status.res_state_owner['COMP_R'] == 'QB3'
        status.apply_move('QB3', 'COMP_R')
        assert status.res_state_owner['COMP_R'] == 'COMP_R'
        with pytest.raises(CircuitTranspilationError):
            status.apply_move('QB1', 'COMP_R')
        with pytest.raises(CircuitTranspilationError):
            status.apply_move('QB1', 'QB2')
        status.res_state_owner['COMP_R'] = 'QB1'
        with pytest.raises(CircuitTranspilationError):
            status.apply_move('QB3', 'COMP_R')

    def test_create_move_instructions(self, sample_move_architecture):
        default_move_impl = sample_move_architecture.gates['move'].default_implementation
        sample_move_architecture.gates['move'].implementations[default_move_impl].loci += (('QB1', 'COMP_R'),)
        status = ResonatorStateTracker.from_dynamic_architecture(sample_move_architecture)
        instr = Instruction(name='move', qubits=('QB3', 'COMP_R'), args={})
        # Check insertion
        gen_instr = tuple(status.create_move_instructions('QB3', 'COMP_R'))
        assert len(gen_instr) == 1
        assert gen_instr[0] == instr
        assert status.res_state_owner['COMP_R'] == 'QB3'
        gen_instr = tuple(status.create_move_instructions('QB3', 'COMP_R'))
        assert len(gen_instr) == 1
        assert gen_instr[0] == instr
        assert status.res_state_owner['COMP_R'] == 'COMP_R'
        status.res_state_owner['COMP_R'] = 'QB1'
        # Check removal
        gen_instr = tuple(status.create_move_instructions('QB3', 'COMP_R'))
        assert len(gen_instr) == 2
        assert gen_instr[0] == Instruction(name='move', qubits=('QB1', 'COMP_R'), args={})
        assert gen_instr[1] == instr
        assert status.res_state_owner['COMP_R'] == 'QB3'

    def test_reset_as_move_instructions(self, sample_move_architecture):
        status = ResonatorStateTracker.from_dynamic_architecture(sample_move_architecture)
        # No reset needed
        gen_instr = tuple(status.reset_as_move_instructions())
        assert len(gen_instr) == 0
        # Reset with argument
        status.apply_move('QB3', 'COMP_R')
        gen_instr = tuple(status.reset_as_move_instructions(['COMP_R']))
        assert len(gen_instr) == 1
        assert gen_instr[0] == Instruction(name='move', qubits=('QB3', 'COMP_R'), args={})
        assert status.res_state_owner['COMP_R'] == 'COMP_R'
        # Reset without arguments
        status.apply_move('QB3', 'COMP_R')
        gen_instr = tuple(status.reset_as_move_instructions())
        assert len(gen_instr) == 1
        assert gen_instr[0] == Instruction(name='move', qubits=('QB3', 'COMP_R'), args={})
        assert status.res_state_owner['COMP_R'] == 'COMP_R'

    def test_available_resonators_to_move(self, sample_move_architecture):
        components = sample_move_architecture.components
        status = ResonatorStateTracker.from_dynamic_architecture(sample_move_architecture)
        assert status.available_resonators_to_move(components) == {
            'COMP_R': [],
            'COMP_R2': [],
            'QB1': [],
            'QB2': [],
            'QB3': ['COMP_R'],
        }

    def test_qubits_in_resonator(self, sample_move_architecture):
        components = sample_move_architecture.components
        status = ResonatorStateTracker.from_dynamic_architecture(sample_move_architecture)
        assert status.resonators_holding_qubits(components) == []
        status.apply_move('QB3', 'COMP_R')
        assert status.resonators_holding_qubits(components) == ['COMP_R']

    def test_choose_move_pair(self, sample_move_architecture):
        status = ResonatorStateTracker.from_dynamic_architecture(sample_move_architecture)
        with pytest.raises(CircuitTranspilationError):
            status.choose_move_pair(['QB1', 'QB2'], [])
        resonator_candidates = status.choose_move_pair(
            ['QB1', 'QB2', 'QB3'],
            [
                Instruction(name='cz', qubits=('QB2', 'QB3'), args={}),
                Instruction(name='prx', qubits=('QB2',), args={'phase_t': 0.3, 'angle_t': -0.2}),
                Instruction(name='prx', qubits=('QB3',), args={'phase_t': 0.3, 'angle_t': -0.2}),
            ],
        )
        r, q = resonator_candidates[0]
        assert r == 'COMP_R'
        assert q == 'QB3'

    def test_map_resonators_in_locus(self, sample_move_architecture):
        components = sample_move_architecture.components
        status = ResonatorStateTracker.from_dynamic_architecture(sample_move_architecture)
        status.apply_move('QB3', 'COMP_R')
        assert status.map_resonators_in_locus(components) == ('QB3', 'COMP_R2', 'QB1', 'QB2', 'QB3')


def test_simplified_architecture(sample_move_architecture):
    """Resonators and MOVE gates are eliminated, q-r gates are replaced with q-q gates."""
    simple = simplified_architecture(sample_move_architecture)

    assert simple.qubits == sample_move_architecture.qubits
    assert not simple.computational_resonators

    assert len(simple.gates) == 3
    assert 'move' not in simple.gates
    assert simple.gates['measure'].loci == (('QB1',), ('QB2',), ('QB3',))
    assert simple.gates['prx'].loci == (('QB1',), ('QB2',), ('QB3',))
    assert simple.gates['cz'].loci == (
        ('QB1', 'QB3'),
        (
            'QB2',
            'QB3',
        ),
    )


def test_simplified_architecture_no_resonators(sample_dynamic_architecture):
    """Architectures with no resonators are not changed."""
    simple = simplified_architecture(sample_dynamic_architecture)
    assert simple == sample_dynamic_architecture
