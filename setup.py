#!/usr/bin/env python

from setuptools import setup, find_packages

requires = [
    "click>=7.0",
    "click_log>=0.3.2",
    "tqdm>=4.8.4",
]

extra_requires = {
    "sunlite": ["lxml>=3.6.4"]
}

__version__ = None
__author__ = None
__email__ = None
exec(open("pyledctrl/version.py").read())

setup(
    name="pyledctrl",
    author=__author__,
    author_email=__email__,
    version=__version__,
    description="Bytecode compiler and utilities for ledctrl",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requires,
    extras_require=extra_requires,
    entry_points={"console_scripts": ["ledctrl = pyledctrl.app:main"]},
)
