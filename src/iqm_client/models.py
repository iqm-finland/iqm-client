# Copyright 2023 IQM client developers
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
Pydantic models and types for iqm-client files.
"""

from enum import Enum
from typing import Any, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, StrictStr, validate_model, validator

SUPPORTED_INSTRUCTIONS = {
    'barrier': {
        'arity': -1,
        'args': {},
    },
    'cz': {
        'arity': 2,
        'args': {},
    },
    'measurement': {
        'arity': -1,
        'args': {
            'key': (str,),
        },
    },
    'phased_rx': {
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
}


class Status(str, Enum):
    """
    Status of a job.
    """

    PENDING_COMPILATION = 'pending compilation'
    PENDING_EXECUTION = 'pending execution'
    READY = 'ready'
    FAILED = 'failed'


class Instruction(BaseModel):
    """An instruction in a quantum circuit."""

    name: str = Field(..., example='measurement')
    """name of the quantum operation"""
    implementation: Optional[StrictStr] = Field(None)
    """name of the implementation, for experimental use only"""
    qubits: tuple[StrictStr, ...] = Field(..., example=('alice',))
    """names of the logical qubits the operation acts on"""
    args: dict[str, Any] = Field(..., example={'key': 'm'})
    """arguments for the operation"""

    @validator('name')
    def name_validator(cls, value):
        """Check if the name of instruction is set to one of the supported quantum operations"""
        name = value
        if name not in SUPPORTED_INSTRUCTIONS:
            raise ValueError(
                f'Unknown instruction "{name}". '
                f'Supported instructions are \"{", ".join(SUPPORTED_INSTRUCTIONS.keys())}\"'
            )
        return name

    @validator('implementation')
    def implementation_validator(cls, value):
        """Check if the implementation of the instruction is set to a non-empty string"""
        implementation = value
        if isinstance(implementation, str):
            if not implementation:
                raise ValueError('Implementation of the instruction should be set to a non-empty string')
        return implementation

    @validator('qubits')
    def qubits_validator(cls, value, values):
        """Check if the instruction has the correct number of qubits according to the instruction's type"""
        qubits = value
        name = values.get('name')
        if not name:
            raise ValueError('Could not validate qubits because the name of the instruction did not pass validation')
        arity = SUPPORTED_INSTRUCTIONS[name]['arity']
        if (0 <= arity) and (arity != len(qubits)):
            raise ValueError(
                f'The "{name}" instruction acts on {arity} qubit(s), but {len(qubits)} were given: {qubits}'
            )
        return qubits

    @validator('args')
    def args_validator(cls, value, values):
        """Check argument names and types for a given instruction"""
        args = value
        name = values.get('name')

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


class Circuit(BaseModel):
    """Quantum circuit to be executed."""

    name: str = Field(..., example='test circuit')
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

    @validator('name')
    def name_validator(cls, value):
        """Check if the circuit name is a non-empty string"""
        name = value
        if len(name) == 0:
            raise ValueError('A circuit should have a non-empty string for a name.')
        return name

    @validator('instructions', pre=True)
    def instructions_validator(cls, value):
        """Check the container of instructions and each instruction within"""
        instructions = value

        # Check container type
        if not isinstance(instructions, (list, tuple)):
            raise ValueError('Instructions of a circuit should be packed in a tuple')

        # Check if any instructions are present
        if len(value) == 0:
            raise ValueError('Each circuit should have at least one instruction.')

        # TODO: The following check is needed because Pydantic coerces data,
        #  e.g. it would try to convert <list> into <Instruction> instead of
        #  trowing a validation error. This check will become obsolete with
        #  Pydantic v2, when strict mode for type checking is implemented and
        #  can be enabled (throwing an error instead of coercing data)

        # Check each instruction
        for instruction in instructions:
            if isinstance(instruction, Instruction):
                *_, validation_error = validate_model(Instruction, instruction.__dict__)
                if validation_error:
                    raise validation_error
            elif isinstance(instruction, dict):
                *_, validation_error = validate_model(Instruction, instruction)
                if validation_error:
                    raise validation_error
            else:
                raise ValueError('Every instruction in a circuit should be of type <Instruction>')

        return instructions

    @validator('metadata', pre=True)
    def metadata_validator(cls, value):
        """Check metadata dictionary and its keys"""
        metadata = value

        if not (isinstance(metadata, dict) or metadata is None):
            raise ValueError('Circuit metadata should be a dictionary')

        # All keys should be strings
        if metadata:
            if not all((isinstance(key, str) for key in metadata.keys())):
                raise ValueError('Metadata dictionary should use strings for all root-level keys')

        return metadata


CircuitBatch = list[Circuit]
"""Type that represents a list of quantum circuits to be executed together in a single batch."""


class SingleQubitMapping(BaseModel):
    """Mapping of a logical qubit name to a physical qubit name."""

    logical_name: str = Field(..., example='alice')
    """logical qubit name"""
    physical_name: str = Field(..., example='QB1')
    """physical qubit name"""


QubitMapping = list[SingleQubitMapping]
"""Type that represents a qubit mapping for a circuit, i.e. a list of single qubit mappings
for all qubits in the circuit."""


class RunRequest(BaseModel):
    """Request for an IQM quantum computer to run a job that executes a batch of quantum circuits.

    Note: all circuits in a batch must measure the same qubits otherwise batch execution fails.
    """

    circuits: CircuitBatch = Field(...)
    """batch of quantum circuit(s) to execute"""
    custom_settings: dict[str, Any] = Field(None)
    """Custom settings to override default IQM hardware settings and calibration data.
Note: This field should be always None in normal use."""
    calibration_set_id: Optional[UUID] = Field(None)
    """ID of the calibration set to use, or None to use the latest calibration set"""
    qubit_mapping: Optional[list[SingleQubitMapping]] = Field(None)
    """mapping of logical qubit names to physical qubit names, or None if using physical qubit names"""
    shots: int = Field(...)
    """how many times to execute each circuit in the batch"""


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


class RunResult(BaseModel):
    """Results of a circuit execution job.

    * ``measurements`` is present iff the status is ``'ready'``.
    * ``message`` carries additional information for the ``'failed'`` status.
    * If the status is ``'pending'``, ``measurements`` and ``message`` are ``None``.
    """

    status: Status = Field(...)
    """current status of the job, in ``{'pending', 'ready', 'failed'}``"""
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
    """current status of the job, in ``{'pending', 'ready', 'failed'}``"""
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


class QuantumArchitectureSpecification(BaseModel):
    """Quantum architecture specification."""

    name: str = Field(...)
    """name of the quantum architecture"""
    operations: list[str] = Field(...)
    """list of operations supported by this quantum architecture"""
    qubits: list[str] = Field(...)
    """list of qubits of this quantum architecture"""
    qubit_connectivity: list[list[str]] = Field(...)
    """qubit connectivity of this quantum architecture"""


class QuantumArchitecture(BaseModel):
    """Quantum architecture as returned by Cortex."""

    quantum_architecture: QuantumArchitectureSpecification = Field(...)
    """details about the quantum architecture"""


class GrantType(str, Enum):
    """
    Type of token request.
    """

    PASSWORD = 'password'
    REFRESH = 'refresh_token'


class AuthRequest(BaseModel):
    """Request sent to authentication server for access token and refresh token, or for terminating the session.

    * Token request with grant type ``'password'`` starts a new session in the authentication server.
      It uses fields ``client_id``, ``grant_type``, ``username`` and ``password``.
    * Token request with grant type ``'refresh_token'`` is used for maintaining an existing session.
      It uses field ``client_id``, ``grant_type``, ``refresh_token``.
    * Logout request uses only fields ``client_id`` and ``refresh_token``.

    """

    client_id: str = Field(...)
    """name of the client for all request types"""
    grant_type: Optional[GrantType] = Field(None)
    """type of token request, in ``{'password', 'refresh_token'}``"""
    username: Optional[str] = Field(None)
    """username for grant type ``'password'``"""
    password: Optional[str] = Field(None)
    """password for grant type ``'password'``"""
    refresh_token: Optional[str] = Field(None)
    """refresh token for grant type ``'refresh_token'`` and logout request"""


class Credentials(BaseModel):
    """Credentials and tokens for maintaining a session with the authentication server.

    * Fields ``auth_server_url``, ``username`` and ``password`` are provided by the user.
    * Fields ``access_token`` and ``refresh_token`` are loaded from the authentication server and
      refreshed periodically.
    """

    auth_server_url: str = Field(...)
    """Base URL of the authentication server"""
    username: str = Field(...)
    """username for logging in to the server"""
    password: str = Field(...)
    """password for logging in to the server"""
    access_token: Optional[str] = Field(None)
    """current access token of the session"""
    refresh_token: Optional[str] = Field(None)
    """current refresh token of the session"""


class ExternalToken(BaseModel):
    """Externally managed token for maintaining a session with the authentication server.

    * Fields ``auth_server_url`` and ``access_token`` are loaded from an
      external resource, e.g. file generated by Cortex CLI's token manager.
    """

    auth_server_url: str = Field(...)
    """Base URL of the authentication server"""
    access_token: str = Field(None)
    """current access token of the session"""
