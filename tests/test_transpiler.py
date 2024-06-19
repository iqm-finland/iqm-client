from typing import Any

import pytest

from iqm.iqm_client import (
    Circuit,
    CircuitExecutionError,
    ExistingMoveHandlingOptions,
    Instruction,
    IQMClient,
    QuantumArchitecture,
    QuantumArchitectureSpecification,
    transpile_insert_moves,
    transpile_remove_moves,
)
from iqm.iqm_client.transpile import ResonatorStateTracker


class TestNaiveMoveTranspiler:
    @pytest.fixture(autouse=True)
    def init_arch(self, sample_move_architecture: dict[str, Any]):
        # pylint: disable=attribute-defined-outside-init
        self.arch: QuantumArchitectureSpecification = QuantumArchitecture(
            **sample_move_architecture
        ).quantum_architecture

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
        return transpile_insert_moves(circuit, arch=self.arch, existing_moves=arg, qubit_mapping=qb_map)

    def remove(self, circuit: Circuit):
        return transpile_remove_moves(circuit)

    def check_equiv_without_moves(self, c1: Circuit, c2: Circuit):
        c1 = self.remove(c1)
        c2 = self.remove(c2)
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

    def test_no_moves_supported(self, sample_quantum_architecture: dict[str, Any]):
        """Tests transpiler for architectures without a resonator"""
        arch = QuantumArchitecture(**sample_quantum_architecture).quantum_architecture
        for option in ExistingMoveHandlingOptions:
            c1 = transpile_insert_moves(self.simple_circuit, arch, existing_moves=option)
            assert c1 == self.simple_circuit
            if option != ExistingMoveHandlingOptions.REMOVE:
                with pytest.raises(ValueError):
                    _ = transpile_insert_moves(self.safe_circuit, arch, existing_moves=option)
            else:
                c2 = transpile_insert_moves(self.safe_circuit, arch, existing_moves=option)
                assert self.check_equiv_without_moves(self.safe_circuit, c2)

    def test_unspecified(self):
        """Tests transpiler in case the handling option is not specified."""
        c1 = self.insert(self.simple_circuit)
        self.assert_valid_circuit(c1)
        assert self.check_equiv_without_moves(c1, self.simple_circuit)
        with pytest.warns(UserWarning):
            c2 = self.insert(self.safe_circuit)
            assert self.check_equiv_without_moves(c2, self.safe_circuit)

    def test_normal_usage(self, sample_circuit: Circuit):
        """Tests basic usage of the transpile method"""
        for handling_option in ExistingMoveHandlingOptions:
            c1 = self.insert(self.simple_circuit, handling_option)
            self.assert_valid_circuit(c1)
            assert self.check_equiv_without_moves(c1, self.simple_circuit)
            with pytest.raises(CircuitExecutionError):
                self.insert(sample_circuit, handling_option)  # untranspiled circuit

    def test_keep(self):
        """Tests special cases for the KEEP option"""
        moves = tuple(i for i in self.safe_circuit.instructions if i.name == 'move')
        c1 = self.insert(self.safe_circuit, ExistingMoveHandlingOptions.KEEP)
        self.assert_valid_circuit(c1)
        assert self.check_moves_in_circuit(c1, moves)

        with pytest.raises(CircuitExecutionError):
            self.insert(self.unsafe_circuit, ExistingMoveHandlingOptions.KEEP)

        with pytest.raises(CircuitExecutionError):
            self.insert(self.ambiguous_circuit, ExistingMoveHandlingOptions.KEEP)

    def test_remove(self):
        """Tests if removing works as intended."""
        for c in [self.safe_circuit, self.unsafe_circuit, self.ambiguous_circuit]:
            moves = tuple(i for i in c.instructions if i.name == 'move')
            c1 = self.remove(c)
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

    def test_multiple_resonators(self, sample_move_architecture: dict[str, Any]):
        """Test if multiple resonators works."""
        sample_move_architecture['quantum_architecture']['qubits'].append('COMP_R2')
        sample_move_architecture['quantum_architecture']['operations']['move'].append(['QB1', 'COMP_R2'])
        # Test with bad architecture
        arch = QuantumArchitecture(**sample_move_architecture).quantum_architecture
        circuit = Circuit(
            name='multi resonators',
            instructions=(
                Instruction(name='cz', qubits=('QB1', 'QB2'), args={}),
                Instruction(name='cz', qubits=('QB2', 'QB3'), args={}),
                Instruction(name='cz', qubits=('QB1', 'QB3'), args={}),
            ),
        )
        with pytest.raises(CircuitExecutionError):
            transpiled_circuit = transpile_insert_moves(circuit, arch)

        # Add the necessary CZ gates to make it a good architecture.
        sample_move_architecture['quantum_architecture']['operations']['cz'] += (
            [qb, 'COMP_R2'] for qb in sample_move_architecture['quantum_architecture']['qubits']
        )
        arch = QuantumArchitecture(**sample_move_architecture).quantum_architecture
        transpiled_circuit = transpile_insert_moves(circuit, arch)
        IQMClient._validate_circuit_instructions(arch, [transpiled_circuit])

        print(transpiled_circuit)

        assert self.check_equiv_without_moves(circuit, transpiled_circuit)

    def test_broken_circuit(self):
        """Test for a broken circuit"""
        c = Circuit(
            name='broken',
            instructions=(
                Instruction(
                    name='prx',
                    qubits=('QB5',),
                    args={'phase_t': 0.3, 'angle_t': -0.2},
                ),
            ),
        )
        with pytest.raises(CircuitExecutionError):
            self.insert(c, qb_map={'QB5': 'QB5'})


class TestResonatorStateTracker:
    alt_qubit_names = {'COMP_R': 'A', 'QB1': 'B', 'QB3': 'C'}

    def test_apply_move(self, sample_quantum_architecture: dict[str, Any], sample_move_architecture: dict[str, Any]):
        # Check handling of an architecture without a resonator
        no_move_arch = QuantumArchitecture(**sample_quantum_architecture).quantum_architecture
        arch = QuantumArchitecture(**sample_move_architecture).quantum_architecture
        no_move_status = ResonatorStateTracker.from_quantum_architecture_specification(no_move_arch)
        assert not no_move_status.supports_move
        with pytest.raises(CircuitExecutionError):
            no_move_status.apply_move('QB1', 'QB2')
        # Check handling of an architecture with resonator
        status = ResonatorStateTracker.from_quantum_architecture_specification(arch)
        assert status.supports_move
        status.apply_move('QB3', 'COMP_R')
        assert status.res_qb_map['COMP_R'] == 'QB3'
        status.apply_move('QB3', 'COMP_R')
        assert status.res_qb_map['COMP_R'] == 'COMP_R'
        with pytest.raises(CircuitExecutionError):
            status.apply_move('QB1', 'COMP_R')
        with pytest.raises(CircuitExecutionError):
            status.apply_move('QB1', 'QB2')
        status.res_qb_map['COMP_R'] = 'QB1'
        with pytest.raises(CircuitExecutionError):
            status.apply_move('QB3', 'COMP_R')

    def test_create_move_instructions(self, sample_move_architecture: dict[str, Any]):
        sample_move_architecture['quantum_architecture']['operations']['move'].append(['QB1', 'COMP_R'])
        arch = QuantumArchitecture(**sample_move_architecture).quantum_architecture
        status = ResonatorStateTracker.from_quantum_architecture_specification(arch)
        instr = Instruction(name='move', qubits=('QB3', 'COMP_R'), args={})
        # Check insertion without and with apply_move
        gen_instr = tuple(status.create_move_instructions('QB3', 'COMP_R', apply_move=False))
        assert len(gen_instr) == 1
        assert gen_instr[0] == instr
        assert status.res_qb_map['COMP_R'] == 'COMP_R'
        gen_instr = tuple(status.create_move_instructions('QB3', 'COMP_R', apply_move=True))
        assert len(gen_instr) == 1
        assert gen_instr[0] == instr
        assert status.res_qb_map['COMP_R'] == 'QB3'
        status.res_qb_map['COMP_R'] = 'QB1'
        # Check removal without and with apply_move
        gen_instr = tuple(status.create_move_instructions('QB3', 'COMP_R', apply_move=False))
        assert len(gen_instr) == 2
        assert gen_instr[0] == Instruction(name='move', qubits=('QB1', 'COMP_R'), args={})
        assert gen_instr[1] == instr
        # Check with a qubit mapping
        gen_instr = tuple(
            status.create_move_instructions('QB3', 'COMP_R', apply_move=True, alt_qubit_names=self.alt_qubit_names)
        )
        assert len(gen_instr) == 2
        assert gen_instr[0] == Instruction(name='move', qubits=('B', 'A'), args={})
        assert gen_instr[1] == Instruction(name='move', qubits=('C', 'A'), args={})
        assert status.res_qb_map['COMP_R'] == 'QB3'

    def test_reset_as_move_instructions(self, sample_move_architecture: dict[str, Any]):
        arch = QuantumArchitecture(**sample_move_architecture).quantum_architecture
        status = ResonatorStateTracker.from_quantum_architecture_specification(arch)
        # No reset needed
        gen_instr = tuple(status.reset_as_move_instructions())
        assert len(gen_instr) == 0
        # Reset with argument and not apply_move
        status.apply_move('QB3', 'COMP_R')
        gen_instr = tuple(status.reset_as_move_instructions(['COMP_R'], apply_move=False))
        assert len(gen_instr) == 1
        assert gen_instr[0] == Instruction(name='move', qubits=('QB3', 'COMP_R'), args={})
        assert status.res_qb_map['COMP_R'] == 'QB3'
        # Reset without argument, with qubit mapping, and not apply_move
        gen_instr = tuple(status.reset_as_move_instructions(apply_move=False, alt_qubit_names=self.alt_qubit_names))
        assert len(gen_instr) == 1
        assert gen_instr[0] == Instruction(name='move', qubits=('C', 'A'), args={})
        assert status.res_qb_map['COMP_R'] == 'QB3'
        # Reset without arguments and with apply_move
        gen_instr = tuple(status.reset_as_move_instructions(apply_move=True))
        assert len(gen_instr) == 1
        assert gen_instr[0] == Instruction(name='move', qubits=('QB3', 'COMP_R'), args={})
        assert status.res_qb_map['COMP_R'] == 'COMP_R'

    def test_available_resonators_to_move(self, sample_move_architecture: dict[str, Any]):
        qubits = sample_move_architecture['quantum_architecture']['qubits']
        arch: QuantumArchitectureSpecification = QuantumArchitecture(**sample_move_architecture).quantum_architecture
        status = ResonatorStateTracker.from_quantum_architecture_specification(arch)
        assert status.available_resonators_to_move(qubits) == {
            'COMP_R': [],
            'QB1': [],
            'QB2': [],
            'QB3': ['COMP_R'],
        }

    def test_qubits_in_resonator(self, sample_move_architecture: dict[str, Any]):
        qubits = sample_move_architecture['quantum_architecture']['qubits']
        arch: QuantumArchitectureSpecification = QuantumArchitecture(**sample_move_architecture).quantum_architecture
        status = ResonatorStateTracker.from_quantum_architecture_specification(arch)
        assert status.resonators_holding_qubits(qubits) == []
        status.apply_move('QB3', 'COMP_R')
        assert status.resonators_holding_qubits(qubits) == ['COMP_R']

    def test_choose_move_pair(self, sample_move_architecture: dict[str, Any]):
        arch: QuantumArchitectureSpecification = QuantumArchitecture(**sample_move_architecture).quantum_architecture
        status = ResonatorStateTracker.from_quantum_architecture_specification(arch)
        with pytest.raises(CircuitExecutionError):
            status.choose_move_pair(['QB1', 'QB2'], [])
        resonator_candidates = status.choose_move_pair(
            ['QB1', 'QB2', 'QB3'], [['cz', 'QB2', 'QB3'], ['prx', 'QB2'], ['prx', 'QB3']]
        )
        r, q, _ = resonator_candidates[0]
        assert r == 'COMP_R'
        assert q == 'QB3'

    def test_update_state_in_resonator(self, sample_move_architecture: dict[str, Any]):
        qubits = sample_move_architecture['quantum_architecture']['qubits']
        arch: QuantumArchitectureSpecification = QuantumArchitecture(**sample_move_architecture).quantum_architecture
        status = ResonatorStateTracker.from_quantum_architecture_specification(arch)
        status.apply_move('QB3', 'COMP_R')
        assert status.update_qubits_in_resonator(qubits) == ['QB3', 'QB1', 'QB2', 'QB3']
