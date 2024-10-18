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
"""Tests for the IQM client models."""
import pytest

from iqm.iqm_client.models import CircuitBatch, HeraldingMode, JobParameters, Metadata, RunRequest


@pytest.fixture
def shots():
    return 1024


@pytest.fixture
def circuits_batch():
    return CircuitBatch()


@pytest.fixture
def heralding_mode():
    return HeraldingMode.ZEROS


@pytest.mark.parametrize(
    "metadata_factory",
    [
        # V1 and RESONANCE_V1
        lambda shots, circuits_batch, heralding_mode: Metadata(
            request=RunRequest(circuits=circuits_batch, shots=shots, heralding_mode=heralding_mode)
        ),
        # V2
        lambda shots, circuits_batch, heralding_mode: Metadata(
            parameters=JobParameters(shots=shots, heralding_mode=heralding_mode), circuits_batch=circuits_batch
        ),
    ],
)
def test_metadata(metadata_factory, shots, circuits_batch, heralding_mode):
    """Tests different modes of Metadata class initialization."""
    metadata = metadata_factory(shots, circuits_batch, heralding_mode)
    assert metadata.shots == shots
    assert metadata.circuits == circuits_batch
    assert metadata.heralding_mode == heralding_mode
