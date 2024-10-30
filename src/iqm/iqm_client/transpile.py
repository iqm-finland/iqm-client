# Copyright 2021-2024 IQM client developers
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
"""
Collection of transpilation functions needed for transpiling to specific devices.
"""
from enum import Enum
from typing import Any, Iterable, Optional
import warnings

from iqm.iqm_client import (
    Circuit,
    CircuitTranspilationError,
    CircuitValidationError,
    DynamicQuantumArchitecture,
    Instruction,
    IQMClient,
)


class ExistingMoveHandlingOptions(str, Enum):
    """Transpile options for handling of existing MOVE instructions."""

    KEEP = 'keep'
    """Transpiler will keep the MOVE instructions as specified checking if they are correct, adding more as needed."""
    REMOVE = 'remove'
    """Transpiler will remove the instructions and add new ones."""
    TRUST = 'trust'
    """Transpiler will keep the MOVE instructions without checking if they are correct, and add more as needed."""


class ResonatorStateTracker:
    r"""Class for tracking the location of the :math:`|0\rangle` state of the resonators on the
    quantum computer as they are moved with the MOVE gates because the MOVE gate is not defined
    when acting on a :math:`|11\rangle` state. This is equivalent to tracking
    which qubit state has been moved into which resonator.

    Args:
        available_moves: A dictionary describing between which qubits a MOVE gate is
            available, for each resonator, i.e. ``available_moves[resonator] = [qubit]``
    """

    move_gate = 'move'

    def __init__(self, available_moves: dict[str, list[str]]) -> None:
        self.available_moves = available_moves
        self.res_qb_map = {r: r for r in self.resonators}

    @staticmethod
    def from_dynamic_architecture(arch: DynamicQuantumArchitecture) -> 'ResonatorStateTracker':
        """Constructor to make the ResonatorStateTracker from a DynamicQuantumArchitecture.

        Args:
            arch: The architecture to track the resonator state on.
        """
        available_moves: dict[str, list[str]] = {
            r: [q for q, r2 in arch.gates[ResonatorStateTracker.move_gate].loci if r == r2]
            for r in arch.computational_resonators
        }
        return ResonatorStateTracker(available_moves)

    @staticmethod
    def from_circuit(circuit: Circuit) -> 'ResonatorStateTracker':
        """Constructor to make the ResonatorStateTracker from a circuit.

        Infers the resonator connectivity from the MOVE gates in the circuit.

        Args:
            circuit: The circuit to track the resonator state on.
        """
        return ResonatorStateTracker.from_instructions(circuit.instructions)

    @staticmethod
    def from_instructions(instructions: Iterable[Instruction]) -> 'ResonatorStateTracker':
        """Constructor to make the ResonatorStateTracker from a sequence of instructions.

        Infers the resonator connectivity from the MOVE gates.

        Args:
            instructions: The instructions to track the resonator state on.
        """
        available_moves: dict[str, list[str]] = {}
        for i in instructions:
            if i.name == ResonatorStateTracker.move_gate:
                q, r = i.qubits
                available_moves.setdefault(r, []).append(q)
        return ResonatorStateTracker(available_moves)

    @property
    def resonators(self) -> Iterable[str]:
        """Getter for the resonator registers that are being tracked."""
        return self.available_moves

    @property
    def supports_move(self) -> bool:
        """Bool whether any MOVE gate is allowed."""
        return bool(self.available_moves)

    def apply_move(self, qubit: str, resonator: str) -> None:
        """Apply the logical changes of the resonator state location when a MOVE gate between qubit and resonator is
        applied.

        Args:
            qubit: The moved qubit.
            resonator: The moved resonator.

        Raises:
            CircuitTranspilationError: MOVE is not allowed, either because the resonator does not exist,
                the MOVE gate is not available between this qubit-resonator pair, or the resonator state
                is currently in a different qubit register.
        """
        if (
            resonator in self.resonators
            and qubit in self.available_moves[resonator]
            and self.res_qb_map[resonator] in [qubit, resonator]
        ):
            self.res_qb_map[resonator] = qubit if self.res_qb_map[resonator] == resonator else resonator
        else:
            raise CircuitTranspilationError('Attempted move is not allowed.')

    def create_move_instructions(
        self,
        qubit: str,
        resonator: str,
        apply_move: Optional[bool] = True,
        alt_qubit_names: Optional[dict[str, str]] = None,
    ) -> Iterable[Instruction]:
        """Create the MOVE instructions needed to move the given resonator state into the resonator if needed and then
        move resonator state to the given qubit.

        Args:
            qubit: The qubit
            resonator: The resonator
            apply_move: Whether the moves should be applied to the resonator tracking state.
            alt_qubit_names: Mapping of logical qubit names to physical qubit names.

        Yields:
            The one or two MOVE instructions needed.
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
    ) -> list[Instruction]:
        """Creates the MOVE instructions needed to move all resonator states to their original state.

        Args:
            resonators: The set of resonators to reset, if None, all resonators will be reset.
            apply_move: Whether the moves should be applied to the resonator tracking state.

        Returns:
            The instructions needed to move all qubit states out of the resonators.
        """
        if resonators is None:
            resonators = self.resonators
        instructions: list[Instruction] = []
        for r, q in [(r, q) for r, q in self.res_qb_map.items() if r != q and r in resonators]:
            instructions += self.create_move_instructions(q, r, apply_move, alt_qubit_names)
        return instructions

    def available_resonators_to_move(self, qubits: Iterable[str]) -> dict[str, list[str]]:
        """Generates a dictionary with which resonators a qubit can be moved to, for each qubit.

        Args:
            qubits: The qubits to check which MOVE gates are available.

        Returns:
            The dict that maps each qubit to a list of resonators.
        """
        return {q: [r for r in self.resonators if q in self.available_moves[r]] for q in qubits}

    def resonators_holding_qubits(self, qubits: Iterable[str]) -> list[str]:
        """Returns the resonators that are currently holding one of the given qubit states.

        Args:
            qubits: The qubits

        Returns:
            The resonators
        """
        return [r for r, q in self.res_qb_map.items() if q in qubits and q not in self.resonators]

    def choose_move_pair(
        self, qubits: list[str], remaining_instructions: list[list[str]]
    ) -> list[tuple[str, str, list[list[str]]]]:
        """Chooses which qubit of the given qubits to move into which resonator, given a sequence of instructions to be
        executed later for looking ahead.

        Args:
            qubits: The qubits to choose from
            remaining_instructions: The instructions to use for the look-ahead.

        Raises:
            CircuitTranspilationError: When no move pair is available, most likely because the circuit was not routed.

        Returns:
            A sorted preference list of resonator and qubit chosen to apply the move on.
        """
        r_candidates = [
            (r, q, remaining_instructions) for q, rs in self.available_resonators_to_move(qubits).items() for r in rs
        ]
        if len(r_candidates) == 0:
            raise CircuitTranspilationError(
                f'Unable to insert MOVE gates because none of the qubits {qubits} share a resonator. '
                + 'This can be resolved by routing the circuit first without resonators.'
            )
        resonator_candidates = list(sorted(r_candidates, key=self._score_choice_heuristic, reverse=True))
        return resonator_candidates

    def _score_choice_heuristic(self, args: tuple[str, str, list[list[str]]]) -> int:
        """A simple look ahead heuristic for choosing which qubit to move where.

        Counts the number of CZ gates until the qubit needs to be moved out.

        Args:
            args: resonator, qubit, instructions.

        Returns:
            The count/score.
        """
        _, qb, circ = args
        score: int = 0
        for instr in circ:
            if qb in instr:
                if instr[0] != 'cz':
                    return score
                score += 1
        return score

    def update_qubits_in_resonator(self, qubits: Iterable[str]) -> list[str]:
        """Applies the resonator to qubit map in the state of the resonator state tracker to the given qubits.

        Args:
            qubits: The qubits or resonators to apply the state to

        Returns:
            The remapped qubits
        """
        return [self.res_qb_map.get(q, q) for q in qubits]


def transpile_insert_moves(
    circuit: Circuit,
    arch: DynamicQuantumArchitecture,
    existing_moves: Optional[ExistingMoveHandlingOptions] = None,
    qubit_mapping: Optional[dict[str, str]] = None,
) -> Circuit:
    """Inserts MOVEs to the circuit according to a given architecture specification.

    The function does nothing if the given architecture specification does not support MOVE gates.
    Note that this method assumes that the circuit is already transpiled to a coupling map/architecture where the
    resonator has been abstracted away, i.e. the edges of the coupling map that contain resonators are replaced by
    edges between the other qubit and all qubits that can be moved to that resonator.

    Args:
        circuit: The circuit to add MOVE instructions to.
        arch: Restrictions of the target device
        existing_moves: Specifies how to deal with existing MOVE instruction,
            If None, the function will use ExistingMoveHandlingOptions.REMOVE with a user warning if there are move
            instructions in the circuit.
        qubit_mapping: Mapping of logical qubit names to physical qubit names.
            Can be set to ``None`` if all ``circuits`` already use physical qubit names.
    """
    res_status = ResonatorStateTracker.from_dynamic_architecture(arch)
    if not qubit_mapping:
        qubit_mapping = {}
    for q in arch.components:
        if q not in qubit_mapping.values():
            qubit_mapping[q] = q
    existing_moves_in_circuit = [i for i in circuit.instructions if i.name == res_status.move_gate]

    if existing_moves is None and len(existing_moves_in_circuit) > 0:
        warnings.warn('Circuit already contains MOVE instructions, removing them before transpiling.')
        existing_moves = ExistingMoveHandlingOptions.REMOVE

    if not res_status.supports_move:
        if not existing_moves_in_circuit:
            return circuit
        if existing_moves == ExistingMoveHandlingOptions.REMOVE:
            return transpile_remove_moves(circuit)
        raise ValueError('Circuit contains MOVE instructions, but device does not support them')

    if existing_moves is None or existing_moves == ExistingMoveHandlingOptions.REMOVE:
        circuit = transpile_remove_moves(circuit)
    elif existing_moves == ExistingMoveHandlingOptions.KEEP:
        try:
            IQMClient._validate_circuit_moves(arch, circuit, qubit_mapping=qubit_mapping)
        except CircuitValidationError as e:
            raise CircuitTranspilationError(
                f'Unable to transpile the circuit after validation error: {e.args[0]}'
            ) from e

    rev_qubit_mapping = {v: k for k, v in qubit_mapping.items()}
    new_instructions = _transpile_insert_moves(list(circuit.instructions), res_status, arch, qubit_mapping)
    new_instructions += res_status.reset_as_move_instructions(alt_qubit_names=rev_qubit_mapping)

    return Circuit(name=circuit.name, instructions=new_instructions, metadata=circuit.metadata)


def _transpile_insert_moves(
    instructions: list[Instruction],
    res_status: ResonatorStateTracker,
    arch: DynamicQuantumArchitecture,
    qubit_mapping: dict[str, str],
) -> list[Instruction]:
    """Inserts MOVE gates into a list of instructions and changes the existing instructions as needed.

    Helper function for :func:`transpile_insert_moves`.

    Args:
        instructions: The instructions in the circuit.
        res_status: The location of the resonator states at the start of the instructions. At
        the end of this method this tracker is adjusted to reflect the state at the end of the returned instructions.
        arch: The target quantum architecture.
        qubit_mapping: Mapping from logical qubit names to physical qubit names.

    Raises:
        CircuitTranspilationError: Raised when the circuit contains invalid gates that cannot be transpiled using this
            method.

    Returns:
        The transpiled list of instructions.
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
                IQMClient._validate_instruction(
                    architecture=arch,
                    instruction=i,
                    qubit_mapping=qubit_mapping,
                )
                new_instructions.append(i)  # No adjustment needed
                if i.name == res_status.move_gate:  # update the tracker if needed
                    res_status.apply_move(*[qubit_mapping[q] for q in i.qubits])
            except CircuitValidationError as e:
                if i.name != 'cz':  # We can only fix cz gates at this point
                    raise CircuitTranspilationError(
                        f'Unable to transpile the circuit after validation error: {e.args[0]}'
                    ) from e
                # Pick which qubit-resonator pair to apply this cz to
                # Pick from qubits already in a resonator or both targets if none off them are in a resonator
                resonator_candidates: Optional[list[tuple[str, str, Any]]] = res_status.choose_move_pair(
                    [res_status.res_qb_map[res] for res in res_match] if res_match else qubits,
                    [[i.name] + [qubit_mapping[q] for q in i.qubits] for i in instructions[idx:]],
                )
                while resonator_candidates:
                    r, q1, _ = resonator_candidates.pop(0)
                    q2 = [q for q in qubits if q != q1][0]
                    try:
                        IQMClient._validate_instruction(
                            architecture=arch,
                            instruction=Instruction(
                                name='cz', qubits=(rev_qubit_mapping[q2], rev_qubit_mapping[r]), args={}
                            ),
                            qubit_mapping=qubit_mapping,
                        )
                        resonator_candidates = None
                        break
                    except CircuitValidationError:
                        pass

                if resonator_candidates is not None:
                    raise CircuitTranspilationError(
                        'Unable to find a valid resonator-qubit pair for a MOVE gate to enable this CZ gate.'
                    ) from e

                # remove the other qubit from the resonator if it was in
                new_instructions += res_status.reset_as_move_instructions(
                    [res for res in res_match if res != r], alt_qubit_names=rev_qubit_mapping
                )
                # move the qubit into the resonator if it was not yet in.
                if not res_match:
                    new_instructions += res_status.create_move_instructions(q1, r, alt_qubit_names=rev_qubit_mapping)
                new_instructions.append(
                    Instruction(name='cz', qubits=(rev_qubit_mapping[q2], rev_qubit_mapping[r]), args={})
                )
    return new_instructions


def transpile_remove_moves(circuit: Circuit) -> Circuit:
    """Removes MOVE gates from a circuit.

    The method assumes that these MOVE gates are moving the resonator state in and out the resonator register to
    reconstruct the CZ gates. If this is not the case, the semantic equivalence cannot be guaranteed.

    Args:
        circuit: The circuit from which the MOVE gates need to be removed.

    Returns:
        The circuit with the MOVE gates removed and the targets for all other gates updated accordingly.
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
