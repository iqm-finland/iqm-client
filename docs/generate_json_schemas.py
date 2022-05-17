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
Script to publish JSON schemas for the Pydantic models used by the HTTP API.
"""
import json
import os
from typing import Any

from iqm_client.iqm_client import BaseModel, RunRequest

try:
    from iqm_client import __version__ as version
except ImportError:
    pass

# schemas to generate
SCHEMAS = {
    'run_request_schema': RunRequest,
}

def generate_json_schema(cls: type[BaseModel], filename: str) -> dict[str, Any]:
    """Generate a JSON schema dictionary from the given Pydantic model.

    Args:
        cls: pydantic model for which the JSON schema should be generated.
        filename: filename of the JSON schema.
    """
    json_schema = cls.schema()

    return {
        # JSON Schema version used
        '$schema': 'https://json-schema.org/draft/2020-12/schema',
        # URI containing the version of the generated schema
        '$id': f'https://iqm-finland.github.io/iqm-client/{filename}',
        **json_schema,
    }

def save_json_schemas_to_docs() -> None:
    """Save the JSON schemas in the docs folder.
    """
    for filename_prefix, cls in SCHEMAS.items():
        filename = f"{filename_prefix}_v{version}.json"
        json_schema_path = os.path.join(os.getcwd(), 'docs', filename)
        with open(json_schema_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(generate_json_schema(cls, filename), indent=2))

if __name__ == '__main__':
    save_json_schemas_to_docs()
