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
r"""
Collection of transpile functions needed for transpiling to specific devices
"""
from enum import Enum
from typing import Iterable, Optional, Union

from iqm.iqm_client import Circuit, Instruction, IQMClient, QuantumArchitectureSpecification, CircuitExecutionError
from iqm.iqm_client.instruction import is_multi_qubit_instruction


class ExistingMoveHandlingOptions(Enum):
    """Transpile options for handling of existing Move instructions.

    KEEP: the transpiler will keep the move instructions as specified checking if they are correct, adding more as needed.
    REMOVE: the transpiler will remove the instructions and add new ones.
    TRUST: the transpiler will keep the move instructions without checking if they are correct, and add more as needed.
    """

    KEEP = 'keep'
    REMOVE = 'remove'
    TRUST = 'trust'


def transpile_insert_moves(
    circuit: Circuit,
    arch: QuantumArchitectureSpecification,
    existing_moves: Optional[ExistingMoveHandlingOptions] = None,
    qubit_mapping: Optional[dict[str, str]] = None,
) -> Circuit:
    """Transpile method that inserts moves to the circuit according to a given architecture specification.
    The function does nothing if the given architecture specification does not support move Instructions.

    Args:
        circuit (Circuit): The circuit to add Move instructions to.
        arch (QuantumArchitectureSpecification): Restrictions of the target device
        existing_moves (ExistingMoveHandlingOptions, optional): Specifies how to deal with existing move instruction,
            If None, the function will use ExistingMoveHandlingOptions.REMOVE with a user warning if there are move instructions in the circuit.
            Defaults to None.
        qubit_mapping (dict[str,str], optional): Mapping of logical qubit names to physical qubit names.
            Can be set to ``None`` if the ``circuit`` already uses physical qubit names.
    """
    moveGate = 'move' 
    existing_moves_in_circuit = [i for i in circuit.instructions if i.name == moveGate]
    if moveGate not in arch.operations.keys():
        if not existing_moves_in_circuit:
            return circuit
        if existing_moves == ExistingMoveHandlingOptions.REMOVE:
            return transpile_remove_moves(circuit)
        raise ValueError('Circuit contains Move instructions, but device does not support them')
    
    resonators = tuple(q for q in arch.qubits if q.startswith('COMP_R'))
    move_calibrations = {r: [q for q, r2 in arch.operations[moveGate] if r == r2] for r in resonators}
    res_qb_map = {r: r for r in resonators}
    if len(existing_moves_in_circuit) > 0:
        if existing_moves is None:
            raise UserWarning('Circuit already contains Move Instructions, removing them before transpiling.')
        if existing_moves is None or existing_moves == ExistingMoveHandlingOptions.REMOVE:
            circuit = transpile_remove_moves(circuit)
        else:
            if existing_moves == ExistingMoveHandlingOptions.KEEP:
                try:
                    IQMClient._validate_circuit_moves(arch, circuit, qubit_mapping=qubit_mapping)
                except CircuitExecutionError as e:
                    if e.args[0].startswith('Instruction prx on'):
                        raise CircuitExecutionError(f'Unable to transpile the circuit after validation error: {e.args[0]}')
            new_instructions = []
            current_instructions = []
            for i in circuit.instructions:
                try:
                    IQMClient._validate_instruction(arch, i, qubit_mapping)
                    if i.name == moveGate:
                        q, r = i.qubits
                        if res_qb_map[r] == r:
                            res_qb_map[r] = q
                        elif q != res_qb_map[r]:
                            raise CircuitExecutionError('MoveGate on qubit {q} while resonator occupied with {res_qb_map[r]}.')
                        else:
                            res_qb_map[r] = r
                    current_instructions.append(i)
                except CircuitExecutionError:
                    c, res_qb_map = _transpile_insert_moves([i],res_qb_map, move_calibrations, arch, qubit_mapping)
                    new_instructions += current_instructions + c
                    current_instructions = []
            new_instructions += current_instructions
            
            for r, q in res_qb_map.items():
                if r != q:
                    new_instructions.append(Instruction(name=moveGate, qubits=(res_qb_map[r], r), args={}))
            
            return Circuit(name=circuit.name, instructions=new_instructions, metadata=circuit.metadata)
          
    new_instructions, res_qb_map = _transpile_insert_moves(circuit.instructions, res_qb_map, move_calibrations, arch, qubit_mapping)

    for r, q in res_qb_map.items():
        if r != q:
            new_instructions.append(Instruction(name=moveGate, qubits=(res_qb_map[r], r), args={}))

    return Circuit(name=circuit.name, instructions=new_instructions)

def _transpile_insert_moves(instructions: list[Instruction], res_qb_map: dict[str,str], move_calibrations: dict[str, list[str]], arch:QuantumArchitectureSpecification, qubit_mapping: Optional[dict[str, str]] = None) -> tuple[list[Instruction], dict[str,str]]:
    moveGate, czGate = 'move', 'cz'
    new_instructions = []
    for idx, i in enumerate(instructions):
        try: 
            IQMClient._validate_instruction(architecture=arch, instruction=i, qubit_mapping=qubit_mapping)
            new_instructions.append(i)
            if i.name == moveGate:
                q, r = i.qubits
                if res_qb_map[r] == r:
                    res_qb_map[r] = q
                elif q != res_qb_map[r]:
                    raise CircuitExecutionError('MoveGate on qubit {q} while resonator occupied with {res_qb_map[r]}.')
                else:
                    res_qb_map[r] = r
        except CircuitExecutionError as e:
            res_match = [(r, q) for r, q in res_qb_map.items() if q in i.qubits and q not in res_qb_map.keys()]
            if i.name == czGate:
                if res_match:  
                    r, q1 = res_match[0] 
                else: 
                    r_candidates = tuple((r, q, instructions[idx:]) for r, qbs in move_calibrations.items() for q in i.qubits if q in qbs)
                    if len(r_candidates) == 0:
                        raise CircuitExecutionError(f'Unable to route instruction {i} because neither qubits can be moved to a resonator.')
                    r, q1, _ = max(r_candidates, key=_score_choice_heuristic)
                    if res_qb_map[r] != r: 
                        new_instructions.append(Instruction(name=moveGate, qubits=(res_qb_map[r], r), args={}))
                    new_instructions.append(Instruction(name=moveGate, qubits=(q1, r), args={}))
                    res_qb_map[r] = q1
                q2 = [q for q in i.qubits if q != q1][0] 
                new_instructions.append(Instruction(name=czGate, qubits=(q2, r), args={}))
            elif res_match:
                for r, q in res_match:
                    new_instructions.append(Instruction(name=moveGate, qubits=(q, r), args={})) 
                    res_qb_map[r] = r
                new_instructions.append(i)
            else:
                raise CircuitExecutionError(f'Unable to transpile the circuit after validation error: {e.args[0]}')
    return new_instructions, res_qb_map


def _score_choice_heuristic(args: tuple[str, str, tuple[Instruction]]):
    res, qb, circ = args
    score: int = 0
    for instr in circ:
        if qb in instr.qubits: 
            if instr.name != 'cz': 
                return score
            score += 1
        
    return score


def transpile_remove_moves(circuit: Circuit) -> Circuit:
    moveGate = 'move'
    res_qb_map = {}
    new_instructions = []
    for i in circuit.instructions:
        if i.name == moveGate:
            qb, r = i.qubits
            if r in res_qb_map.keys():
                del res_qb_map[r]
            else:
                res_qb_map[r] = qb
        else:
            new_qubits = [res_qb_map[q] if q in res_qb_map.keys() else q for q in i.qubits]
            new_instructions.append(Instruction(name=i.name, qubits=new_qubits, args=i.args))
    return Circuit(name=circuit.name, instructions=new_instructions)