"""Tox docs pre-build helper file. Checks out the documentation branch and
copies available documentation versions to the build directory. Then,
rebuilding the existing versions can be skipped by
``sphinx-multiversion-contrib`` using flag ``--skip-if-outputdir-exists``"""

import argparse
import os
import shutil
from subprocess import PIPE, Popen
import tarfile

# Get documentation path parameters from command line arguments

parser = argparse.ArgumentParser()
parser.add_argument('--build_dir', required=True, help='Path to Sphinx documentation build directory')
parser.add_argument('--build_type', required=True, help='Sphinx documentation build type')
args = parser.parse_args()
DOCS_BUILD_DIR = args.build_dir
DOCS_BUILD_TYPE = args.build_type

# Set paths

TEMP_DIR = 'temp'
DOCS_VERSIONS_DIR = 'versions'
DOCS_BUILD_INNER_PATH = os.path.join(DOCS_BUILD_DIR, DOCS_BUILD_TYPE)
TEMP_ARCHIVE_FILE = 'temp_archive.tar'

DOCS_BRANCH = 'remotes/origin/gh-pages'

# Delete stale directories if any

if os.path.exists(TEMP_DIR):
    shutil.rmtree(TEMP_DIR)

if os.path.exists(DOCS_BUILD_DIR):
    shutil.rmtree(DOCS_BUILD_DIR)

# Create new directories

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(DOCS_BUILD_INNER_PATH, exist_ok=True)

# Get available versions of documentation from Git branch as TAR archive

with Popen(
    ['git', 'archive', DOCS_BRANCH, '-o', os.path.join(TEMP_DIR, TEMP_ARCHIVE_FILE)], stdout=PIPE, stderr=PIPE
) as p:
    p.wait()

with tarfile.open(os.path.join(TEMP_DIR, TEMP_ARCHIVE_FILE), 'r') as f:
    f.extractall(path=TEMP_DIR)

# Copy directories of documentation versions to build directory

shutil.move(os.path.join(TEMP_DIR, DOCS_VERSIONS_DIR), DOCS_BUILD_INNER_PATH)

# Delete temp directories

if os.path.exists(TEMP_DIR):
    shutil.rmtree(TEMP_DIR)
