# Copyright 2022 IQM client developers
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
"""Tests to check if the generated json schema validates run requests.
"""
# pylint: disable=redefined-outer-name
from copy import deepcopy

import pytest
from jsonschema import ValidationError, validate

from docs.generate_json_schemas import generate_json_schema
from iqm_client.iqm_client import RunRequest


@pytest.fixture
def sample_valid_run_request(sample_circuit):
    """
    Returns valid example run request.
    """
    return RunRequest(
        circuits=[sample_circuit],
        settings={},
        shots=1000,
        qubit_mapping=[{'logical_name': 'q1', 'physical_name': 'qubit_1'}]
    ).dict()


@pytest.fixture
def sample_invalid_run_request(sample_valid_run_request):
    """
    Returns invalid example run request.
    """
    invalid_run_request = deepcopy(sample_valid_run_request)
    invalid_run_request['shots'] = 'not_a_number'
    return invalid_run_request


def test_jsonschema_validates_run_requests(sample_valid_run_request):
    """
    Tests that the generated json schema validates valid run requests.
    """
    json_schema = generate_json_schema(RunRequest, '')
    validate(schema=json_schema, instance=sample_valid_run_request)


def test_jsonschema_throws_validation_errors(sample_invalid_run_request):
    """
    Tests that the generated json schema rejects invalid run requests.
    """
    json_schema = generate_json_schema(RunRequest, '')
    with pytest.raises(ValidationError):
        validate(schema=json_schema, instance=sample_invalid_run_request)
