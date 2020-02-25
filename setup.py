"""A setuptools based setup module for pointsToRfile"""
### !!!PLEASE USE PIP LOCALLY!!!

#!/usr/bin/env python
# -*- coding: utf-8 -*-

from codecs import open
from os import path
from setuptools import setup, find_packages

import versioneer

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as readme_file:
    readme = readme_file.read()

with open(path.join(here, 'HISTORY.rst'), encoding='utf-8') as history_file:
    history = history_file.read().replace('.. :changelog:', '')

requirements = [
    # TODO: put package requirements here
    'click',
]

test_requirements = [
    # TODO: put package test requirements here
]

setup(
    name='pointsToRfile',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="Provides methods for taking point data, inserting it into the grid hdf5 data format, interpolating on this and saving the results as an rFile",
    long_description=readme + '\n\n' + history,
    author="Eric Eckert",
    author_email='contact through github',
    url='https://github.com/firstkingofrome/pointsToRfile',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    entry_points={
        'console_scripts':[
            'pointsToRfile=points2Rfile.cli:cli',
            ],
        },
    include_package_data=True,
    install_requires=requirements,
    license="MIT",
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        "Programming Language :: Python :: 3.6.4",
    ],
    test_suite='tests',
    tests_require=test_requirements,
)
