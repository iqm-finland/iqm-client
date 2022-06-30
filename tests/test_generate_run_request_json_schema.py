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
from __future__ import annotations

from copy import deepcopy

import jsonschema
import pytest
from jsonschema import Draft202012Validator, ValidationError
from jsonschema.validators import extend

from docs.generate_json_schemas import generate_json_schema
from iqm_client import RunRequest


@pytest.fixture
def sample_valid_run_request(sample_circuit):
    """
    Returns valid example run request.
    """
    return RunRequest(
        circuit=sample_circuit,
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

@pytest.fixture
def run_request_schema() -> dict:
    """JSON schema for RunRequests.
    """
    return generate_json_schema(RunRequest, filename='')

@pytest.fixture
def json_validator(run_request_schema) -> jsonschema.protocols.Validator:
    """Validator for JSON-serialized RunRequests.
    """
    # allow the representation of JSON arrays as either tuples or lists
    type_checker = Draft202012Validator.TYPE_CHECKER.redefine(
        'array',
        lambda checker, instance: isinstance(instance, (tuple, list))
    )
    validator_class = extend(Draft202012Validator, type_checker=type_checker)
    return validator_class(schema=run_request_schema)


def test_jsonschema_validates_run_requests(sample_valid_run_request, json_validator):
    """Tests that the generated json schema validates valid run requests.
    """
    json_validator.validate(instance=sample_valid_run_request)


def test_jsonschema_throws_validation_errors(sample_invalid_run_request, json_validator):
    """Tests that the generated json schema rejects invalid run requests.
    """
    with pytest.raises(ValidationError):
        json_validator.validate(instance=sample_invalid_run_request)
