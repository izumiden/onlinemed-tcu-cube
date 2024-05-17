# -*- coding: utf-8 -*-
import ast
from glob import glob
import os
from os.path import basename
from os.path import splitext
import re
from setuptools import setup
from setuptools import find_packages

PACKAGE_NAME = 'cube'

def _requires_from_file(filename):
    return open(filename).read().splitlines()


with open(os.path.join(PACKAGE_NAME, '__init__.py')) as f:
    match = re.search(r'__version__\s+=\s+(.*)', f.read())
version = str(ast.literal_eval(match.group(1)))


setup(
    name="OnlineMed Cube",
    version=version,
    license="",
    description="OnlineMed Cube Control Application",
    author="Izumiden",
    # url="GitHubなどURL",
    packages=find_packages(PACKAGE_NAME),
    package_dir={"": PACKAGE_NAME},
    py_modules=[splitext(basename(path))[0] for path in glob('*.py')],
    include_package_data=True,
    zip_safe=False,
    install_requires=_requires_from_file('requirements.txt'),
    setup_requires=["pytest-runner"],
    tests_require=["pytest", "pytest-cov"]
)
