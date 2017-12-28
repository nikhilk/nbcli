#!/bin/sh

mkdir -p build
python setup.py sdist --dist-dir build

rm -rf build/notebook_cli.egg-info
mv notebook_cli.egg-info build

