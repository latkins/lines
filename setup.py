#!/usr/bin/env python

import setuptools

if __name__ == "__main__":
    setuptools.setup(
        packages=setuptools.find_packages(include=["lines.*"]),
    )
