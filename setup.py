#!/usr/bin/env python
#
# For developement:
#
#   pip install -e .[dev]
#
# For packaging first install the latest versions of the tooling:
#
#   pip install --upgrade pip setuptools wheel twine
#   pip install -e .[dev]
#

import sys
from setuptools import setup, find_packages
from distutils.util import convert_path


# Fetch version without importing the package
version_globals = {}  # type: ignore
with open(convert_path('redash_reql/version.py')) as fd:
    exec(fd.read(), version_globals)


setup(
    name='redash_reql',
    version=version_globals['__version__'],
    author='Iván Montes Velencoso',
    author_email='drslump@pollinimini.net',
    url='https://github.com/drslump/redash-reql',
    license='LICENSE.txt',
    description='ReDash ReQL query runner.',
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    classifiers=(
        "Development Status :: 2 - Pre-Alpha",
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
        "Programming Language :: Python :: 2.7",
    ),
    keywords='redash sqlite',
    project_urls={  # Optional
        'Bug Reports': 'https://github.com/drslump/redash-reql/issues',
        'Source': 'https://github.com/drslump/redash-reql',
        'Say Thanks!': 'https://twitter/drslump',
    },

    packages=find_packages(exclude=['tests']),

    install_requires=[
        "lark-parser==0.6.4",
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-runner",
        ]
    },

    package_data={},
    data_files=[]
)
