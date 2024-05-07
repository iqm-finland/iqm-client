import pytest

from iqm.iqm_client import transpile_insert_moves, transpile_remove_moves, ExistingMoveHandlingOptions, Circuit, Instruction, QuantumArchitecture, IQMClient, CircuitExecutionError

class TestNaiveMoveTranspiler:

    @pytest.fixture(autouse=True)
    def init_arch(self, sample_move_architecture):
        self.arch = QuantumArchitecture(**sample_move_architecture).quantum_architecture

    @property
    def unsafe_circuit(self):

        instructions=(   
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
        instructions=(
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
    def ambiguous_circuit(self):
        instructions=(
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
        
    
    @pytest.mark.parametrize('qubits', [['QB1', 'QB2'], ['QB2'], ['QB1', 'QB2', 'QB3'], ['QB3', 'QB1'], ['QB1']])
    def insert(self, circuit, arg=None, qb_map=None, ):
        return transpile_insert_moves(circuit, arch=self.arch, existing_moves=arg, qubit_mapping=qb_map)
    
    def remove(self, circuit:Circuit):
        return transpile_remove_moves(circuit)
    
    def check_equiv_without_moves(self, c_with: Circuit, c_without: Circuit):
        return c_without == self.remove(c_with)
    
    def assert_valid_circuit(self, circuit, qb_map=None):
        IQMClient._validate_circuit_instructions(self.arch, [circuit], qubit_mapping=qb_map)

    def check_moves_in_circuit(self, circuit: Circuit, moves: tuple[Instruction]):
        idx = 0
        for instr in circuit.instructions:
            if idx < len(moves) and moves[idx] == instr:
                idx += 1
        return idx == len(moves)
    
    def test_unspecified(self, sample_circuit):
        c1=self.insert(sample_circuit)
        self.assert_valid_circuit(c1)
        assert self.check_equiv_without_moves(c1, sample_circuit) 
        with pytest.warns(UserWarning):
            c2 = self.insert(self.safe_circuit)
            assert self.check_equiv_without_moves(c2, self.safe_circuit)

    def test_normal_usage(self, sample_circuit):
        for handling_option in ExistingMoveHandlingOptions:
            c1=self.insert(sample_circuit, handling_option)
            self.assert_valid_circuit(c1)
            assert self.check_equiv_without_moves(c1, sample_circuit)

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
        moves = tuple(i for i in self.safe_circuit.instructions if i.name == 'move')
        c1 = self.insert(self.safe_circuit, ExistingMoveHandlingOptions.REMOVE)
        self.assert_valid_circuit(c1)
        assert not self.check_moves_in_circuit(c1, moves)
        moves2 = tuple(i for i in self.unsafe_circuit.instructions if i.name == 'move')
        c2 = self.insert(self.unsafe_circuit, ExistingMoveHandlingOptions.REMOVE)
        self.assert_valid_circuit(c2)
        assert not self.check_moves_in_circuit(c2, moves2)
        moves3 = tuple(i for i in self.safe_circuit.instructions if i.name == 'move')
        c3 = self.insert(self.ambiguous_circuit, ExistingMoveHandlingOptions.REMOVE)
        self.assert_valid_circuit(c3)
        assert not self.check_moves_in_circuit(c3, moves3) 
  
    def test_trust(self):
        moves = tuple(i for i in self.safe_circuit.instructions if i.name == 'move')
        c1 = self.insert(self.safe_circuit, ExistingMoveHandlingOptions.TRUST)
        self.assert_valid_circuit(c1)
        assert self.check_moves_in_circuit(c1, moves)
        self.insert(self.unsafe_circuit, ExistingMoveHandlingOptions.TRUST)
        moves3 = tuple(i for i in self.safe_circuit.instructions if i.name == 'move')
        c3 = self.insert(self.ambiguous_circuit, ExistingMoveHandlingOptions.TRUST)
        self.assert_valid_circuit(c3)
        assert self.check_moves_in_circuit(c3, moves3) 

    def test_with_qubit_map(self):
        raise NotImplementedError()

