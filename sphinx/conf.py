import os
import sys
sys.path.insert(0, os.path.abspath('../'))

import app.db.data_table
import app.db.repository
import app.integrations.ytapi
import app.integrations.ytdlp
import app.service.yt_monitor


# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Youtube node downloader'
copyright = '2024, mithmith'
author = 'mithmith'
release = '0.0.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = []

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
extensions = [
    'sphinx.ext.autodoc',  # Includes documentation from docstrings
    'sphinx.ext.coverage',  # Checks documentation coverage
    'sphinx.ext.napoleon',  # Support for Google and NumPy style docstrings
    'sphinx.ext.viewcode',  # Adds links to the source code of documented Python objects
]
