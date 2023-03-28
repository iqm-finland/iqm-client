"""Tox docs post-build helper file. It iterates through all HTML files and
updates sections that contain information about available documentation
versions. The script is needed in case we have a new documentation version,
and we want to avoid rebuilding the old versions from scratch.

NB: The script is designed and tested to work with "sphinx_book_theme" v0.3.3"""

import argparse
import os

from bs4 import BeautifulSoup
from packaging.version import parse as version_parser

parser = argparse.ArgumentParser()
parser.add_argument('--build_dir', required=True, help='Path to Sphinx documentation build directory')
parser.add_argument('--build_type', required=True, help='Sphinx documentation build type')
args = parser.parse_args()
DOCS_BUILD_DIR = args.build_dir
DOCS_BUILD_TYPE = args.build_type

VERSIONS_DIR_PATH = os.path.join(DOCS_BUILD_DIR, DOCS_BUILD_TYPE, 'versions')


def get_versions(base_path: str) -> list[str]:
    """Given a path to a directory with ``sphinx-multiversion`` documentation
    builds, extract documentation version numbers from sub-directory names
    and return them sorted in descending order"""
    versions = os.listdir(base_path)
    versions.sort(key=version_parser, reverse=True)
    return versions


def get_html_file_paths(base_path: str) -> list[str]:
    """Search given directory recursively and return a list of HTML file
    paths"""
    paths = []
    for dirpath, _, filenames in os.walk(base_path):
        for filename in filenames:
            if os.path.splitext(filename)[1].lower() in ['.html']:
                paths.append(os.path.join(dirpath, filename))

    return paths


def get_path_to_parent_dir(filepath: str, processed_version: str) -> str:
    """Get path to the parent dir of a file, determined by documentation
    version. The path is obtained by calculating the nesting level of
    a file in the inner folder structure of a documentation release"""
    dirpath = os.path.split(filepath)[0]
    inner_dirpath = dirpath.split(processed_version)[1]
    inner_dirs = inner_dirpath.split(os.sep)
    inner_nesting_levels = sum(1 for i in inner_dirs if i) + 1
    return (os.path.pardir + os.path.sep) * inner_nesting_levels


def generate_version_list_markup(processed_version: str, versions: list[str], parent_path: str) -> str:
    """Generate HTML markup for UL element with links to all versions of
    documentation as LI elements"""

    UL_TEMPLATE = '<ul class="version_list">{}</ul>'
    DEV_VERSION_LI_TEMPLATE = '<li class="version_item"><a href="{parent_path}../index.html">dev</a></li>'
    PROCESSED_VERSION_LI_TEMPLATE = '<li class="version_item current_version">{version}</li>'
    OTHER_VERSION_LI_TEMPLATE = (
        '<li class="version_item"><a href="{parent_path}{version}/index.html">{version}</a></li>'
    )

    li_markup = []
    li_markup.append(DEV_VERSION_LI_TEMPLATE.format(parent_path=parent_path))

    for ver in versions:
        if ver == processed_version:
            li_markup.append(PROCESSED_VERSION_LI_TEMPLATE.format(version=ver))
        else:
            li_markup.append(OTHER_VERSION_LI_TEMPLATE.format(parent_path=parent_path, version=ver))

    ul_markup = UL_TEMPLATE.format('\n'.join(li_markup))
    return ul_markup


def generate_version_notice_markup(latest_ver: str, parent_path: str) -> tuple[str, str]:
    """Generate HTML markup with styling for version notice element for a given
    version"""
    STYLE_TEMPLATE = '''
    <style type="text/css">
      .version_notice {
        background-color: #ffc107;
        padding: 0.5em 0.75em;
        margin-bottom: 1em;
      }
    </style>
    '''

    VERSION_NOTICE_DIV_TEMPLATE = '''
    <div class="version_notice">
        <strong>
    
            You're reading an old version of this documentation.
            If you want up-to-date information, please have a look at <a href="{parent_path}{version}/index.html">{version}</a>.
    
        </strong>
    </div>
    '''

    style_markup = STYLE_TEMPLATE
    div_markup = VERSION_NOTICE_DIV_TEMPLATE.format(parent_path=parent_path, version=latest_ver)
    return style_markup, div_markup


all_versions = get_versions(VERSIONS_DIR_PATH)
latest_version = all_versions[0]

for version in all_versions:
    html_file_paths = get_html_file_paths(os.path.join(VERSIONS_DIR_PATH, version))

    for html_file_path in html_file_paths:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_dom = BeautifulSoup(f, 'html.parser')

        path_to_parent = get_path_to_parent_dir(html_file_path, version)

        # Update doc version list
        outdated_version_list_element = html_dom.find('ul', class_='version_list')
        if outdated_version_list_element:
            updated_version_list_markup = generate_version_list_markup(version, all_versions, path_to_parent)
            updated_version_list_element = BeautifulSoup(updated_version_list_markup, 'html.parser').ul
            outdated_version_list_element.replace_with(updated_version_list_element)

        # Update version notice
        updated_notice_style_markup, updated_version_notice_markup = generate_version_notice_markup(latest_version,
                                                                                                    path_to_parent)
        updated_notice_style_element = BeautifulSoup(updated_notice_style_markup, 'html.parser').style
        updated_version_notice_element = BeautifulSoup(updated_version_notice_markup, 'html.parser').div
        if version != latest_version:
            outdated_version_notice_element = html_dom.find('div', class_='version_notice')
            if outdated_version_notice_element:
                outdated_version_notice_element.replace_with(updated_version_notice_element)
            else:
                section = html_dom.find('main').find('section')
                if section:
                    section.insert_before(updated_notice_style_element)
                    section.insert_before(updated_version_notice_element)

        with open(html_file_path, 'w', encoding='utf-8') as f:
            # Do not prettify HTML markup with BeautifulSoup as it will change
            # the appearance (spacing and layout) of rendered page slightly
            f.write(str(html_dom))
