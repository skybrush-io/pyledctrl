#!/usr/bin/env python

import pyledctrl
from setuptools import setup

setup(
    name="pyledctrl",
    version=pyledctrl.__version__,
    description="Bytecode compiler and utilities for ledctrl",
    author=pyledctrl.__author__,
    author_email=pyledctrl.__email__,
    packages=["pyledctrl"],
    scripts=["bin/ledctrl"],
    requires=["serial", "Baker (>=1.0)"]
)
