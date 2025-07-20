# Configuration file for the Sphinx documentation builder.

# -- Path setup --------------------------------------------------------------

import os
import sys
sys.path.insert(0, os.path.abspath('..'))

import version


# -- Project information -----------------------------------------------------

project = 'Paracon'
copyright = '2024-2025, Martin F N Cooper. All rights reserved'
author = 'Martin F N Cooper'
release = version.get_version('../paracon/paracon.py')
version = release


# -- General configuration ---------------------------------------------------

templates_path = ['_templates']

rst_prolog = """
.. meta::
   :author: Martin F N Cooper
   :description: A simple packet radio terminal application for Linux, Mac
      and Windows.
"""


# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'prev_next_buttons_location': 'none'
}
html_copy_source = False
html_use_index = False
