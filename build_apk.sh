#!/bin/bash
python3 -m venv venv
source ./venv/bin/activate
pip install -r requirements_build.txt
buildozer android debug
