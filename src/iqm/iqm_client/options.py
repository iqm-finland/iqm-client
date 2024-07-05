from dataclasses import dataclass
from enum import Enum
from typing import Final, Optional

from iqm.iqm_client.quantum_architecture import QuantumArchitectureSpecification

import warnings


class HeraldingMode(str, Enum):
    """Heralding mode for circuit execution.

    Heralding is the practice of generating data about the state of qubits prior to execution of a circuit.
    This can be achieved by measuring the qubits immediately before executing each shot for a circuit."""

    NONE = 'none'
    """Do not do any heralding."""
    ZEROS = 'zeros'
    """Perform a heralding measurement after qubit initialization, only retain shots with an all-zeros result.

    Note: in this mode, the number of shots returned after execution will be less or equal to the requested amount
    due to the post-selection based on heralding data."""


class MoveGateValidationMode(Enum):
    """MOVE gate validation mode for circuit compilation. This options is meant for advanced users."""

    STRICT: Final[str] = 'strict'
    """Perform standard MOVE gate validation: MOVE gates must only appear in sandwiches, with no gates acting on the
    MOVE qubit inside the sandwich."""
    ALLOW_PRX: Final[str] = 'allow_prx'
    """Allow PRX gates on the MOVE qubit inside MOVE sandwiches during validation."""
    NONE: Final[str] = 'none'
    """Do not perform any MOVE gate validation."""


class MoveGateFrameTrackingMode(Enum):
    """MOVE gate frame tracking mode for circuit compilation. This option is meant for advanced users."""

    FULL: Final[str] = 'full'
    """Perform complete MOVE gate frame tracking."""
    NO_DETUNING_CORRECTION: Final[str] = 'no_detuning_correction'
    """Do not add the phase detuning corrections to the pulse schedule for the MOVE gate. The user is expected to do
    these manually."""
    NONE: Final[str] = 'none'
    """Do not perform any MOVE gate frame tracking. The user is expected to do these manually."""


class CircuitCompilationOptions:
    """Various discrete options for quantum circuit compilation to pulse schedule."""

    def __init__(
        self,
        max_circuit_duration_over_t2: Optional[float] = None,
        heralding_mode: Optional[HeraldingMode] = None,
        move_gate_validation: Optional[MoveGateValidationMode] = None,
        move_gate_frame_tracking: Optional[MoveGateFrameTrackingMode] = None,
    ) -> None:
        """Initialize the circuit compilation options.

        Args:
            max_circuit_duration_over_t2:  Circuits are disqualified on the server if they are longer than this ratio
                of the T2 time of the qubits. Setting this value to ``0.0`` turns off circuit duration checking.
                The default value ``None`` instructs server to use server's default value in the checking.
            heralding_mode: Heralding mode to use during the execution.
            move_gate_validation: The MOVE gate validation mode for circuit compilation.
            move_gate_frame_tracking: The MOVE gate frame tracking mode for circuit compilation.
        """
        if move_gate_frame_tracking == MoveGateFrameTrackingMode.FULL and move_gate_validation not in [
            MoveGateValidationMode.STRICT,
            MoveGateValidationMode.ALLOW_PRX,
            None,
        ]:
            raise ValueError(
                'Unable to perform full MOVE gate frame tracking if MOVE gate validation is not "strict" or "allow_prx".'
            )
        self.max_circuit_duration_over_t2 = max_circuit_duration_over_t2
        self.heralding_mode = heralding_mode
        self.move_gate_validation = move_gate_validation
        self.move_gate_frame_tracking = move_gate_frame_tracking

    def _validate_and_fill_in(
        self, arch: QuantumArchitectureSpecification, circuit: "CircuitBatch"
    ) -> "CircuitCompilationOptions":
        """Validate the options and fill in the missing values."""
        if 'move' not in arch.operations.keys():
            if self.move_gate_validation is not None:
                warnings.warn("MOVE gate validation is not supported by the architecture. Ignoring the option.")
            elif self.move_gate_frame_tracking is not None:
                warnings.warn("MOVE gate frame tracking is not supported by the architecture. Ignoring the option.")
        elif not any('move' in op for op in circuit.operations):
            if self.move_gate_validation is not None:
                warnings.warn(
                    "MOVE gate validation is only relevant for circuits with MOVE gates. Ignoring the option."
                )
            elif self.move_gate_frame_tracking is not None:
                warnings.warn(
                    "MOVE gate frame tracking is only relevant for circuits with MOVE gates. Ignoring the option."
                )
        new_options = CircuitCompilationOptions(
            max_circuit_duration_over_t2=self.max_circuit_duration_over_t2,
            heralding_mode=self.heralding_mode if self.heralding_mode is not None else HeraldingMode.NONE,
            move_gate_validation=(
                self.move_gate_validation if self.move_gate_validation is not None else MoveGateValidationMode.STRICT
            ),
            move_gate_frame_tracking=(
                self.move_gate_frame_tracking
                if self.move_gate_frame_tracking is not None
                else MoveGateFrameTrackingMode.FULL
            ),
        )
        return new_options
