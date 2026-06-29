#! /bin/sh

pytest --doctest-modules --cov=htmltreediff --cov-report=term-missing --cov-fail-under=100 "$@" && flake8 htmltreediff
