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
import os

from iqm.iqm_client import IQMClient, update_batch_circuit_metadata


def test_iqm_client_initializes_with_project_id(base_url):
    """Test that IQMClient initializes successfully when project ID is available as environment variable."""
    os.environ['PROJECT_ID'] = 'ABC123'
    sample_client = IQMClient(base_url)
    del os.environ['PROJECT_ID']
    assert sample_client._project_id == 'ABC123'


def test_update_batch_circuit_matadata(sample_circuit):
    """Test updating batch circuit metadata."""
    metadata = {'project_id': 'ABC123'}
    circuits = update_batch_circuit_metadata(metadata, [sample_circuit])
    assert circuits[0].metadata['project_id'] == metadata['project_id']
