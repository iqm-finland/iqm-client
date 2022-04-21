#!/usr/bin/env python3
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
"""
Script to publish json schema for the circuit execution request which is sent to the IQM backend.
"""
import json
import os
from typing import Any, Dict

from git import Repo

from iqm_client.iqm_client import RunRequest


def _get_git_tag() -> str:
    repo = Repo(os.getcwd())
    tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime)
    return str(tags[-1])

def generate_json_schema() -> Dict[str, Any]:
    """
    Generate json schema dictionary from pydantic model of RunRequest.
    """
    json_schema = RunRequest.schema()
    json_schema['title'] += f' v{_get_git_tag()}'
    return json_schema

def save_json_schema_to_docs() -> None:
    """
    Save json schema in docs folder.
    """
    json_schema_path = os.path.join(os.getcwd(), 'docs', 'run_request_json_schema.json')
    with open(json_schema_path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(generate_json_schema(),indent=2))

if __name__ == '__main__':
    save_json_schema_to_docs()
