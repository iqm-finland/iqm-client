# Copyright 2021-2025 IQM client developers
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
"""Transpiling circuits to IQM devices involving computational resonators.

In the IQM Star architecture, computational resonators are connected to multiple qubits.
A MOVE gate can be used to move the state of a qubit to a connected, empty computational resonator,
and vice versa, so that effectively the qubit can be made to interact with other qubits connected
to the resonator. Additionally, two-qubit gates like CZ can be applied between a qubit
and a connected resonator. However, the resonator cannot be measured, and no single-qubit gates
can be applied on it.

To enable third-party transpilers to work on the IQM Star architecture, we may abstract away the
resonators and replace the real dynamic quantum architecture with a *simplified architecture*.
Specifically, this happens by removing the resonators from the architecture, and for
each resonator ``r``, for each pair of supported native qubit-resonator gates ``(G(q1, r), MOVE(q2, r))``
adding the fictional gate ``G(q1, q2)`` to the simplified architecture (since the latter can be
implemented as the sequence ``MOVE(q2, r), G(q1, r), MOVE(q2, r)``).

Before a circuit transpiled to a simplified architecture can be executed it must be further
transpiled to the real Star architecture using :func:`transpile_insert_moves`, which will introduce
the resonators, add MOVE gates as necessary to move the states, and convert the fictional two-qubit
gates into real native gates acting on qubit-resonator pairs.

Likewise :func:`transpile_remove_moves` can be used to perform the opposite transformation,
converting a circuit valid for the real Star architecture into an equivalent circuit for the
corresponding simplified architecture, e.g. so that the circuit can be retranspiled or optimized
using third-party tools that do not support the MOVE gate.

Given a :class:`DynamicQuantumArchitecture` for a Star architecture, the corresponding simplified
version can be obtained using :func:`simplified_architecture`.
"""
from __future__ import annotations
from copy import deepcopy

from collections.abc import Collection, Iterable
from enum import Enum
from typing import Optional

from iqm.iqm_client import (
    Circuit,
    CircuitTranspilationError,
    CircuitValidationError,
    DynamicQuantumArchitecture,
    Instruction,
    IQMClient,
)
from iqm.iqm_client.models import GateImplementationInfo, GateInfo, Locus


TRANSPILER_FIX: bool = True
#TRANSPILER_FIX: bool = False


class ExistingMoveHandlingOptions(str, Enum):
    """Options for how :func:`transpile_insert_moves` should handle existing MOVE instructions."""

    KEEP = 'keep'
    """Keep existing MOVE instructions, check if they are correct, and add more as needed."""
    TRUST = 'trust'
    """Keep existing MOVE instructions without checking if they are correct, and add more as needed."""
    REMOVE = 'remove'
    """Remove existing MOVE instructions using :func:`transpile_remove_moves`, and
    then add new ones as needed. This may produce a more optimized end result."""


def _map_loci(
    instructions: Iterable[Instruction],
    qubit_mapping: dict[str, str],
    inverse: bool = False,
) -> list[Instruction]:
    """Map the loci of the given instructions using the given qubit mapping, or its inverse.

    Args:
        instructions: Instructions whose loci are to be mapped.
        qubit_mapping: Mapping from one set of qubit names to another. Assumed to be injective.
        inverse: Invert ``qubit_mapping`` before using it.
    Returns:
        Copies of ``instructions`` with mapped loci.
    """
    if inverse:
        qubit_mapping = {phys: log for log, phys in qubit_mapping.items()}
    return list(
        inst.model_copy(update={'qubits': tuple(qubit_mapping[q] for q in inst.qubits)}) for inst in instructions
    )


class _ResonatorStateTracker:
    r"""Tracks the qubit states stored in computational resonators on a Star architecture QPU
    as they are moved with MOVE gates.

    Since the MOVE gate is not defined when acting on a :math:`|11\rangle` state,
    and involves an unknown phase, it is not equivalent to a SWAP.
    The state must always be moved back to its original qubit (this reverses the unknown phase),
    and no gates may be applied on the qubit while its state is in a resonator (to avoid populating
    the :math:`|11\rangle` state).

    Args:
        available_moves: Mapping from resonator to qubits with which it has a MOVE gate available.
    """

    move_gate = 'move'
    """Name of the MOVE gate in the architecture."""
    qr_gates = ['cz']
    """Names of all other arity-2 gates that can be applied on a (qubit, resonator) locus in the real
    Star architecture. Other arity-2 gates in the real architecture are assumed to require a
    (qubit, qubit) locus."""

    def __init__(self, available_moves: dict[str, list[str]]) -> None:
        self.available_moves = available_moves
        available_moves_inverse: dict[str, list[str]] = {}
        for r, qubits in available_moves.items():
            for q in qubits:
                available_moves_inverse.setdefault(q, []).append(r)
        self.available_moves_inverse = available_moves_inverse
        """Mapping from qubit to resonators it can be MOVEd into."""

        self.res_state_owner = {r: r for r in self.resonators}
        """Maps resonator to the QPU component whose state it currently holds."""

    @staticmethod
    def from_dynamic_architecture(arch: DynamicQuantumArchitecture) -> _ResonatorStateTracker:
        """Constructor to make a _ResonatorStateTracker from a dynamic quantum architecture.

        Args:
            arch: Architecture that determines the available MOVE gate loci.
        """
        resonators = set(arch.computational_resonators)
        available_moves: dict[str, list[str]] = {}
        if gate_info := arch.gates.get(_ResonatorStateTracker.move_gate):
            for q, r in gate_info.loci:
                if q in resonators or r not in resonators:
                    # NOTE we assume this in the rest of the code
                    raise ValueError(f'MOVE locus {q, r} is not of the form (qubit, resonator)')
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
    def resonators(self) -> Collection[str]:
        """Getter for the resonator registers that are being tracked."""
        return self.available_moves.keys()

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
                the MOVE gate is not available between this qubit-resonator pair, or the resonator is
                currently holding the state of a different qubit.
        """
        if (
            resonator in self.resonators
            and qubit in self.available_moves[resonator]
            and self.res_state_owner[resonator] in [qubit, resonator]
        ):
            self.res_state_owner[resonator] = qubit if self.res_state_owner[resonator] == resonator else resonator
        else:
            raise CircuitTranspilationError(f'MOVE locus {qubit, resonator} is not allowed.')

    def create_move_instructions(
        self,
        qubit: str,
        resonator: str,
    ) -> Iterable[Instruction]:
        """MOVE instruction(s) to move the state of the given qubit into the given resonator,
        or back to the qubit.

        If the resonator has the state of another qubit in it, or if qubit's state is in another resonator,
        restore them first using additional MOVE instructions.

        Args:
            qubit: The qubit
            resonator: The resonator

        Yields:
            1, 2 or 3 MOVE instructions.
        """
        # if the resonator has another qubit's state in it, restore it
        res_state_owner = self.res_state_owner[resonator]
        if res_state_owner not in [qubit, resonator]:
            locus = (res_state_owner, resonator)
            self.apply_move(*locus)
            yield Instruction(name=self.move_gate, qubits=locus, args={})

        # if the qubit does not hold its own state, restore it, unless it's in the resonator
        # find where the qubit state is (it can be in at most one resonator)
        res = [r for r, q in self.res_state_owner.items() if q == qubit]  # TODO not efficient
        if res and (qubit_state_holder := res[0]) != resonator:
            locus = (qubit, qubit_state_holder)
            self.apply_move(*locus)
            yield Instruction(name=self.move_gate, qubits=locus, args={})

        # move qubit state to resonator, or back to the qubit
        locus = (qubit, resonator)
        self.apply_move(*locus)
        yield Instruction(name=self.move_gate, qubits=locus, args={})

    def reset_as_move_instructions(
        self,
        resonators: Optional[Iterable[str]] = None,
    ) -> list[Instruction]:
        """MOVE instructions that move the states held in the given resonators back to their qubits.

        Applies the returned MOVE instructions on the tracker state.

        Args:
            resonators: Resonators that (may) hold qubit states that should be moved back to the qubits.
                If ``None``, the states in all known resonators will be returned to the qubits.

        Returns:
            MOVE instructions needed to move the states out of ``resonators`` into
            the qubits they belong to.
        """
        if resonators is None:
            resonators = self.resonators

        instructions: list[Instruction] = []
        for r in resonators:
            q = self.res_state_owner[r]
            # if the state in r does not belong to r, restore it to its owner
            if q != r:
                locus = (q, r)
                instructions.append(Instruction(name=self.move_gate, qubits=locus, args={}))
                self.apply_move(*locus)
        return instructions

    def resonators_to_move_to(self, qubits: Iterable[str]) -> dict[str, list[str]]:
        """Find out to which resonators the given qubits' states can be moved to.

        Args:
            qubits: The qubits to check.

        Returns:
            Mapping from qubit to a list of resonators its state can be moved to.
            If a qubit cannot be moved into a resonator, it does not appear in the mapping.
        """
        return {q: resonators for q in qubits if (resonators := self.available_moves_inverse.get(q))}

    def resonators_holding_qubits(self, qubits: Iterable[str]) -> list[str]:
        """Return the resonators that are holding the state of one of the given qubits.

        Args:
            qubits: The qubits to check.

        Returns:
            Resonators that hold the state of one of ``qubits``.
        """
        # a resonator can only hold the state of a connected qubit, or its own state
        # TODO needs to be made more efficient once we have lots of resonators
        return [r for r, q in self.res_state_owner.items() if q != r and q in qubits]

    def choose_move_pair(
        self, qubits: Iterable[str], remaining_instructions: Iterable[Instruction]
    ) -> list[tuple[str, str]]:
        """Choose which of the given qubits to move into which resonator.

        The choice is made using a heuristic based on the given lookahead sequence
        of instructions to executed later.

        Args:
            qubits: The qubits to choose from.
            remaining_instructions: Look-ahead instructions.

        Raises:
            CircuitTranspilationError: No MOVE locus is available, most likely because the circuit
                was not properly routed.

        Returns:
            Sorted preference list of (qubit, resonator) loci to apply a MOVE on.
        """

        def choice_heuristic(locus: tuple[str, str]) -> int:
            """A simple look ahead heuristic for choosing which qubit to move into which resonator.

            FIXME out of where??? until the qubit needs to be moved out.
            FIXME what if we have multiple resonators? the cz gates we count into the score might use another resonator???

            Args:
                locus: Possible MOVE gate locus, (qubit, resonator).
            Returns:
                Number of qubit-resonator gates acting on the qubit until something else uses it.
            """
            qb, _ = locus
            score: int = 0
            for instr in remaining_instructions:
                if qb in instr.qubits:
                    if instr.name not in self.qr_gates:
                        return score
                    score += 1
            return score

        # these MOVE loci are available
        r_candidates = [(q, r) for q, rs in self.resonators_to_move_to(qubits).items() for r in rs]
        if not r_candidates:
            raise CircuitTranspilationError(
                f'Unable to insert MOVE gates because none of the qubits {qubits} can be moved into a resonator. '
                + 'This can be resolved by routing the circuit first without resonators.'
            )
        resonator_candidates = list(sorted(r_candidates, key=choice_heuristic, reverse=True))
        return resonator_candidates

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

    def insert_moves(
        self,
        instructions: list[Instruction],
        arch: DynamicQuantumArchitecture,
    ) -> list[Instruction]:
        """Convert a simplified architecture circuit into a equivalent Star architecture circuit with
        resonators and MOVE gates.

        Inserts MOVE gates into the circuit and changes the existing instruction loci as needed,
        while updating the state of the tracker object.

        Can also handle circuits that mix the simplified and real architectures.

        Args:
            instructions: The instructions in the circuit, using physical qubit names.
            arch: Real Star quantum architecture we transpile to.

        Raises:
            CircuitTranspilationError: Raised when the circuit contains invalid gates that cannot be transpiled using this
                method.

        Returns:
            Real Star architecture equivalent of ``circuit`` with MOVEs and resonators added.
        """
        # This method can handle real single- and two-qubit gates, real q-r gates including MOVE,
        # and fictional two-qubit gates which it decomposes into real q-r gates.
        new_instructions = []

        for idx, inst in enumerate(instructions):
            locus = inst.qubits

            # key: Q=qubit holding its own state, q=qubit not holding its state, r=resonator
            # possible loci: qq, Qq, qQ, QQ, qr, rq, Qr, rQ, rr, q, Q, r
            try:
                IQMClient._validate_instruction(architecture=arch, instruction=inst)
                # inst can be applied as is on locus, but we may first need to use MOVEs to make
                # sure the locus qubits contain their states

                if inst.name == self.move_gate:
                    # apply the requested MOVE, closing interfering MOVE sandwiches first
                    new_instructions += self.create_move_instructions(*locus)
                    continue

                # are some of the locus qubits' states currently in a resonator?
                if res_match := self.resonators_holding_qubits(locus):
                    # Some locus qubits do not hold their states, which need to be restored before applying the gate.
                    # FIXME As a consequence, a barrier closes a MOVE sandwich?
                    new_instructions += self.reset_as_move_instructions(res_match)
                new_instructions.append(inst)

            except CircuitValidationError as e:
                # inst can not be applied to this locus as is
                if inst.name not in self.qr_gates or any(c in self.resonators for c in locus):
                    raise CircuitTranspilationError(e) from e

                # Fictional qubit-qubit gates G can be made valid by decomposing them using MOVEs.
                # We move the state of one qubit q1 into resonator r, and then apply G(q2, r).
                # locus: qq, Qq, qQ, QQ

                res_match = self.resonators_holding_qubits(locus)

                # find the best MOVE(s) to enable the fictional gate to be implemented
                # qq, qQ, Qq: only check the q qubits for moves
                # QQ:  find move candidates for both locus components
                # FIXME logic is broken, cannot handle the multiple resonator case
                move_candidates = self.choose_move_pair(
                    [self.res_state_owner[res] for res in res_match] if res_match else locus,
                    instructions[idx:],
                )
                for q1, r in move_candidates:
                    # the other fictional gate locus qubit is not moved
                    q2 = [q for q in locus if q != q1][0]
                    new_inst = inst.model_copy(update={'qubits': (q2, r)})
                    try:
                        IQMClient._validate_instruction(architecture=arch, instruction=new_inst)
                        break
                    except CircuitValidationError:
                        pass
                else:
                    # ran out of MOVE candidates, did not hit break
                    raise CircuitTranspilationError(
                        f'Unable to find a valid qubit-resonator pair for a MOVE gate to enable {inst.name} at {locus}.'
                    ) from e

                # remove the other qubit from the resonator if it was in
                new_instructions += self.reset_as_move_instructions([res for res in res_match if res != r])

                # move the qubit into the resonator if it was not yet in.
                if not res_match:
                    new_instructions += self.create_move_instructions(q1, r)
                new_instructions.append(new_inst)

        return new_instructions




def simplified_architecture(arch: DynamicQuantumArchitecture) -> DynamicQuantumArchitecture:
    """Converts the given IQM Star quantum architecture into the equivalent simplified quantum architecture.

    See :mod:`iqm.iqm_client.transpile` for the details.

    Abstracts away the gate implementations of fictional gates.
    Does nothing if ``arch`` does not contain computational resonators.

    Args:
        arch: quantum architecture to convert

    Returns:
        equivalent simplified quantum architecture with fictional gates
    """
    # xpylint: disable=too-many-nested-blocks
    # NOTE: assumes all qubit-resonator gates have the locus order (q, r)
    if not arch.computational_resonators:
        return arch

    # we modify the contents, so make a copy
    gates = deepcopy(arch.gates)

    r_set = frozenset(arch.computational_resonators)
    q_set = frozenset(arch.qubits)

    moves: dict[str, set[str]] = {}  # maps resonator r to qubits q for which we have MOVE(q, r) available
    for q, r in gates.pop('move').loci if 'move' in gates else []:
        if q not in q_set or r not in r_set:
            raise ValueError(f'MOVE locus {q, r} is not of the form (qubit, resonator)')
        moves.setdefault(r, set()).add(q)

    # create fictional gates, remove real gate loci that involve a resonator
    new_gates: dict[str, GateInfo] = {}
    for gate_name, gate_info in gates.items():
        new_loci: dict[str, list[Locus]] = {}  # mapping from implementation to its new loci
        fictional_loci: set[Locus] = set()  # loci for new fictional gates

        for impl_name, impl_info in gate_info.implementations.items():
            kept_impl_loci: list[Locus] = []  # these real loci we keep for this implementation
            for locus in impl_info.loci:
                if len(locus) == 2:
                    # two-component op
                    q1, r = locus
                    if q1 not in q_set:
                        raise ValueError(f"Unexpected '{op}' locus: {locus}")

                    if r in r_set:
                        # involves a resonator, for each G(q1, r), MOVE(q2, r) pair add G(q1, q2) to the simplified arch
                        for q2 in moves.get(r, []):
                            if q1 != q2:
                                # set because multiple resonators can produce the same fictional locus
                                fictional_loci.add((q1, q2))
                    else:
                        # does not involve a resonator, keep
                        kept_impl_loci.append(locus)
                else:
                    # other arities: keep as long as it does not involve a resonator
                    if not set(locus) & r_set:
                        kept_impl_loci.append(locus)
            new_loci[impl_name] = tuple(kept_impl_loci)

        # implementation info is lost in the simplification
        if fictional_loci:
            new_loci['__fictional'] = tuple(fictional_loci)

        new_gates[gate_name] = gate_info.model_copy(
            update={'implementations': {impl_name: GateImplementationInfo(loci=loci) for impl_name, loci in new_loci.items()}},
        )

    return DynamicQuantumArchitecture(
        calibration_set_id=arch.calibration_set_id,
        qubits=arch.qubits,
        computational_resonators=[],
        gates=new_gates,
    )


def transpile_insert_moves(
    circuit: Circuit,
    arch: DynamicQuantumArchitecture,
    *,
    existing_moves: ExistingMoveHandlingOptions = ExistingMoveHandlingOptions.KEEP,
    qubit_mapping: Optional[dict[str, str]] = None,
    restore_states: bool = True,
) -> Circuit:
    """Convert a simplified architecture circuit into an equivalent Star architecture circuit with
    resonators and MOVE gates, if needed.

    In the typical use case ``circuit`` has been transpiled to a simplified architecture
    where the resonators have been abstracted away, and this function converts it into
    the corresponding Star architecture circuit.

    It can also handle the case where ``circuit`` already contains MOVE gates and resonators,
    which are treated according to ``existing_moves``, followed by the conversion
    of the two-qubit gates that are not supported by the Star architecture.

    The function does nothing if ``arch`` does not support MOVE gates.

    Args:
        circuit: The circuit to convert.
        arch: Real Star architecture of the target device.
        existing_moves: Specifies how to deal with existing MOVE instructions in ``circuit``, if any.
        qubit_mapping: Mapping of logical qubit names to physical qubit names.
            Can be set to ``None`` if ``circuit`` already uses physical qubit names.
        restore_states: Iff True, all qubit states held in resonators are returned to their qubits
            at the end of the circuit (i.e. all MOVE sandwiches are closed), even when there
            is no computational reason to do so.

    Returns:
        Equivalent Star architecture circuit with MOVEs and resonators added.
    """
    tracker = _ResonatorStateTracker.from_dynamic_architecture(arch)

    # see if the circuit already contains some MOVEs/resonators
    circuit_has_moves = any(i for i in circuit.instructions if i.name == tracker.move_gate)
    # can we use MOVEs?
    if not tracker.supports_move:
        if circuit_has_moves:
            raise ValueError('Circuit contains MOVE instructions, but the device does not support them.')
        # nothing to do (do not validate the circuit)
        return circuit

    # add missing QPU components to the mapping (mapped to themselves)
    if qubit_mapping is None:
        qubit_mapping = {}
    for c in set(arch.components) - set(qubit_mapping.values()):
        qubit_mapping[c] = c

    if existing_moves == ExistingMoveHandlingOptions.KEEP:
        # convert to physical qubit names
        phys_instructions = _map_loci(circuit.instructions, qubit_mapping)
        try:
            if not TRANSPILER_FIX:
                IQMClient._validate_circuit_moves(
                    arch,
                    Circuit(name=circuit.name, instructions=phys_instructions, metadata=circuit.metadata),
                )

        except CircuitValidationError as e:
            raise CircuitTranspilationError(e) from e
    else:
        if circuit_has_moves and existing_moves == ExistingMoveHandlingOptions.REMOVE:
            # convert the circuit into a pure simplified architecture circuit
            circuit = transpile_remove_moves(circuit)

        # convert to physical qubit names
        phys_instructions = _map_loci(circuit.instructions, qubit_mapping)

    if TRANSPILER_FIX:
        new_instructions = tracker.insert_moves(phys_instructions, arch)
    else:
        new_instructions = _transpile_insert_moves(phys_instructions, tracker, arch)

    if restore_states:
        new_instructions += tracker.reset_as_move_instructions()

    # convert back to logical qubit names
    new_instructions = _map_loci(new_instructions, qubit_mapping, inverse=True)
    return Circuit(name=circuit.name, instructions=new_instructions, metadata=circuit.metadata)


def _transpile_insert_moves(
    instructions: list[Instruction],
    tracker: _ResonatorStateTracker,
    arch: DynamicQuantumArchitecture,
) -> list[Instruction]:
    """Convert a simplified architecture circuit into a equivalent Star architecture circuit with
    resonators and MOVE gates.

    Inserts MOVE gates into the circuit and changes the existing instruction loci as needed.
    Helper function for :func:`transpile_insert_moves`.

    Assumes only CZ and MOVE gates can be executed on a resonator.

    Args:
        instructions: The instructions in the circuit, using physical qubit names.
        tracker: Keeps track of the MOVE gate loci available, and the state stored in each resonator.
            At the end of the function the tracker is adjusted to reflect the state at the end of
            the returned instructions.
        arch: Star quantum architecture we transpile to.

    Raises:
        CircuitTranspilationError: Raised when the circuit contains invalid gates that cannot be transpiled using this
            method.

    Returns:
        Star architecture equivalent of ``circuit`` with MOVEs and resonators added.
    """
    new_instructions = []
    for idx, inst in enumerate(instructions):
        locus = inst.qubits

        # are some of the locus qubits' states currently in a resonator?
        res_match = tracker.resonators_holding_qubits(locus)
        if res_match and inst.name not in ['cz', tracker.move_gate]:
            # We have a gate on a qubit whose state is currently in a resonator, and that gate cannot
            # be executed on the resonator (incl. barriers), so return the state to the qubit and then apply the gate.
            new_instructions += tracker.reset_as_move_instructions(res_match)
            new_instructions.append(inst)
        else:
            # Either the gate locus does not involve qubits whose states are in a resonator,
            # or the gate is MOVE or CZ.
            # Check if the instruction is valid, which raises an exception if not.
            try:
                IQMClient._validate_instruction(
                    architecture=arch,
                    instruction=inst,
                )
                new_instructions.append(inst)  # No adjustment needed
                if inst.name == tracker.move_gate:
                    # MOVE: update the tracker
                    tracker.apply_move(*locus)
            except CircuitValidationError as e:
                if inst.name != 'cz':  # We can only fix CZ gates at this point
                    raise CircuitTranspilationError(e) from e
                # CZ: cannot be applied to this locus, one of the qubits needs to be moved into a resonator.
                # Pick which qubit-resonator pair to apply this CZ to
                # Pick from qubits already in a resonator or both targets if none off them are in a resonator
                move_candidates = tracker.choose_move_pair(
                    [tracker.res_state_owner[res] for res in res_match] if res_match else locus,
                    instructions[idx:],
                )
                for q1, r in move_candidates:
                    # the other CZ locus qubit is not moved
                    q2 = [q for q in locus if q != q1][0]
                    try:
                        IQMClient._validate_instruction(
                            architecture=arch,
                            instruction=Instruction(name='cz', qubits=(q2, r), args={}),
                        )
                        break
                    except CircuitValidationError:
                        pass
                else:
                    # ran out of candidates, did not hit break
                    raise CircuitTranspilationError(
                        'Unable to find a valid qubit-resonator pair for a MOVE gate to enable this CZ gate.'
                    ) from e

                # remove the other qubit from the resonator if it was in
                new_instructions += tracker.reset_as_move_instructions([res for res in res_match if res != r])

                # move the qubit into the resonator if it was not yet in.
                if not res_match:
                    new_instructions += tracker.create_move_instructions(q1, r)
                new_instructions.append(Instruction(name='cz', qubits=(q2, r), args={}))
    return new_instructions


def transpile_remove_moves(circuit: Circuit) -> Circuit:
    """Convert a Star architecture circuit involving resonators and MOVE gates into an equivalent
    simplified achitecture circuit without them.

    The method assumes that in ``circuit`` a MOVE gate is always used to move a qubit state into a
    resonator before any other gates act on the resonator. If this is not the case, this function
    will not work as intended.

    Args:
        circuit: Star architecture circuit from which resonators and MOVE gates should be removed.

    Returns:
        Equivalent simplified architecture circuit without resonators and MOVEs.

    """
    tracker = _ResonatorStateTracker.from_circuit(circuit)
    new_instructions = []
    for inst in circuit.instructions:
        if inst.name == tracker.move_gate:
            # update the state tracking, drop the MOVE
            tracker.apply_move(*inst.qubits)
        else:
            # map the instruction locus
            new_qubits = tracker.map_resonators_in_locus(inst.qubits)
            new_instructions.append(
                Instruction(name=inst.name, implementation=inst.implementation, qubits=new_qubits, args=inst.args)
            )
    return Circuit(name=circuit.name, instructions=new_instructions, metadata=circuit.metadata)
