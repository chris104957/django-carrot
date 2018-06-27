#!/usr/bin/env bash
coverage run run_tests.py
coverage html
open ./htmlcov/index.html