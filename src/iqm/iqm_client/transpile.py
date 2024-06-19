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
from typing import Iterable, Optional
import warnings

from iqm.iqm_client import Circuit, CircuitExecutionError, Instruction, IQMClient, QuantumArchitectureSpecification


class ExistingMoveHandlingOptions(Enum):
    """Transpile options for handling of existing Move instructions.

    KEEP: the transpiler will keep the move instructions as specified checking if they are correct,
            adding more as needed.
    REMOVE: the transpiler will remove the instructions and add new ones.
    TRUST: the transpiler will keep the move instructions without checking if they are correct,
            and add more as needed.
    """

    KEEP = 'keep'
    REMOVE = 'remove'
    TRUST = 'trust'


class ResonatorStateTracker:
    """Class for tracking the location of the resonator states on the quantum computer as they are moved with the move
    gates.

    Args:
        move_calibrations (dict[str, Iterable[str]]): A dictionary describing between which qubits a move gate is
        available, for each resonator, i.e. `move_calibrations[resonator] = [qubit]`
    """

    move_gate = 'move'

    def __init__(self, move_calibrations: dict[str, list[str]]) -> None:
        self.move_calibrations = move_calibrations
        self.res_qb_map = {r: r for r in self.resonators}

    @staticmethod
    def from_quantum_architecture_specification(arch: QuantumArchitectureSpecification):
        """Constructor to make the ResonatorStateTracker from a QuantumArchitectureSpecification.

        Args:
            arch (QuantumArchitectureSpecification): The architecture to track the resonator state on.
        """
        resonators = tuple(q for q in arch.qubits if q.startswith('COMP_R'))
        move_calibrations: dict[str, list[str]] = {
            r: [q for q, r2 in arch.operations[ResonatorStateTracker.move_gate] if r == r2] for r in resonators
        }
        return ResonatorStateTracker(move_calibrations)

    @staticmethod
    def from_circuit(circuit: Circuit):
        """Constructor to make the ResonatorStateTracker from a circuit. It infers the resonator connectivity from the
        move gates in the circuit.

        Args:
            circuit (Circuit): The circuit to track the resonator state on.
        """
        return ResonatorStateTracker.from_instructions(circuit.instructions)

    @staticmethod
    def from_instructions(instructions: Iterable[Instruction]):
        """Constructor to make the ResonatorStateTracker from a sequence of instructions. It infers the resonator
        connectivity from the move instructions.

        Args:
            instructions (Iterable[Instruction]): The instructions to track the resonator state on.
        """
        move_calibrations: dict[str, list[str]] = {}
        for i in instructions:
            if i.name == ResonatorStateTracker.move_gate:
                q, r = i.qubits
                if r in move_calibrations:
                    move_calibrations[r].append(q)
                else:
                    move_calibrations[r] = [q]
        return ResonatorStateTracker(move_calibrations)

    @property
    def resonators(self):
        """Getter for the resonator registers that are being tracked."""
        return self.move_calibrations.keys()

    @property
    def supports_move(self):
        """Bool whether any move gate is allowed."""
        return self.move_calibrations != {}

    def apply_move(self, qubit: str, resonator: str):
        """Apply the logical changes of the resonator state location when a move gate between qubit and resonator is
        applied.

        Args:
            qubit (str): The moved qubit.
            resonator (str): The moved resonator.

        Raises:
            CircuitExecutionError: When the move is not allowed, either because the resonator does not exist, the move
            gate is not valid between this qubit-resonator pair, or the resonator state is currently in a different
            qubit register.
        """
        if (
            resonator in self.resonators
            and qubit in self.move_calibrations[resonator]
            and self.res_qb_map[resonator] in [qubit, resonator]
        ):
            self.res_qb_map[resonator] = qubit if self.res_qb_map[resonator] == resonator else resonator
        else:
            raise CircuitExecutionError('Attempted move is not allowed.')

    def create_move_instructions(
        self,
        qubit: str,
        resonator: str,
        apply_move: Optional[bool] = True,
        alt_qubit_names: Optional[dict[str, str]] = None,
    ):
        """Create the move instructions needed to move qubit and resonator.

        Args:
            qubit (str): The qubit
            resonator (str): The resonator
            apply_move (Optional[bool], optional): Whether the moves should be applied to the resonator tracking state.
            Defaults to True.

        Yields:
            Instruction: The one or two move instructions needed.
        """
        if self.res_qb_map[resonator] not in [qubit, resonator]:
            other = self.res_qb_map[resonator]
            if apply_move:
                self.apply_move(other, resonator)
            qbs = tuple(alt_qubit_names[q] if alt_qubit_names else q for q in [other, resonator])
            yield Instruction(name=self.move_gate, qubits=qbs, args={})
        if apply_move:
            self.apply_move(qubit, resonator)
        qbs = tuple(alt_qubit_names[q] if alt_qubit_names else q for q in [qubit, resonator])
        yield Instruction(name=self.move_gate, qubits=qbs, args={})

    def reset_as_move_instructions(
        self,
        resonators: Optional[Iterable[str]] = None,
        apply_move: Optional[bool] = True,
        alt_qubit_names: Optional[dict[str, str]] = None,
    ):
        """Creates the move instructions needed to move all resonator states to their original state.

        Args:
            resonators (Optional[Iterable[str]], optional): The set of resonators to reset, if None, all resonators will
            be reset. Defaults to None.
            apply_move (Optional[bool], optional): Whether the moves should be applied to the resonator tracking state.
            Defaults to True.

        Returns:
            list[Instruction]: The instructions needed to move all qubit states out of the resonators.
        """
        if resonators is None:
            resonators = self.resonators
        instructions = []
        for r, q in [(r, q) for r, q in self.res_qb_map.items() if r != q and r in resonators]:
            instructions += self.create_move_instructions(q, r, apply_move, alt_qubit_names)
        return instructions

    def available_resonators_to_move(self, qubits: Iterable[str]):
        """Generates a dictionary with which resonators a qubit can be moved to, for each qubit.

        Args:
            qubits (Iterable[str]): The qubits to check which move gates are available.

        Returns:
            dict[str, list[str]]: The dict that maps each qubit to a list of resonators.
        """
        return {q: [r for r in self.resonators if q in self.move_calibrations[r]] for q in qubits}

    def resonators_holding_qubits(self, qubits: Iterable[str]):
        """Returns the resonators that are currently holding one of the given qubit states.

        Args:
            qubits (Iterable[str]): The qubits

        Returns:
            list[str]: The resonators
        """
        return [r for r, q in self.res_qb_map.items() if q in qubits and q not in self.resonators]

    def choose_move_pair(
        self, qubits: list[str], remaining_instructions: list[list[str]]
    ) -> list[tuple[str, str, list[list[str]]]]:
        """Chooses which qubit of the given qubits to move into which resonator, given a sequence of instructions to be
        executed later for looking ahead.

        Args:
            qubits (list[str]): The qubits to choose from
            remaining_instructions (list[Instruction]): The instructions to use for the look-ahead.

        Raises:
            CircuitExecutionError: When no move pair is available, most likely because the circuit was not routed.

        Returns:
            list[tuple[str, str, list[list[str]]]]: A sorted preference list of resonator and qubit chosen to apply the move on.
        """
        r_candidates = [
            (r, q, remaining_instructions) for q, rs in self.available_resonators_to_move(qubits).items() for r in rs
        ]
        if len(r_candidates) == 0:
            raise CircuitExecutionError(
                f'Unable to insert MOVE gates because none of the qubits {qubits} share a resonator. '
                + 'This can be resolved by routing the circuit first without resonators.'
            )
        resonator_candidates = list(sorted(r_candidates, key=self._score_choice_heuristic, reverse=True))
        return resonator_candidates

    def _score_choice_heuristic(self, args: tuple[str, str, list[list[str]]]):
        """A simple look ahead heuristic for choosing which qubit to move where. Counts the number of CZ gates until the
        qubit needs to be moved out.

        Args:
            args (tuple[str, str, list[list[str]]): resonator, qubit, instructions.

        Returns:
            int: The count/score.
        """
        _, qb, circ = args
        score: int = 0
        for instr in circ:
            if qb in instr:
                if instr[0] != 'cz':
                    return score
                score += 1
        return score

    def update_qubits_in_resonator(self, qubits: Iterable[str]):
        """Applies the resonator to qubit map in the state of the resonator state tracker to the given qubits.

        Args:
            qubits (Iterable[str]): The qubits or resonators to apply the state to

        Returns:
            list[str]: The remapped qubits
        """
        return [self.res_qb_map[q] if q in self.res_qb_map else q for q in qubits]


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
            If None, the function will use ExistingMoveHandlingOptions.REMOVE with a user warning if there are move
            instructions in the circuit. Defaults to None.
          qubit_mapping: Mapping of logical qubit names to physical qubit names.
              Can be set to ``None`` if all ``circuits`` already use physical qubit names.
    """
    res_status = ResonatorStateTracker.from_quantum_architecture_specification(arch)
    if not qubit_mapping:
        qubit_mapping = {}
    for q in arch.qubits:
        if q not in qubit_mapping.values():
            qubit_mapping[q] = q
    existing_moves_in_circuit = [i for i in circuit.instructions if i.name == res_status.move_gate]
    if not res_status.supports_move:
        if not existing_moves_in_circuit:
            return circuit
        if existing_moves == ExistingMoveHandlingOptions.REMOVE:
            return transpile_remove_moves(circuit)
        raise ValueError('Circuit contains Move instructions, but device does not support them')

    if existing_moves is None and len(existing_moves_in_circuit) > 0:
        warnings.warn('Circuit already contains Move Instructions, removing them before transpiling.')
        existing_moves = ExistingMoveHandlingOptions.REMOVE
    if existing_moves is None or existing_moves == ExistingMoveHandlingOptions.REMOVE:
        circuit = transpile_remove_moves(circuit)
    elif existing_moves == ExistingMoveHandlingOptions.KEEP:
        try:
            IQMClient._validate_circuit_moves(arch, circuit, qubit_mapping=qubit_mapping)
        except CircuitExecutionError as e:
            raise CircuitExecutionError(f'Unable to transpile the circuit after validation error: {e.args[0]}') from e

    rev_qubit_mapping = {v: k for k, v in qubit_mapping.items()}
    new_instructions = _transpile_insert_moves(list(circuit.instructions), res_status, arch, qubit_mapping)
    new_instructions += res_status.reset_as_move_instructions(alt_qubit_names=rev_qubit_mapping)

    return Circuit(name=circuit.name, instructions=new_instructions, metadata=circuit.metadata)


def _transpile_insert_moves(
    instructions: list[Instruction],
    res_status: ResonatorStateTracker,
    arch: QuantumArchitectureSpecification,
    qubit_mapping: dict[str, str],
) -> list[Instruction]:
    """Helper function for transpile_insert_moves that inserts MOVE gates into a list of intstructions and changes the
    existing instructions as needed.

    Args:
        instructions (list[Instruction]): The instructions in the circuit.
        res_status (ResonatorStateTracker): The location of the resonator states at the start of the instructions. At
        the end of this method this tracker is adjusted to reflect the state at the end of the returned instructions.
        arch (QuantumArchitectureSpecification): The target quantum architecture.
        qubit_mapping (dict[str, str]): Mapping from logical qubit names to physical qubit names.

    Raises:
        CircuitExecutionError: Raised when the circuit contains invalid gates that cannot be transpiled using this
        method.

    Returns:
        list[Instruction]: The transpiled list of instructions.
    """
    new_instructions = []
    rev_qubit_mapping = {v: k for k, v in qubit_mapping.items()}
    for idx, i in enumerate(instructions):
        qubits = [qubit_mapping[q] for q in i.qubits]
        res_match = res_status.resonators_holding_qubits(qubits)
        if res_match and i.name not in ['cz', res_status.move_gate]:
            # We have a gate on a qubit in the resonator that cannot be executed on the resonator (incl. barriers)
            new_instructions += res_status.reset_as_move_instructions(res_match, alt_qubit_names=rev_qubit_mapping)
            new_instructions.append(i)
        else:
            # Check if the instruction is valid, which raises an exception if not.
            try:
                IQMClient._validate_instruction(architecture=arch, instruction=i, qubit_mapping=qubit_mapping)
                new_instructions.append(i)  # No adjustment needed
                if i.name == res_status.move_gate:  # update the tracker if needed
                    res_status.apply_move(*[qubit_mapping[q] for q in i.qubits])
            except CircuitExecutionError as e:
                if i.name != 'cz':  # We can only fix cz gates at this point
                    raise CircuitExecutionError(
                        f'Unable to transpile the circuit after validation error: {e.args[0]}'
                    ) from e
                remaining_instructions = [[i.name] + [qubit_mapping[q] for q in i.qubits] for i in instructions[idx:]]
                # Pick which qubit-resonator pair to apply this cz to
                # Pick from qubits already in a resonator or both targets if none off them are in a resonator
                resonator_candidates = res_status.choose_move_pair(
                    [res_status.res_qb_map[res] for res in res_match] if res_match else qubits, remaining_instructions
                )
                candidate_found = False
                while resonator_candidates and not candidate_found:
                    r, q1, _ = resonator_candidates.pop(0)
                    q2 = [q for q in qubits if q != q1][0]
                    instruction = Instruction(name='cz', qubits=(rev_qubit_mapping[q2], rev_qubit_mapping[r]), args={})
                    try:
                        IQMClient._validate_instruction(
                            architecture=arch, instruction=instruction, qubit_mapping=qubit_mapping
                        )
                        candidate_found = True
                        print("Found:", instruction)
                    except CircuitExecutionError as e:
                        candidate_found = False
                        print("Not found:", instruction)
                if not candidate_found:
                    raise CircuitExecutionError('Unable to find a valid resonator-qubit pair to apply the CZ gate to.')

                # remove the other qubit from the resonator if it was in
                new_instructions += res_status.reset_as_move_instructions(
                    [res for res in res_match if res != r], alt_qubit_names=rev_qubit_mapping
                )
                # move the qubit into the resonator if it was not yet in.
                if not res_match:
                    new_instructions += res_status.create_move_instructions(q1, r, alt_qubit_names=rev_qubit_mapping)
                new_instructions.append(instruction)
    return new_instructions


def transpile_remove_moves(circuit: Circuit) -> Circuit:
    """Transpile method that removes move gates from a circuit.

    The method assumes that these move gates are moving the resonator state in and out the resonator register to
    reconstruct the CZ gates. If this is not the case, the semantic equivalence cannot be guaranteed.

    Args:
        circuit (Circuit): The circuit from which the move gates need to be removed.

    Returns:
        Circuit: The circuit with the move gates removed and the targets for all other gates updated accordingly.
    """
    res_status = ResonatorStateTracker.from_circuit(circuit)
    new_instructions = []
    for i in circuit.instructions:
        if i.name == res_status.move_gate:
            res_status.apply_move(*i.qubits)
        else:
            new_qubits = res_status.update_qubits_in_resonator(i.qubits)
            new_instructions.append(Instruction(name=i.name, qubits=new_qubits, args=i.args))
    return Circuit(name=circuit.name, instructions=new_instructions, metadata=circuit.metadata)
