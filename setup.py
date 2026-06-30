#! /usr/bin/env python

import codecs
import os

from setuptools import setup, find_packages

long_description = codecs.open("README.md", "r", "utf-8").read()


def strip_comments(line):
    return line.split('#', 1)[0].strip()


def get_requirements(path):
    for line in open(os.path.join(os.getcwd(), path)).readlines():
        line = strip_comments(line)
        if line:
            yield line


setup(
    name="html-tree-diff",
    version="0.3.1",
    description="Structure-aware diff for html and xml documents",
    author="Christian Oudard",
    author_email="christian.oudard@gmail.com",
    url="http://github.com/PolicyStat/htmltreediff/",
    platforms=["any"],
    license="BSD",
    packages=find_packages(),
    scripts=[],
    zip_safe=False,
    install_requires=list(get_requirements('requirements/default.txt')),
    python_requires=">=3.8",
    tests_require=list(get_requirements('requirements/testing.txt')),
    cmdclass={},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Text Processing :: Markup :: HTML",
        "Topic :: Text Processing :: Markup :: XML",
    ],
    long_description=long_description,
)
