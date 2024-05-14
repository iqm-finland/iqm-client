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


class TestNaiveMoveTranspiler:
    @pytest.fixture(autouse=True)
    def init_arch(self, sample_move_architecture):
        # pylint: disable=attribute-defined-outside-init
        self.arch: QuantumArchitectureSpecification = QuantumArchitecture(
            **sample_move_architecture
        ).quantum_architecture

    @property
    def unsafe_circuit(self):
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
        )
        return Circuit(name='safe', instructions=instructions)

    @property
    def mapped_circuit(self):
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
        circuit,
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

    def assert_valid_circuit(self, circuit, qb_map=None):
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

    def test_unspecified(self):
        c1 = self.insert(self.simple_circuit)
        self.assert_valid_circuit(c1)
        assert self.check_equiv_without_moves(c1, self.simple_circuit)
        with pytest.warns(UserWarning):
            c2 = self.insert(self.safe_circuit)
            assert self.check_equiv_without_moves(c2, self.safe_circuit)

    def test_normal_usage(self, sample_circuit):
        for handling_option in ExistingMoveHandlingOptions:
            c1 = self.insert(self.simple_circuit, handling_option)
            self.assert_valid_circuit(c1)
            assert self.check_equiv_without_moves(c1, self.simple_circuit)
            with pytest.raises(CircuitExecutionError):
                self.insert(sample_circuit, handling_option)  # untranspiled circuit

    def test_keep(self):
        moves = tuple(i for i in self.safe_circuit.instructions if i.name == 'move')
        c1 = self.insert(self.safe_circuit, ExistingMoveHandlingOptions.KEEP)
        self.assert_valid_circuit(c1)
        assert self.check_moves_in_circuit(c1, moves)
        with pytest.raises(CircuitExecutionError):
            self.insert(self.unsafe_circuit, ExistingMoveHandlingOptions.KEEP)

        moves3 = tuple(i for i in self.safe_circuit.instructions if i.name == 'move')
        c3 = self.insert(self.ambiguous_circuit, ExistingMoveHandlingOptions.KEEP)
        self.assert_valid_circuit(c3)
        assert self.check_moves_in_circuit(c3, moves3)

    def test_remove(self):
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
        moves = tuple(i for i in self.safe_circuit.instructions if i.name == 'move')
        c1 = self.insert(self.safe_circuit, ExistingMoveHandlingOptions.TRUST)
        self.assert_valid_circuit(c1)
        assert self.check_moves_in_circuit(c1, moves)

        c2 = self.insert(self.unsafe_circuit, ExistingMoveHandlingOptions.TRUST)
        with pytest.raises(CircuitExecutionError):
            self.assert_valid_circuit(c2)

        moves3 = tuple(i for i in self.safe_circuit.instructions if i.name == 'move')
        c3 = self.insert(self.ambiguous_circuit, ExistingMoveHandlingOptions.TRUST)
        self.assert_valid_circuit(c3)
        assert self.check_moves_in_circuit(c3, moves3)

    def test_with_qubit_map(self):
        for handling_option in ExistingMoveHandlingOptions:
            circuit, qb_map = self.mapped_circuit
            c1 = self.insert(circuit, handling_option, qb_map)
            self.assert_valid_circuit(c1, qb_map)
            assert self.check_equiv_without_moves(c1, circuit)
