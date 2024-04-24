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

from iqm.iqm_client import Circuit, Instruction, IQMClient, QuantumArchitectureSpecification
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
    existing_moves_in_circuit = (i for i in circuit.instructions if i.name == moveGate)
    if moveGate not in arch.operations.keys():
        if not existing_moves_in_circuit:
            return circuit
        raise ValueError('Circuit contains Move instructions, but device does not support them')
    if len(existing_moves_in_circuit) > 0:
        if existing_moves is None:
            raise UserWarning('Circuit already contains Move Instructions, removing them before transpiling.')
        if existing_moves is None or existing_moves == ExistingMoveHandlingOptions.REMOVE:
            circuit = transpile_remove_moves(circuit)
        else:
            if existing_moves == ExistingMoveHandlingOptions.KEEP:
                IQMClient._validate_circuit_moves(arch, circuit)
                arch.validate_moves(circuit)  # TODO Maybe client or neither?
            new_instructions = ()
            current_instructions = ()
            for i in circuit.instructions:
                if i.name != moveGate:
                    current_instructions.append(i)
                else:
                    c = transpile_insert_moves(
                        Circuit(name='Transpile intermediate', instructions=current_instructions), arch=arch
                    )
                    new_instructions += c.instructions
                    new_instructions.append(i)
            return Circuit(name=circuit.name, instructions=new_instructions, metadata=circuit.metadata)
    instructions = circuit.instructions
    resonators = (q for q in arch.qubits if q.startswith('COMP_R'))
    res_qb_map = {r: r for r in resonators}
    new_instructions = ()
    for i in instructions:
        # TODO If gate not allowed, check resonators and place move
        # TODO If gate allowed, check resonators
        new_instructions.append(i)

    return circuit


def transpile_remove_moves(circuit: Circuit) -> Circuit:
    # TODO Fix resonator gates.
    return circuit
