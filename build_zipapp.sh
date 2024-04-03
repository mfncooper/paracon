#!/bin/bash

VER=`python3 version.py paracon/paracon.py`
APPDIR=_zipapp

# Ensure clean target build directory
rm -rf $APPDIR
mkdir -p $APPDIR

# Application sources
cp -p paracon/*.py $APPDIR/

# Default config
mkdir -p $APPDIR/paracon_config
cp -p paracon/*.def $APPDIR/paracon_config/
# Create empty file to make it a module
touch $APPDIR/paracon_config/__init__.py

# Install dependencies
python -m pip install -r requirements-zipapp.txt --target $APPDIR/

# Build the zipapp and make it executable
python -m zipapp $APPDIR/ -p '/usr/bin/env python3' -o paracon_${VER}.pyz -m "paracon:run"
chmod a+x paracon_${VER}.pyz
