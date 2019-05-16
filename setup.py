#! /usr/bin/env python
# coding: utf-8

import codecs
import os

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

long_description = codecs.open("README.rst", "r", "utf-8").read()


def strip_comments(l):
    return l.split('#', 1)[0].strip()


def get_requirements(path):
    for line in open(os.path.join(os.getcwd(), path)).readlines():
        line = strip_comments(line)
        if line:
            yield line


setup(
    name="html-tree-diff",
    version="0.1.4",
    description="Structure-aware diff for html and xml documents",
    author="Christian Oudard",
    author_email="christian.oudard@gmail.com",
    url="http://github.com/christian-oudard/htmltreediff/",
    platforms=["any"],
    license="BSD",
    packages=find_packages(),
    scripts=[],
    zip_safe=False,
    install_requires=list(get_requirements('requirements/default.txt')),
    tests_require=list(get_requirements('requirements/testing.txt')),
    cmdclass={},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Topic :: Text Processing :: Markup :: HTML",
        "Topic :: Text Processing :: Markup :: XML",
    ],
    long_description=long_description,
)
