# Copyright 2024 IQM client developers
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
"""This module contains the data models used by IQMClient."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, StrictStr, field_validator
from pydantic_core.core_schema import ValidationInfo

# Supported instruction configuration values:
# - 'arity': the arity of the locus; use -1 to allow any arity.
# - 'args': allowed arguments for the operation.
# - 'directed': if True, the loci defined in the architecture description are considered directed.
# - 'renamed_to': if set, indicates that this instruction name is deprecated, and IQM client will
#    auto-rename it to the new name.
# - 'check_locus': if False, skips the locus checking entirely. If set to the string
#   value 'any_combination', will check that the qubits in the instruction locus are found
#   in the architecture definition, but will allow any combination of them in.

SUPPORTED_INSTRUCTIONS: dict[str, dict[str, Any]] = {
    'barrier': {
        'arity': -1,
        'args': {},
        'check_locus': False,
    },
    'cz': {
        'arity': 2,
        'args': {},
        'directed': False,
    },
    'move': {
        'arity': 2,
        'args': {},
        'directed': True,
    },
    'measure': {
        'arity': -1,
        'args': {
            'key': (str,),
        },
        'check_locus': 'any_combination',
    },
    'measurement': {  # deprecated
        'arity': -1,
        'args': {
            'key': (str,),
        },
        'renamed_to': 'measure',
        'check_locus': 'any_combination',
    },
    'prx': {
        'arity': 1,
        'args': {
            'angle_t': (
                float,
                int,
            ),
            'phase_t': (
                float,
                int,
            ),
        },
    },
    'phased_rx': {  # deprecated
        'arity': 1,
        'args': {
            'angle_t': (
                float,
                int,
            ),
            'phase_t': (
                float,
                int,
            ),
        },
        'renamed_to': 'prx',
    },
}


class Instruction(BaseModel):
    r"""

    The :class:`Instruction` class represents a native quantum operation.

    Different Instruction types are distinguished by their :attr:`~Instruction.name`.
    Each Instruction type acts on a number of :attr:`~Instruction.qubits`, and expects certain
    :attr:`~Instruction.args`.

    We currently support the following native instruction types:

    ================ =========== ====================================== ===========
    name             # of qubits args                                   description
    ================ =========== ====================================== ===========
    measure          >= 1        ``key: str``                           Measurement in the Z basis.
    prx              1           ``angle_t: float``, ``phase_t: float`` Phased x-rotation gate.
    cz               2                                                  Controlled-Z gate.
    barrier          >= 1                                               Execution barrier.
    move             2                                                  Moves 1 state between resonator and qubit.
    ================ =========== ====================================== ===========

    For each Instruction you may also optionally specify :attr:`~Instruction.implementation`,
    which contains the name of an implementation of the instruction to use.
    Support for multiple implementations is currently experimental and in normal use the
    field should be omitted, this selects the default implementation for the instruction.

    .. note::

        The following instruction names are deprecated, but supported for backwards compatibility for now:

    * ``phased_rx`` ↦ ``prx``
    * ``measurement`` ↦ ``measure``

    Measure
    -------

    Measurement in the computational (Z) basis. The measurement results are the output of the circuit.
    Takes one string argument, ``key``, denoting the measurement key the results are labeled with.
    All the measurement keys in a circuit must be unique. Each qubit may only be measured once.
    The measurement must be the last operation on each qubit, i.e. it cannot be followed by gates.

    .. code-block:: python
        :caption: Example

        Instruction(name='measure', qubits=('alice', 'bob', 'charlie'), args={'key': 'm1'})

    PRX
    ---

    Phased x-rotation gate, i.e. an x-rotation conjugated by a z-rotation.
    Takes two arguments, the rotation angle ``angle_t`` and the phase angle ``phase_t``,
    both measured in units of full turns (:math:`2\pi` radians).
    The gate is represented in the standard computational basis by the matrix

    .. math::
        \text{PRX}(\theta, \phi) = \exp(-i (X \cos (2 \pi \; \phi) + Y \sin (2 \pi \; \phi)) \: \pi \; \theta)
        = \text{RZ}(\phi) \: \text{RX}(\theta) \: \text{RZ}^\dagger(\phi),

    where :math:`\theta` = ``angle_t``, :math:`\phi` = ``phase_t``,
    and :math:`X` and :math:`Y` are Pauli matrices.

    .. code-block:: python
        :caption: Example

        Instruction(name='prx', qubits=('bob',), args={'angle_t': 0.7, 'phase_t': 0.25})

    CZ
    --

    Controlled-Z gate. Represented in the standard computational basis by the matrix

    .. math:: \text{CZ} = \text{diag}(1, 1, 1, -1).

    It is symmetric wrt. the qubits it's acting on, and takes no arguments.

    .. code-block:: python
        :caption: Example

        Instruction(name='cz', qubits=('alice', 'bob'), args={})

    MOVE
    ----

    The MOVE operation is a unitary population exchange operation between a qubit and a resonator.
    Its effect is only defined in the invariant subspace :math:`S = \text{span}\{|00\rangle, |01\rangle, |10\rangle\}`,
    where it swaps the populations of the states :math:`|01\rangle` and :math:`|10\rangle`.
    Its effect on the orthogonal subspace is undefined.

    MOVE has the following presentation in the subspace :math:`S`:

    .. math:: \text{MOVE}_S = |00\rangle \langle 00| + a |10\rangle \langle 01| + a^{-1} |01\rangle \langle 10|,

    where :math:`a` is an undefined complex phase that is canceled when the MOVE gate is applied a second time.

    To ensure that the state of the qubit and resonator has no overlap with :math:`|11\rangle`, it is
    recommended that no single qubit gates are applied to the qubit in between a
    pair of MOVE operations.

    .. code-block:: python
        :caption: Example

        Instruction(name='move', qubits=('alice', 'resonator'), args={})

    Barrier
    -------

    A barrier instruction affects the physical execution order of the instructions elsewhere in the
    circuit that act on qubits spanned by the barrier.
    It ensures that any such instructions that succeed the barrier are only executed after
    all such instructions that precede the barrier have been completed.
    Hence it can be used to guarantee a specific causal order for the other instructions.
    It takes no arguments, and has no other effect.

    .. code-block:: python
        :caption: Example

        Instruction(name='barrier', qubits=('alice', 'bob'), args={})

    *Note*
    1-qubit barriers will not have any effect on circuit's compilation and execution. Higher layers
    that sit on top of IQM Client can make actual use of 1-qubit barriers (e.g. during circuit optimization),
    therefore having them is allowed.

    """

    name: str = Field(..., examples=['measure'])
    """name of the quantum operation"""
    implementation: Optional[StrictStr] = Field(None)
    """name of the implementation, for experimental use only"""
    qubits: tuple[StrictStr, ...] = Field(..., examples=[('alice',)])
    """names of the logical qubits the operation acts on"""
    args: dict[str, Any] = Field(..., examples=[{'key': 'm'}])
    """arguments for the operation"""

    def __init__(self, **data):
        super().__init__(**data)
        # Auto-convert name if a deprecated name is used
        self.name = get_current_instruction_name(self.name)

    @field_validator('name')
    @classmethod
    def name_validator(cls, value):
        """Check if the name of instruction is set to one of the supported quantum operations"""
        name = value
        if name not in SUPPORTED_INSTRUCTIONS:
            raise ValueError(
                f'Unknown instruction "{name}". '
                f'Supported instructions are \"{", ".join(SUPPORTED_INSTRUCTIONS.keys())}\"'
            )
        return name

    @field_validator('implementation')
    @classmethod
    def implementation_validator(cls, value):
        """Check if the implementation of the instruction is set to a non-empty string"""
        implementation = value
        if isinstance(implementation, str):
            if not implementation:
                raise ValueError('Implementation of the instruction should be None, or a non-empty string')
        return implementation

    @field_validator('qubits')
    @classmethod
    def qubits_validator(cls, value, info: ValidationInfo):
        """Check if the instruction has the correct number of qubits according to the instruction's type"""
        qubits = value
        name = info.data.get('name')
        if not name:
            raise ValueError('Could not validate qubits because the name of the instruction did not pass validation')
        arity = SUPPORTED_INSTRUCTIONS[name]['arity']
        if (0 <= arity) and (arity != len(qubits)):
            raise ValueError(
                f'The "{name}" instruction acts on {arity} qubit(s), but {len(qubits)} were given: {qubits}'
            )
        return qubits

    @field_validator('args')
    @classmethod
    def args_validator(cls, value, info: ValidationInfo):
        """Check argument names and types for a given instruction"""
        args = value
        name = info.data.get('name')
        if not name:
            raise ValueError('Could not validate args because the name of the instruction did not pass validation')

        # Check argument names
        submitted_arg_names = set(args.keys())
        supported_arg_names = set(SUPPORTED_INSTRUCTIONS[name]['args'].keys())
        if submitted_arg_names != supported_arg_names:
            raise ValueError(
                f'The instruction "{name}" requires '
                f'{tuple(supported_arg_names) if supported_arg_names else "no"} argument(s), '
                f'but {tuple(submitted_arg_names)} were given'
            )

        # Check argument types
        for arg_name, arg_value in args.items():
            supported_arg_types = SUPPORTED_INSTRUCTIONS[name]['args'][arg_name]
            if not isinstance(arg_value, supported_arg_types):
                raise TypeError(
                    f'The argument "{arg_name}" should be of one of the following supported types'
                    f' {supported_arg_types}, but ({type(arg_value)}) was given'
                )

        return value


def is_multi_qubit_instruction(name: str) -> bool:
    """Checks if the instruction with the given name is a multi-qubit instruction.

    Args:
        name: The name of the instruction to check

    Returns:
        True if the instruction expects more than one qubit as its locus.
    """
    return name in SUPPORTED_INSTRUCTIONS and SUPPORTED_INSTRUCTIONS[name]['arity'] > 1


def is_directed_instruction(name: str) -> bool:
    """Checks if the instruction with the given name is directed, i.e. if the instruction
    is allowed only in the direction defined by the operation loci in the quantum architecture.

    Args:
        name: The name of the instruction to check

    Returns:
        True if the instruction is valid only in the direction defined by the architecture specification; or
        False if the instruction is valid also with the qubits in the locus in reversed order.
    """
    return (
        name in SUPPORTED_INSTRUCTIONS
        and 'directed' in SUPPORTED_INSTRUCTIONS[name]
        and SUPPORTED_INSTRUCTIONS[name]['directed']
    )


def get_current_instruction_name(name: str):
    """Checks if the instruction name has been deprecated and returns the new name if it is;
    otherwise, just returns the name as-is.

    Args:
        name: the name of the instruction

    Returns:
        the current name of the instruction.
    """
    return (
        SUPPORTED_INSTRUCTIONS[name]['renamed_to']
        if name in SUPPORTED_INSTRUCTIONS and 'renamed_to' in SUPPORTED_INSTRUCTIONS[name]
        else name
    )


class Circuit(BaseModel):
    """Quantum circuit to be executed.

    Consists of native quantum operations, each represented by an instance of the :class:`Instruction` class.
    """

    name: str = Field(..., examples=['test circuit'])
    """name of the circuit"""
    instructions: tuple[Instruction, ...] = Field(...)
    """instructions comprising the circuit"""
    metadata: Optional[dict[str, Any]] = Field(None)
    """arbitrary metadata associated with the circuit"""

    def all_qubits(self) -> set[str]:
        """Return the names of all qubits in the circuit."""
        qubits: set[str] = set()
        for instruction in self.instructions:
            qubits.update(instruction.qubits)
        return qubits

    @field_validator('name')
    @classmethod
    def name_validator(cls, value):
        """Check if the circuit name is a non-empty string"""
        name = value
        if len(name) == 0:
            raise ValueError('A circuit should have a non-empty string for a name.')
        return name

    @field_validator('instructions')
    @classmethod
    def instructions_validator(cls, value):
        """Check the container of instructions and each instruction within"""
        instructions = value

        # Check container type
        if not isinstance(instructions, (list, tuple)):
            raise ValueError('Instructions of a circuit should be packed in a tuple')

        # Check if any instructions are present
        if len(value) == 0:
            raise ValueError('Each circuit should have at least one instruction.')

        # Check each instruction explicitly, because automatic validation for Instruction
        # is only called when we create a new instance of Instruction, but not if we modify
        # an existing instance.
        for instruction in instructions:
            if isinstance(instruction, Instruction):
                Instruction.model_validate(instruction.__dict__)
            else:
                raise ValueError('Every instruction in a circuit should be of type <Instruction>')

        return instructions


CircuitBatch = list[Circuit]
"""Type that represents a list of quantum circuits to be executed together in a single batch."""


def validate_circuit(circuit: Circuit) -> None:
    """Validates a submitted quantum circuit using Pydantic tooling. If the
    validation of the circuit fails, an exception is raised.

    Args:
        circuit: a circuit that needs validation

    Raises:
            pydantic.error_wrappers.ValidationError
    """
    Circuit.model_validate(circuit.__dict__)


class SingleQubitMapping(BaseModel):
    """Mapping of a logical qubit name to a physical qubit name."""

    logical_name: str = Field(..., examples=['alice'])
    """logical qubit name"""
    physical_name: str = Field(..., examples=['QB1'])
    """physical qubit name"""


QubitMapping = list[SingleQubitMapping]
"""Type that represents a qubit mapping for a circuit, i.e. a list of single qubit mappings
for all qubits in the circuit."""


def serialize_qubit_mapping(qubit_mapping: dict[str, str]) -> list[SingleQubitMapping]:
    """Serializes a qubit mapping dict into the corresponding IQM data transfer format.

    Args:
        qubit_mapping: mapping from logical to physical qubit names

    Returns:
        data transfer object representing the mapping
    """
    return [SingleQubitMapping(logical_name=k, physical_name=v) for k, v in qubit_mapping.items()]


class HeraldingMode(str, Enum):
    """Heralding mode for circuit execution.

    Heralding is the practice of generating data about the state of qubits prior to execution of a circuit.
    This can be achieved by measuring the qubits immediately before executing each shot for a circuit."""

    NONE = 'none'
    """Do not do any heralding."""
    ZEROS = 'zeros'
    """Perform a heralding measurement, only retain shots with an all-zeros result.

    Note: in this mode, the number of shots returned after execution will be less or equal to the requested amount
    due to the post-selection based on heralding data."""


class QuantumArchitectureSpecification(BaseModel):
    """Quantum architecture specification."""

    name: str = Field(...)
    """Name of the quantum architecture."""
    operations: dict[str, list[list[str]]] = Field(...)
    """Operations supported by this quantum architecture, mapped to the allowed loci."""
    qubits: list[str] = Field(...)
    """List of qubits of this quantum architecture."""
    qubit_connectivity: list[list[str]] = Field(...)
    """Qubit connectivity of this quantum architecture."""

    def __init__(self, **data):
        # Convert a simplified quantum architecture to full quantum architecture
        raw_operations = data.get('operations')
        raw_qubits = data.get('qubits')
        raw_qubit_connectivity = data.get('qubit_connectivity')
        if isinstance(raw_operations, list):
            data['operations'] = {
                get_current_instruction_name(op): raw_qubit_connectivity
                if is_multi_qubit_instruction(get_current_instruction_name(op))
                else [[qb] for qb in raw_qubits]
                for op in raw_operations
            }

        super().__init__(**data)
        self.operations = {get_current_instruction_name(k): v for k, v in self.operations.items()}

    def has_equivalent_operations(self, other: QuantumArchitectureSpecification):
        """Compares the given operation sets defined by the quantum architecture against
        another architecture specification.

        Returns:
             True if the operation and the loci are equivalent.
        """
        return QuantumArchitectureSpecification.compare_operations(self.operations, other.operations)

    @staticmethod
    def compare_operations(ops1: dict[str, list[list[str]]], ops2: dict[str, list[list[str]]]) -> bool:
        """Compares the given operation sets.

        Returns:
             True if the operation and the loci are equivalent.
        """
        if set(ops1.keys()) != set(ops2.keys()):
            return False
        for [op, c1] in ops1.items():
            c2 = ops2[op]
            if is_multi_qubit_instruction(op):
                if not is_directed_instruction(op):
                    c1 = [sorted(qbs) for qbs in c1]
                    c2 = [sorted(qbs) for qbs in c2]
                if sorted(c1) != sorted(c2):
                    return False
            else:
                qs1 = {q for [q] in c1}
                qs2 = {q for [q] in c2}
                if qs1 != qs2:
                    return False
        return True


class QuantumArchitecture(BaseModel):
    """Quantum architecture as returned by server."""

    quantum_architecture: QuantumArchitectureSpecification = Field(...)
    """Details about the quantum architecture."""


class RunRequest(BaseModel):
    """Request for an IQM quantum computer to run a job that executes a batch of quantum circuits.

    Note: all circuits in a batch must measure the same qubits otherwise batch execution fails.
    """

    circuits: CircuitBatch = Field(...)
    """batch of quantum circuit(s) to execute"""
    custom_settings: Optional[dict[str, Any]] = Field(None)
    """Custom settings to override default IQM hardware settings and calibration data.
Note: This field should be always None in normal use."""
    calibration_set_id: Optional[UUID] = Field(None)
    """ID of the calibration set to use, or None to use the latest calibration set"""
    qubit_mapping: Optional[list[SingleQubitMapping]] = Field(None)
    """mapping of logical qubit names to physical qubit names, or None if using physical qubit names"""
    shots: int = Field(..., gt=0)
    """how many times to execute each circuit in the batch, must be greater than zero"""
    max_circuit_duration_over_t2: Optional[float] = Field(None)
    """Circuits are disqualified on the server if they are longer than this ratio
        of the T2 time of the qubits.
        If set to 0.0, no circuits are disqualified. If set to None the server default value is used."""
    heralding_mode: HeraldingMode = Field(HeraldingMode.NONE)
    """which heralding mode to use during the execution of circuits in this request."""


CircuitMeasurementResults = dict[str, list[list[int]]]
"""Measurement results from a single circuit. For each measurement operation in the circuit,
maps the measurement key to the corresponding results. The outer list elements correspond to shots,
and the inner list elements to the qubits measured in the measurement operation."""


CircuitMeasurementResultsBatch = list[CircuitMeasurementResults]
"""Type that represents measurement results for a batch of circuits."""


class Metadata(BaseModel):
    """Metadata describing a circuit execution job."""

    calibration_set_id: Optional[UUID] = Field(None)
    """ID of the calibration set used"""
    request: RunRequest = Field(...)
    """copy of the original RunRequest sent to the server"""
    cocos_version: Optional[str] = Field(None)
    """CoCoS version used to execute the job"""
    timestamps: Optional[dict[str, str]] = Field(None)
    """Timestamps of execution progress"""


class Status(str, Enum):
    """
    Status of a job.
    """

    PENDING_COMPILATION = 'pending compilation'
    PENDING_EXECUTION = 'pending execution'
    READY = 'ready'
    FAILED = 'failed'
    ABORTED = 'aborted'
    PENDING_DELETION = 'pending deletion'
    DELETION_FAILED = 'deletion failed'
    DELETED = 'deleted'


class RunResult(BaseModel):
    """
    Results of the quantum circuit execution job.
    If the job succeeded, :attr:`measurements` contains the output of the batch of circuits,
    consisting of the results of the measurement operations in each circuit.
    It is a list of dictionaries, where each dict maps each measurement key to a 2D array of measurement
    results, represented as a nested list.
    ``RunResult.measurements[circuit_index][key][shot][qubit_index]`` is the result of measuring the
    ``qubit_index``'th qubit in measurement operation ``key`` in the shot ``shot`` in the
    ``circuit_index``'th circuit of the batch.
    :attr:`measurements` is present iff the status is ``'ready'``.
    :attr:`message` carries additional information for the ``'failed'`` status.
    If the status is ``'pending compilation'`` or ``'pending execution'``,
    :attr:`measurements` and :attr:`message` are ``None``.

    The results are non-negative integers representing the computational basis state (for qubits, 0 or 1)
    that was the measurement outcome.

    ----
    """

    status: Status = Field(...)
    """current status of the job, in ``{'pending compilation', 'pending execution', 'ready', 'failed', 'aborted'}``"""
    measurements: Optional[CircuitMeasurementResultsBatch] = Field(None)
    """if the job has finished successfully, the measurement results for the circuit(s)"""
    message: Optional[str] = Field(None)
    """if the job failed, an error message"""
    metadata: Metadata = Field(...)
    """metadata about the job"""
    warnings: Optional[list[str]] = Field(None)
    """list of warning messages"""

    @staticmethod
    def from_dict(inp: dict[str, Union[str, dict]]) -> 'RunResult':
        """Parses the result from a dict.

        Args:
            inp: value to parse, has to map to RunResult

        Returns:
            parsed job result

        """
        input_copy = inp.copy()
        return RunResult(status=Status(input_copy.pop('status')), **input_copy)


class RunStatus(BaseModel):
    """Status of a circuit execution job."""

    status: Status = Field(...)
    """current status of the job, in ``{'pending compilation', 'pending execution', 'ready', 'failed', 'aborted'}``"""
    message: Optional[str] = Field(None)
    """if the job failed, an error message"""
    warnings: Optional[list[str]] = Field(None)
    """list of warning messages"""

    @staticmethod
    def from_dict(inp: dict[str, Union[str, dict]]) -> 'RunStatus':
        """Parses the result from a dict.

        Args:
            inp: value to parse, has to map to RunResult

        Returns:
            parsed job status

        """
        input_copy = inp.copy()
        return RunStatus(status=Status(input_copy.pop('status')), **input_copy)
