#!/bin/sh
curl -O https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py
curl -O https://raw.github.com/pypa/pip/master/contrib/get-pip.py
./casa-python ez_setup.py
./casa-python get-pip.py
