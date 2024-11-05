#!/bin/bash

VER=`python3 version.py paracon/paracon.py`
APPDIR=_zipapp

# Ensure clean target build directory
rm -rf $APPDIR
mkdir -p $APPDIR

# Application sources
mkdir $APPDIR/paracon
cp -p paracon/*.py $APPDIR/paracon
cp -p paracon/paracon.def $APPDIR/paracon

# Install dependencies
python3 -m pip install -r requirements-zipapp.txt --target $APPDIR/

# Build the zipapp and make it executable
python3 -m zipapp $APPDIR/ -p '/usr/bin/env python3' -o paracon_${VER}.pyz -m "paracon.paracon:run"
chmod a+x paracon_${VER}.pyz
