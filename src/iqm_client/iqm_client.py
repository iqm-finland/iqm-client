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
r"""
Client for connecting to the IQM quantum computer server interface.

The :class:`Circuit` class represents quantum circuits to be executed, consisting of a list of
native quantum operations, each represented by an instance of the :class:`Instruction` class.
Different Instruction types are distinguished by their ``name``.
Each Instruction type acts on a number of ``qubits``, and expects certain ``args``.


Instructions
============

We currently support three native instruction types:

================ =========== ====================================== ===========
name             # of qubits args                                   description
================ =========== ====================================== ===========
measurement      >= 1        ``key: str``                           Measurement in the Z basis.
phased_rx        1           ``angle_t: float``, ``phase_t: float`` Phased x-rotation gate.
cz               2                                                  Controlled-Z gate.
================ =========== ====================================== ===========

Measurement
-----------

Measurement in the computational (Z) basis. The measurement results are the output of the circuit.
Takes one string argument, ``key``, denoting the measurement key the results are labeled with.
All the measurement keys in a circuit must be unique.
Each qubit may only be measured once.
The measurement must be the last operation on each qubit, i.e. it cannot be followed by gates.

Example: ``Instruction(name='measurement', qubits=['alice', 'bob', 'charlie'], args={'key': 'm1'})``


Phased Rx
---------

Phased x-rotation gate, i.e. an x-rotation conjugated by a z-rotation.
Takes two arguments, the rotation angle ``angle_t`` and the phase angle ``phase_t``,
both measured in units of full turns (:math:`2\pi` radians).
The gate is represented in the standard computational basis by the matrix

.. math::
    R(\theta, \phi) = \exp(-i (X \cos (2 \pi \; \phi) + Y \sin (2 \pi \; \phi)) \: \pi \; \theta)
    = R_z(\phi) R_x(\theta) R_z^\dagger(\phi),

where :math:`\theta` = ``angle_t``, :math:`\phi` = ``phase_t``,
and :math:`X` and :math:`Y` are Pauli matrices.

Example: ``Instruction(name='phased_rx', qubits=['bob'], args={'angle_t': 0.7, 'phase_t': 0.25})``


CZ
--

Controlled-Z gate. Represented in the standard computational basis by the matrix

.. math:: \text{CZ} = \text{diag}(1, 1, 1, -1).

Symmetric wrt. the qubits it's acting on. Takes no arguments.

Example: ``Instruction(name='cz', qubits=['alice', 'bob'], args={})``


Circuit output
==============

The :class:`RunResult` class represents the results of a quantum circuit execution.
If the run succeeded, ``RunResult.measurements`` contains the output of the circuit, consisting
of the results of the measurement operations in the circuit.
It is a dictionary that maps each measurement key to a 2D array of measurement results, represented as a nested list.
``RunResult.measurements[key][shot][index]`` is the result of measuring the ``index`` th qubit in measurement
operation ``key`` in the shot ``shot``. The results are nonnegative integers representing the computational
basis state (for qubits, 0 or 1) that was the measurement outcome.

----
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


class Instruction(BaseModel):
    """An instruction in a quantum circuit.
    """
    name: str = Field(..., description='name of the quantum operation', example='measurement')
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
        example={'key': 'm'},
    )
    'arguments for the operation'


class Circuit(BaseModel):
    """Quantum circuit to be executed.
    """
    name: str = Field(..., description='name of the circuit', example='test circuit')
    'name of the circuit'
    instructions: list[Instruction] = Field(..., description='instructions comprising the circuit')
    'instructions comprising the circuit'


class SingleQubitMapping(BaseModel):
    """Mapping of a logical qubit name to a physical qubit name.
    """
    logical_name: str = Field(..., description='logical name of the qubit', example='q1')
    'logical name of the qubit'
    physical_name: str = Field(..., description='physical name of the qubit', example='qubit_1')
    'physical name of the qubit'


class RunRequest(BaseModel):
    """Request for an IQM quantum computer to execute a quantum circuit.
    """
    circuit: Circuit = Field(..., description='quantum circuit to execute')
    'quantum circuit to execute'
    settings: dict[str, Any] = Field(..., description='EXA settings node containing the calibration data')
    'EXA settings node containing the calibration data'
    qubit_mapping: list[SingleQubitMapping] = Field(
        ...,
        description='mapping of logical qubit names to physical qubit names'
    )
    'mapping of logical qubit names to physical qubit names'
    shots: int = Field(..., description='how many times to execute the circuit')
    'how many times to execute the circuit'


class RunResult(BaseModel):
    """Results of a circuit execution.

    * ``measurements`` is present iff the status is ``'ready'``.
    * ``message`` carries additional information for the ``'failed'`` status.
    * If the status is ``'pending'``, ``measurements`` and ``message`` are ``None``.
    """
    status: RunStatus = Field(..., description='current status of the run, either "pending", "ready" or "failed"')
    'current status of the run, either "pending", "ready" or "failed"'
    measurements: Optional[dict[str, list[list[int]]]] = Field(
        None,
        description='if the run has finished successfully, the measurement results for the circuit'
    )
    'if the run has finished successfully, the measurement results for the circuit'
    message: Optional[str] = Field(None, description='if the run failed, an error message')
    'if the run failed, an error message'

    @staticmethod
    def from_dict(inp: dict[str, Union[str, dict]]) -> RunResult:
        """Parses the result from a dict.

        Args:
            inp: value to parse, has to map to RunResult

        Returns:
            parsed run result

        """
        input_copy = inp.copy()
        return RunResult(status=RunStatus(input_copy.pop('status')), **input_copy)


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
            circuit: Circuit,
            qubit_mapping: list[SingleQubitMapping],
            shots: int = 1
    ) -> UUID:
        """Submits a quantum circuit to be executed on a quantum computer.

        Args:
            circuit: circuit to be executed
            qubit_mapping: mapping of human-readable qubit names in ``circuit`` to physical qubit names
            shots: number of times ``circuit`` is executed

        Returns:
            ID for the created task. This ID is needed to query the status and the execution results.
        """

        data = RunRequest(
            qubit_mapping=qubit_mapping,
            circuit=circuit,
            settings=self._settings,
            shots=shots
        )

        result = requests.post(join(self._base_url, 'circuit/run'), json=data.dict())
        result.raise_for_status()
        return UUID(json.loads(result.text)['id'])

    def get_run(self, run_id: UUID) -> RunResult:
        """Query the status of the running task.

        Args:
            run_id: id of the task

        Returns:
            result of the run (can be pending)

        Raises:
            HTTPException: http exceptions
            CircuitExecutionError: IQM server specific exceptions
        """
        result = requests.get(join(self._base_url, 'circuit/run/', str(run_id)))
        result.raise_for_status()
        result = RunResult.from_dict(json.loads(result.text))
        if result.status == RunStatus.FAILED:
            raise CircuitExecutionError(result.message)
        return result

    def wait_for_results(self, run_id: UUID, timeout_secs: float = TIMEOUT_SECONDS) -> RunResult:
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
