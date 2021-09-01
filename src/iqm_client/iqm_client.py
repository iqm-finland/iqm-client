# Copyright 2021 IQM client developers
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
Client for connecting to the IQM quantum computer server interface.
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from enum import Enum
from posixpath import join
from typing import Any, Optional, Union
from uuid import UUID

import requests
from pydantic import BaseModel, Field

TIMEOUT_SECONDS = 120
SECONDS_BETWEEN_CALLS = 1


class CircuitExecutionError(RuntimeError):
    """Something went wrong on the server.
    """


class APITimeoutError(CircuitExecutionError):
    """Exception for when executing a task on the server takes too long.
    """


class RunStatus(str, Enum):
    """
    Status of a task.
    """
    PENDING = 'pending'
    READY = 'ready'
    FAILED = 'failed'


class InstructionDTO(BaseModel):
    """An instruction in a quantum circuit.
    """
    name: str = Field(..., description='name of the quantum operation', example='phased_rx')
    'name of the quantum operation'
    qubits: list[str] = Field(
        ...,
        description='names of the logical qubits the operation acts on',
        example=['q1'],
    )
    'names of the logical qubits the operation acts on'
    args: dict[str, Any] = Field(
        ...,
        description='arguments for the operation',
        example={'angle_t': 0.1, 'phase_t': 0.2},
    )
    'arguments for the operation'


class CircuitDTO(BaseModel):
    """Quantum circuit to be executed.
    """
    name: str = Field(..., description='name of the circuit', example='test circuit')
    'name of the circuit'
    args: dict[str, Any] = Field(..., description='arguments for a parameterized circuit', example={})
    'arguments for a parameterized circuit'
    instructions: list[InstructionDTO] = Field(..., description='instructions comprising the circuit')
    'instructions comprising the circuit'


class SingleQubitMappingDTO(BaseModel):
    """Mapping of a logical qubit name to a physical qubit name.
    """
    logical_name: str = Field(..., description='logical name of the qubit', example='q1')
    'logical name of the qubit'
    physical_name: str = Field(..., description='physical name of the qubit', example='qubit_1')
    'physical name of the qubit'


class RunRequestDTO(BaseModel):
    """Request for an IQM quantum computer to execute a quantum circuit.
    """
    circuit: CircuitDTO = Field(..., description='quantum circuit to execute')
    'quantum circuit to execute'
    settings: dict[str, Any] = Field(..., description='EXA settings node containing the calibration data')
    'EXA settings node containing the calibration data'
    qubit_mapping: list[SingleQubitMappingDTO] = Field(
        ...,
        description='mapping of logical qubit names to physical qubit names'
    )
    'mapping of logical qubit names to physical qubit names'
    shots: int = Field(..., description='how many times to sample the circuit')
    'how many times to sample the circuit'


class RunResultDTO(BaseModel):
    """Results of a circuit execution.

    * ``measurements`` is present iff the status is ``'ready'``.
    * ``message`` carries additional information for the ``'failed'`` status.
    * If the status is ``'pending'``, ``measurements`` and ``message`` are ``None``.
    """
    status: RunStatus = Field(..., description='current status of the run, either "pending", "ready" or "failed"')
    'current status of the run, either "pending", "ready" or "failed"'
    measurements: Optional[dict[str, list[list[int]]]] = Field(
        None,
        description='if the run has finished successfully, the measurement values for the circuit'
    )
    'if the run has finished successfully, the measurement values for the circuit'
    message: Optional[str] = Field(None, description='if the run failed, an error message')
    'if the run failed, an error message'

    @staticmethod
    def from_dict(inp: dict[str, Union[str, dict]]) -> RunResultDTO:
        """Parses the result from a dict.

        Args:
            inp: value to parse, has to map to RunResultDTO

        Returns:
            parsed run result

        """
        input_copy = inp.copy()
        return RunResultDTO(status=RunStatus(input_copy.pop('status')), **input_copy)


class IQMClient:
    """Provides access to IQM quantum computers.

    Args:
        url: Endpoint for accessing the server. Has to start with http or https.
        settings: Settings for the quantum computer, in IQM JSON format.
    """
    def __init__(self, url: str, settings: dict[str, Any]):
        self._base_url = url
        self._settings = settings

    def submit_circuit(
            self,
            circuit: CircuitDTO,
            qubit_mapping: list[SingleQubitMappingDTO],
            shots: int = 1
    ) -> UUID:
        """Submits a quantum circuit to be executed on a quantum computer.

        Args:
            circuit: circuit to be executed
            qubit_mapping: mapping of human-readable qubit names in ``circuit`` to physical qubit names
            shots: number of times ``circuit`` is sampled

        Returns:
            ID for the created task. This ID is needed to query the status and the execution results.
        """

        data = RunRequestDTO(
            qubit_mapping=qubit_mapping,
            circuit=circuit,
            settings=self._settings,
            shots=shots
        )

        result = requests.post(join(self._base_url, 'circuit/run'), json=data.dict())
        result.raise_for_status()
        return UUID(json.loads(result.text)['id'])

    def get_run(self, run_id: UUID) -> RunResultDTO:
        """Query the status of the running task.

        Args:
            run_id: id of the taks

        Returns:
            result of the run (can be pending)

        Raises:
            HTTPException: http exceptions
            CircuitExecutionError: IQM server specific exceptions
        """
        result = requests.get(join(self._base_url, 'circuit/run/', str(run_id)))
        result.raise_for_status()
        result = RunResultDTO.from_dict(json.loads(result.text))
        if result.status == RunStatus.FAILED:
            raise CircuitExecutionError(result.message)
        return result

    def wait_for_results(self, run_id: UUID, timeout_secs: float = TIMEOUT_SECONDS) -> RunResultDTO:
        """Poll results until run is ready, failed, or timed out.

        Args:
            run_id: id of the task to wait
            timeout_secs: how long to wait for a response before raising an APITimeoutError

        Returns:
            run result

        Raises:
            APITimeoutError: time exceeded the set timeout
        """
        start_time = datetime.now()
        while (datetime.now() - start_time).total_seconds() < timeout_secs:
            results = self.get_run(run_id)
            if results.status != RunStatus.PENDING:
                return results
            time.sleep(SECONDS_BETWEEN_CALLS)
        raise APITimeoutError(f"The task didn't finish in {timeout_secs} seconds.")
