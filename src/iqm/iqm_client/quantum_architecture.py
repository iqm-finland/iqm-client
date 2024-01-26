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
This module contains the definition of the quantum architecture specification
classes.

For more information on the topic, refer to the more comprehensive documentation in iqm_client.py.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from iqm.iqm_client.instruction import get_current_instruction_name, is_directed_instruction, is_multi_qubit_instruction


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
        super().__init__(**data)
        self.operations = {get_current_instruction_name(k): v for k, v in self.operations.items()}
        print("OPS", self.operations)

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
