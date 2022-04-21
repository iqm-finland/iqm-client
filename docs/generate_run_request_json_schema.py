#!/usr/bin/env python3
import json
from iqm_client.iqm_client import RunRequest
from git import Repo
import os

def get_git_tag():
    repo = Repo(os.getcwd())
    tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime)
    return str(tags[-1])

def generate_json_schema():
    json_schema = RunRequest.schema()
    json_schema['title'] += f" v{get_git_tag()}"
    json_schema_path = os.path.join(os.getcwd(), 'docs', 'run_request_json_schema.json')
    with open(json_schema_path, 'w') as f:
        f.write(json.dumps(json_schema,indent=2))

if __name__ == "__main__":
    generate_json_schema()
