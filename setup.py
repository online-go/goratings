#!/usr/bin/env python

from setuptools import find_packages, setup

setup(
    name="goratings",
    version="0.0.1",
    author="Various",
    author_email="contact@online-go.com",
    url="https://github.com/online-go/goratings",
    description="Official rating and rank calculator used by Online-Go.com.",
    long_description=__doc__,
    packages=find_packages(exclude=("analysis", "analysis.*", "unit_tests", "unit_tests.*")),
    zip_safe=True,
    license="MIT",
)
