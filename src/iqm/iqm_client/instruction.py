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
r"""
This module contains the definition of the Instruction class and defines
the supported instructions.

For more information on the topic, refer to the more comprehensive documentation in iqm_client.py.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field, StrictStr, field_validator
from pydantic_core.core_schema import ValidationInfo

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
    },
    'measurement': {  # deprecated
        'arity': -1,
        'args': {
            'key': (str,),
        },
        'renamed_to': 'measure',
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
    """An instruction in a quantum circuit."""

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
