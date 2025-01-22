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
    r"""Tracks the qubit states stored in computational resonators on the QPU as they are moved with MOVE gates.

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
    resonator_gates = ['cz']
    """Names of all other arity-2 gates that can be applied on a (qubit, resonator) locus.
    Other arity-2 gates are assumed to require a (qubit, qubit) locus."""
    # FIXME what if cz has both qr and qq loci?

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
            raise CircuitTranspilationError(f'MOVE locus {qubit, resonator} is not allowed.')

    def create_move_instructions(
        self,
        qubit: str,
        resonator: str,
    ) -> Iterable[Instruction]:
        """MOVE instruction(s) to move the state of the given resonator into the
        qubit that owns it if needed, and then move the state of the given qubit to the resonator.

        Args:
            qubit: The qubit
            resonator: The resonator

        Yields:
            The one or two MOVE instructions needed.
        """
        res_state_owner = self.res_state_owner[resonator]
        if res_state_owner not in [qubit, resonator]:
            locus = (res_state_owner, resonator)
            self.apply_move(*locus)
            yield Instruction(name=self.move_gate, qubits=locus, args={})

        locus = (qubit, resonator)
        self.apply_move(*locus)
        yield Instruction(name=self.move_gate, qubits=locus, args={})

    def reset_as_move_instructions(
        self,
        resonators: Optional[Iterable[str]] = None,
    ) -> list[Instruction]:
        """MOVE instructions that move all the states held in the given resonators back to their qubits.

        Applies the returned MOVE instructions on the tracker state.

        Args:
            resonators: Resonators that hold qubit states that should be moved back to the qubits.
                If ``None``, the states in any resonators will be returned to the qubits.

        Returns:
            Instructions needed to move all qubit states out of the resonators.
        """
        if resonators is None:
            resonators = self.resonators

        instructions: list[Instruction] = []
        for r, q in self.res_state_owner.items():
            if r != q and r in resonators:
                locus = (q, r)
                instructions.append(Instruction(name=self.move_gate, qubits=locus, args={}))
                self.apply_move(*locus)
        return instructions

    def available_resonators_to_move(self, qubits: Iterable[str]) -> dict[str, list[str]]:
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
                Number of resonator gates acting on the qubit until something else uses it.
            """
            qb, _ = locus
            score: int = 0
            for instr in remaining_instructions:
                if qb in instr.qubits:
                    if instr.name not in self.resonator_gates:
                        return score
                    score += 1
            return score

        # these MOVE loci are available
        r_candidates = [(q, r) for q, rs in self.available_resonators_to_move(qubits).items() for r in rs]
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

        Args:
            instructions: The instructions in the circuit, using physical qubit names.
            arch: Star quantum architecture we transpile to.

        Raises:
            CircuitTranspilationError: Raised when the circuit contains invalid gates that cannot be transpiled using this
                method.

        Returns:
            Star architecture equivalent of ``circuit`` with MOVEs and resonators added.
        """
        resonator_gates_and_move = self.resonator_gates + [self.move_gate]
        new_instructions = []

        # we must handle non-res instructions on qubits, res instructions + MOVE on (q,r), and res instructions on simplified (q,q)

        for idx, inst in enumerate(instructions):
            # are some of the locus qubits' states currently in a resonator?
            locus = inst.qubits
            res_match = self.resonators_holding_qubits(locus)

            try:
                IQMClient._validate_instruction(architecture=arch, instruction=inst)
                # instruction could be applied as is on locus
                if res_match:
                    # locus: qq, qr, rq, q
                    # Some locus qubits do not have their states.
                    if inst.name not in resonator_gates_and_move:
                        # Restore the qubits' states before applying the gate.
                        # FIXME As a consequence, a barrier closes a MOVE sandwich?
                        new_instructions += self.reset_as_move_instructions(res_match)

                    # Non-MOVE resonator gates *expect* the resonator to hold a state.
                    new_instructions.append(inst)

                    if inst.name == self.move_gate:
                        # MOVE(r->q): update the tracker
                        self.apply_move(*locus)
                else:
                    # locus: QQ, Qr, rQ, rr, Q, r
                    # locus qubits have their states (locus res may have another state)
                    new_instructions.append(inst)
                    if inst.name == self.move_gate:
                        # MOVE(q->r): update the tracker
                        self.apply_move(*locus)

            except CircuitValidationError as e:
                # gate can not be applied to this locus
                if inst.name not in self.resonator_gates:
                    # normal gates or MOVEs cannot be helped by adding MOVEs
                    raise CircuitTranspilationError(e) from e

                # simple res_gate(q,q) can be helped, move the state of one q into a res r so that we have res_gate(other_q, r)
                # res_gate(q,r)?

                #if res_match:
                # locus: qq, qr, rq
                # qq: one of the qubits needs to be moved into a resonator
                # Pick which qubit-resonator pair to apply this CZ to
                # Pick from qubits already in a resonator or both targets if none of them are in a resonator
                # else:
                # locus: QQ, Qr, rQ
                # Locus qubits already hold their states, no need to use MOVEs.

                # QQ can maybe helped, find move candidates for locus components, move one locus Q into a resonator for which we have resgate(Q, r).
                # Pick which qubit-resonator pair to apply this CZ to
                # Pick from qubits already in a resonator or both targets if none of them are in a resonator
                move_candidates = self.choose_move_pair(
                    [self.res_state_owner[res] for res in res_match] if res_match else locus,
                    instructions[idx:],
                )
                # find the best MOVE that produces a valid locus for the resonator gate
                for q1, r in move_candidates:
                    # the other CZ locus qubit is not moved
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
    Abstracts away the gate implementations, replacing them with a fake one.

    Does nothing if ``arch`` does not contain computational resonators.

    Args:
        arch: quantum architecture to convert

    Returns:
        equivalent simplified quantum architecture
    """
    # pylint: disable=too-many-nested-blocks
    # NOTE: assumes all qubit-resonator gates have the locus order (q, r)
    if not arch.computational_resonators:
        return arch

    op_loci = {gate_name: gate_info.loci for gate_name, gate_info in arch.gates.items()}
    r_set = frozenset(arch.computational_resonators)
    q_set = frozenset(arch.qubits)

    moves: dict[str, set[str]] = {}  # maps resonator r to qubits q for which we have MOVE(q, r) available
    for q, r in op_loci.pop('move', []):
        if q not in q_set or r not in r_set:
            raise ValueError(f'MOVE locus {q, r} is not of the form (qubit, resonator)')
        moves.setdefault(r, set()).add(q)

    new_gates = {}
    for op, loci in op_loci.items():
        new_loci: list[Locus] = []
        for locus in loci:
            if len(locus) == 2:
                # two-component op
                q1, r = locus
                if q1 not in q_set:
                    raise ValueError(f"Unexpected '{op}' locus: {locus}")

                if r in r_set:
                    # involves a resonator, for each G(q1, r), MOVE(q2, r) pair add G(q1, q2) to the simplified arch
                    for q2 in moves.get(r, []):
                        if q1 != q2:
                            new_loci.append((q1, q2))
                else:
                    # does not involve a resonator, keep
                    new_loci.append(locus)
            else:
                # other arities: keep as long as it does not involve a resonator
                if not set(locus) & r_set:
                    new_loci.append(locus)
        # implementation info is lost in the simplification
        new_gates[op] = GateInfo(
            implementations={'__fake': GateImplementationInfo(loci=tuple(new_loci))},
            default_implementation='__fake',
            override_default_implementation={},
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
            # FIXME does transpilation even need to catch MOVE/PRX violations etc? it can maybe fix them, and when submitting a circuit it is validated!
            #IQMClient._validate_circuit_moves(
            #    arch,
            #    Circuit(name=circuit.name, instructions=phys_instructions, metadata=circuit.metadata),
            #)
            pass
        except CircuitValidationError as e:
            raise CircuitTranspilationError(e) from e
    else:
        if circuit_has_moves and existing_moves == ExistingMoveHandlingOptions.REMOVE:
            # convert the circuit into a pure simplified architecture circuit
            circuit = transpile_remove_moves(circuit)

        # convert to physical qubit names
        phys_instructions = _map_loci(circuit.instructions, qubit_mapping)

    new_instructions = tracker.insert_moves(phys_instructions, arch)
    new_instructions += tracker.reset_as_move_instructions()

    # convert back to logical qubit names
    new_instructions = _map_loci(new_instructions, qubit_mapping, inverse=True)
    return Circuit(name=circuit.name, instructions=new_instructions, metadata=circuit.metadata)


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
