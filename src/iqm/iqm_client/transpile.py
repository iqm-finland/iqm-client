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
Transpiling circuits to IQM devices involving computational resonators.

In the IQM Star architecture, computational resonators are connected to multiple qubits.
The qubit state can be moved into connected resonator and back using a MOVE gate between
the qubit and resonator. Additionally, two-qubit gates like CZ can be applied between a qubit
and a connected resonator. However, the resonator cannot be measured, and no single-qubit gates
can be applied on it.

To enable third-party transpilers to work on the IQM Star architecture, we may abstract away the
resonators, and replace a resonator and its ``n`` neighboring qubits with a fully connected subgraph
(clique) of ``n`` qubits with the qubit-resonator gates now acting on pairs of qubits.
This is called a *fake architecture*.

Before a circuit transpiled to a fake architecture can be executed it must be further transpiled to
the real Star architecture using :func:`transpile_insert_moves`, which will introduce the
resonators, add MOVE gates as necessary to move the states, and convert the two-qubit gates into
gates acting on a qubit-resonator pair.

Likewise :func:`transpile_remove_moves` can be used to perform the opposite transformation,
converting a circuit valid for the real Star architecture into an equivalent circuit for
the corresponding fake architecture.
"""
from __future__ import annotations

from collections.abc import Iterable
from enum import Enum
from typing import Any, Optional
import warnings

from iqm.iqm_client import (
    Circuit,
    CircuitTranspilationError,
    CircuitValidationError,
    DynamicQuantumArchitecture,
    Instruction,
    IQMClient,
)
from iqm.iqm_client.models import Locus


class ExistingMoveHandlingOptions(str, Enum):
    """Transpile options for handling of existing MOVE instructions."""

    KEEP = 'keep'
    """Transpiler will keep the MOVE instructions as specified checking if they are correct, adding more as needed."""
    REMOVE = 'remove'
    """Transpiler will remove the instructions and add new ones."""
    TRUST = 'trust'
    """Transpiler will keep the MOVE instructions without checking if they are correct, and add more as needed."""


class _ResonatorStateTracker:
    r"""Tracks the qubit states stored in computational resonators on the QPU as they are moved with MOVE gates.

    This is required because the MOVE gate is not defined when acting on a :math:`|11\rangle` state,
    and involves an unknown phase.

    Args:
        available_moves: Mapping from resonator to qubits with which it has a MOVE gate available.
    """

    move_gate = 'move'

    def __init__(self, available_moves: dict[str, list[str]]) -> None:
        self.available_moves = available_moves
        self.res_state_owner = {r: r for r in self.resonators}
        """Maps resonator to the QPU component whose state it currently holds."""

    @staticmethod
    def from_dynamic_architecture(arch: DynamicQuantumArchitecture) -> _ResonatorStateTracker:
        """Constructor to make a _ResonatorStateTracker from a dynamic quantum architecture.

        Args:
            arch: Architecture that determines the available MOVE gate loci.
        """
        available_moves: dict[str, list[str]] = {}
        if gate_info := arch.gates.get(_ResonatorStateTracker.move_gate):
            for q, r in gate_info.loci:
                # assume MOVE gate loci are always [qubit, resonator]
                available_moves.setdefault(r, []).append(q)
        return _ResonatorStateTracker(available_moves)

    @staticmethod
    def from_circuit(circuit: Circuit) -> _ResonatorStateTracker:
        """Constructor to make the _ResonatorStateTracker from a circuit.

        Infers the resonator connectivity from the MOVE gates in the circuit.

        Args:
            circuit: The circuit to track the resonator state on.
        """
        return _ResonatorStateTracker.from_instructions(circuit.instructions)

    @staticmethod
    def from_instructions(instructions: Iterable[Instruction]) -> _ResonatorStateTracker:
        """Constructor to make the _ResonatorStateTracker from a sequence of instructions.

        Infers the resonator connectivity from the MOVE gates.

        Args:
            instructions: The instructions to track the resonator state on.
        """
        available_moves: dict[str, list[str]] = {}
        for i in instructions:
            if i.name == _ResonatorStateTracker.move_gate:
                q, r = i.qubits
                available_moves.setdefault(r, []).append(q)
        return _ResonatorStateTracker(available_moves)

    @property
    def resonators(self) -> Iterable[str]:
        """Getter for the resonator registers that are being tracked."""
        return self.available_moves

    @property
    def supports_move(self) -> bool:
        """True iff any MOVE gates are available."""
        return bool(self.available_moves)

    def apply_move(self, qubit: str, resonator: str) -> None:
        """Record changes to resonator state location when a MOVE gate is applied.

        Args:
            qubit: The moved qubit.
            resonator: The moved resonator.

        Raises:
            CircuitTranspilationError: MOVE is not allowed, either because the resonator does not exist,
                the MOVE gate is not available between this qubit-resonator pair, or the resonator state
                is currently held in a different qubit.
        """
        if (
            resonator in self.resonators
            and qubit in self.available_moves[resonator]
            and self.res_state_owner[resonator] in [qubit, resonator]
        ):
            self.res_state_owner[resonator] = qubit if self.res_state_owner[resonator] == resonator else resonator
        else:
            raise CircuitTranspilationError('Attempted move is not allowed.')

    def create_move_instructions(
        self,
        qubit: str,
        resonator: str,
        *,
        apply_move: Optional[bool] = True,
        alt_qubit_names: Optional[dict[str, str]] = None,
    ) -> Iterable[Instruction]:
        """MOVE instruction(s) to move the state of the given resonator into the
        resonator if needed and then move resonator state to the given qubit.

        Args:
            qubit: The qubit
            resonator: The resonator
            apply_move: Whether the moves should be applied to the resonator tracking state.
            alt_qubit_names: Mapping of physical qubit names to logical qubit names.

        Yields:
            The one or two MOVE instructions needed.
        """
        res_state_owner = self.res_state_owner[resonator]
        if res_state_owner not in [qubit, resonator]:
            other = res_state_owner
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
        *,
        apply_move: Optional[bool] = True,
        alt_qubit_names: Optional[dict[str, str]] = None,
    ) -> list[Instruction]:
        """MOVE instructions that move all the states held in the given resonators back to their qubits.

        Args:
            resonators: Resonators that hold qubit states that should be moved back to the qubits.
                If ``None``, the states in any resonators will be returned to the qubits.
            apply_move: Whether the moves should be applied to the resonator tracking state.
            alt_qubit_names: physical to logical mapping????

        Returns:
            Instructions needed to move all qubit states out of the resonators.
        """
        if resonators is None:
            resonators = self.resonators

        instructions: list[Instruction] = []
        for r, q in self.res_state_owner.items():
            if r != q and r in resonators:
                # qbs = tuple(alt_qubit_names[q] if alt_qubit_names else q for q in [qubit, resonator])
                # instructions.append(Instruction(name=self.move_gate, qubits=qbs, args={}))
                instructions += self.create_move_instructions(
                    q, r, apply_move=apply_move, alt_qubit_names=alt_qubit_names
                )
        return instructions

    def available_resonators_to_move(self, qubits: Iterable[str]) -> dict[str, list[str]]:
        """Find out to which resonators the given qubits' states can be moved to.

        Args:
            qubits: The qubits to check.

        Returns:
            Mapping from qubit to a list of resonators its state can be moved to.
        """
        return {q: [r for r in self.resonators if q in self.available_moves[r]] for q in qubits}

    def resonators_holding_qubits(self, qubits: Iterable[str]) -> list[str]:
        """Return the resonators that are holding the state of one of the given qubits.

        Args:
            qubits: The qubits to check.

        Returns:
            Resonators holding their states.
        """
        return [r for r, q in self.res_state_owner.items() if q in qubits and q not in self.resonators]

    def choose_move_pair(
        self, qubits: list[str], remaining_instructions: list[list[str]]
    ) -> list[tuple[str, str, list[list[str]]]]:
        """Choose which of the given qubits to move into which resonator.


        , given a sequence of instructions to be
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

    def map_resonators_in_locus(self, locus: Iterable[str]) -> Locus:
        """Map any resonators in the given instruction locus into the QPU components whose state is
        currently stored in that resonator.

        If the resonator contains no qubit state at the moment, it is not changed.
        Non-resonator components in the locus are also unchanged.

        Args:
            locus: Instruction locus to map.

        Returns:
            The mapped locus.
        """
        return tuple(self.res_state_owner.get(q, q) for q in locus)


def transpile_insert_moves(
    circuit: Circuit,
    arch: DynamicQuantumArchitecture,
    *,
    existing_moves: Optional[ExistingMoveHandlingOptions] = None,
    qubit_mapping: Optional[dict[str, str]] = None,
) -> Circuit:
    """Convert a circuit for a fake architecture into a equivalent real architecture circuit with
    resonators and MOVE gates.

    The function does nothing if ``arch`` does not support MOVE gates.
    Note that this method normally assumes that ``circuit`` is transpiled to a fake architecture
    where the resonators have been abstracted away.

    Args:
        circuit: The fake architecture circuit to convert.
        arch: Real architecture of the target device.
        existing_moves: Specifies how to deal with existing MOVE instructions in ``circuit``, if any.
            If ``None``, the function will use :attr:`ExistingMoveHandlingOptions.REMOVE` with a user
            warning if there are MOVE instructions in ``circuit``.
        qubit_mapping: Mapping of logical qubit names to physical qubit names.
            Can be set to ``None`` if ``circuit`` already uses physical qubit names.

    Returns:
        Equivalent Star architecture circuit with MOVEs and resonators added.
    """
    tracker = _ResonatorStateTracker.from_dynamic_architecture(arch)

    # add missing QPU components to the mapping (mapped to themselves)
    if qubit_mapping is None:
        qubit_mapping = {}
    for q in arch.components:
        if q not in qubit_mapping.values():
            qubit_mapping[q] = q

    # see if the circuit already contains some MOVEs/resonators
    existing_moves_in_circuit = [i for i in circuit.instructions if i.name == tracker.move_gate]
    if existing_moves is None and len(existing_moves_in_circuit) > 0:
        warnings.warn('Circuit already contains MOVE instructions, removing them before transpiling.')
        existing_moves = ExistingMoveHandlingOptions.REMOVE

    if not tracker.supports_move:
        if not existing_moves_in_circuit:
            return circuit
        if existing_moves == ExistingMoveHandlingOptions.REMOVE:
            # TODO does this make sense?
            return transpile_remove_moves(circuit)
        raise ValueError('Circuit contains MOVE instructions, but the device does not support them.')

    if existing_moves is None or existing_moves == ExistingMoveHandlingOptions.REMOVE:
        # convert the circuit into a pure fake architecture circuit
        circuit = transpile_remove_moves(circuit)
    elif existing_moves == ExistingMoveHandlingOptions.KEEP:
        try:
            IQMClient._validate_circuit_moves(arch, circuit, qubit_mapping=qubit_mapping)
        except CircuitValidationError as e:
            raise CircuitTranspilationError(
                f'Unable to transpile the circuit after validation error: {e.args[0]}'
            ) from e

    rev_qubit_mapping = {v: k for k, v in qubit_mapping.items()}
    new_instructions = _transpile_insert_moves(list(circuit.instructions), tracker, arch, qubit_mapping)
    new_instructions += tracker.reset_as_move_instructions(alt_qubit_names=rev_qubit_mapping)

    return Circuit(name=circuit.name, instructions=new_instructions, metadata=circuit.metadata)


def _transpile_insert_moves(
    instructions: list[Instruction],
    tracker: _ResonatorStateTracker,
    arch: DynamicQuantumArchitecture,
    qubit_mapping: dict[str, str],
) -> list[Instruction]:
    """Convert a circuit for a fake architecture into a equivalent real architecture circuit with
    resonators and MOVE gates.

    Inserts MOVE gates into the circuit and changes the existing instruction loci as needed.
    Helper function for :func:`transpile_insert_moves`.

    Assumes only CZ and MOVE gates can be executed on a resonator.

    Args:
        instructions: The instructions in the circuit.
        tracker: Keeps track of the MOVE gate loci available, and the state stored in each resonator.
            At the end of the function the tracker is adjusted to reflect the state at the end of
            the returned instructions.
        arch: Real quantum architecture we transpile to.
        qubit_mapping: Mapping from logical qubit names to physical qubit names.

    Raises:
        CircuitTranspilationError: Raised when the circuit contains invalid gates that cannot be transpiled using this
            method.

    Returns:
        Real Star architecture equivalent of ``circuit`` with MOVEs and resonators added.
    """
    new_instructions = []
    # physical to logical
    rev_qubit_mapping = {v: k for k, v in qubit_mapping.items()}

    for idx, i in enumerate(instructions):
        qubits = [qubit_mapping[q] for q in i.qubits]
        res_match = tracker.resonators_holding_qubits(qubits)
        if res_match and i.name not in ['cz', tracker.move_gate]:
            # We have a gate on a qubit whose state is currently in a resonator, and that gate cannot
            # be executed on the resonator (incl. barriers)
            new_instructions += tracker.reset_as_move_instructions(res_match, alt_qubit_names=rev_qubit_mapping)
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
                if i.name == tracker.move_gate:  # update the tracker if needed
                    tracker.apply_move(*[qubit_mapping[q] for q in i.qubits])
            except CircuitValidationError as e:
                if i.name != 'cz':  # We can only fix cz gates at this point
                    raise CircuitTranspilationError(
                        f'Unable to transpile the circuit after validation error: {e.args[0]}'
                    ) from e
                # Pick which qubit-resonator pair to apply this cz to
                # Pick from qubits already in a resonator or both targets if none off them are in a resonator
                resonator_candidates: Optional[list[tuple[str, str, Any]]] = tracker.choose_move_pair(
                    [tracker.res_state_owner[res] for res in res_match] if res_match else qubits,
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
                new_instructions += tracker.reset_as_move_instructions(
                    [res for res in res_match if res != r], alt_qubit_names=rev_qubit_mapping
                )
                # move the qubit into the resonator if it was not yet in.
                if not res_match:
                    new_instructions += tracker.create_move_instructions(q1, r, alt_qubit_names=rev_qubit_mapping)
                new_instructions.append(
                    Instruction(name='cz', qubits=(rev_qubit_mapping[q2], rev_qubit_mapping[r]), args={})
                )
    return new_instructions


def transpile_remove_moves(circuit: Circuit) -> Circuit:
    """Convert a circuit involving resonators and MOVE gates into an equivalent circuit without them.

    The method assumes that in ``circuit`` a MOVE gate is always used to move a qubit state into a
    resonator before any gates act on the resonator. If this is not the case, this function will not
    work as intended.

    Args:
        circuit: The circuit from which resonators and MOVE gates should be removed.

    Returns:
        Equivalent fake architecture circuit without resonators and MOVEs.
    """
    tracker = _ResonatorStateTracker.from_circuit(circuit)
    new_instructions = []
    for i in circuit.instructions:
        if i.name == tracker.move_gate:
            # update the state tracking, drop the MOVE
            tracker.apply_move(*i.qubits)
        else:
            # map the instruction locus
            new_qubits = tracker.map_resonators_in_locus(i.qubits)
            new_instructions.append(
                Instruction(name=i.name, implementation=i.implementation, qubits=new_qubits, args=i.args)
            )
    return Circuit(name=circuit.name, instructions=new_instructions, metadata=circuit.metadata)
