# Copyright 2021-2023 IQM client developers
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
"""Tests for changes to the IQM client in the context of the FiQCI project.
"""
# pylint: disable=too-many-arguments
import os

from mockito import expect, unstub, verifyNoUnwantedInteractions, when
import requests

from iqm.iqm_client import IQMClient, update_batch_circuit_metadata
from tests.conftest import post_jobs_args


def test_iqm_client_initializes_with_project_id(base_url):
    """Test that IQMClient initializes successfully when project ID is available as environment variable."""
    os.environ['PROJECT_ID'] = 'ABC123'
    sample_client = IQMClient(base_url)
    del os.environ['PROJECT_ID']
    assert sample_client._project_id == 'ABC123'


def test_iqm_client_initializes_with_project_id_and_job_id(base_url):
    """Test that IQMClient initializes successfully when project/job ID is available as environment variable."""
    os.environ['PROJECT_ID'] = 'ABC123'
    os.environ['SLURM_JOB_ID'] = 'DEF456'
    sample_client = IQMClient(base_url)
    del os.environ['PROJECT_ID']
    del os.environ['SLURM_JOB_ID']
    assert sample_client._project_id == 'ABC123'
    assert sample_client._slurm_job_id == 'DEF456'


def test_update_batch_circuit_metadata(sample_circuit):
    """Test updating batch circuit metadata."""
    metadata = {'project_id': 'ABC123'}
    circuits = update_batch_circuit_metadata(metadata, [sample_circuit])
    assert circuits[0].metadata['project_id'] == metadata['project_id']


def test_submit_circuits_attaches_slurm_job_id(
    sample_client,
    jobs_url,
    minimal_run_request,
    submit_success,
    quantum_architecture_url,
    quantum_architecture_success,
    base_url,
):
    """
    Test submitting run request without heralding
    """
    # Initialize mock client with exposed job id
    os.environ['SLURM_JOB_ID'] = 'ABC123'
    sample_client = IQMClient(base_url)
    del os.environ['SLURM_JOB_ID']

    # Add job_id to the metadata of the first circuit
    minimal_run_request_serialized = post_jobs_args(minimal_run_request)

    minimal_run_request_serialized['json']['circuits'][0]['metadata']['slurm_job_id'] = 'ABC123'

    # Set up mock responses
    expect(requests, times=1).post(jobs_url, **minimal_run_request_serialized).thenReturn(submit_success)
    when(requests).get(quantum_architecture_url, ...).thenReturn(quantum_architecture_success)

    # Test .submit_circuits()
    sample_client.submit_circuits(circuits=minimal_run_request.circuits, shots=minimal_run_request.shots)

    # Verify no unwanted interactions
    verifyNoUnwantedInteractions()
    unstub()
