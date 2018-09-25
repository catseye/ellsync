#!/bin/sh

PYTHONPATH=src python2 src/ellsync/tests.py || exit 1
PYTHONPATH=src python3 src/ellsync/tests.py || exit 1
