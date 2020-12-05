#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# hwtLib documentation build configuration file, created by
# sphinx-quickstart on Sat Mar 25 11:25:59 2017.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
from datetime import datetime
import glob
import os
import re
from sphinx.ext.apidoc import main as apidoc_main
import sphinx_bootstrap_theme
import sys

from hwt.pyUtils.fileHelpers import find_files
from hwt.serializer.mode import serializeExclude, serializeParamsUniq,\
    serializeOnce, _serializeExclude_eval, _serializeParamsUniq_eval,\
    _serializeOnce_eval


# add hwtLib to path
sys.path.insert(0, os.path.abspath('../'))
# add local sphinx extensions to path
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "_ext"))
)

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.todo',
              'sphinx.ext.viewcode',
              # 'sphinx.ext.napoleon',
              'sphinx.ext.graphviz',
              'aafig',
              'sphinx_hwt']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'hwtLib'
copyright = '2017-%d, Michal Orsak' % datetime.now().year
author = 'Michal Orsak'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = ''
# The full version, including alpha/beta/rc tags.
release = ''

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = 'en'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', '**test**']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
# html_theme = 'alabaster'

html_theme = 'bootstrap'
html_theme_path = sphinx_bootstrap_theme.get_html_theme_path()

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
# html_theme_options = {}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']


# -- Options for HTMLHelp output ------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = 'hwtLibdoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #
    # 'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    #
    # 'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    #
    # 'preamble': '',

    # Latex figure (float) alignment
    #
    # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (master_doc, 'hwtLib.tex', 'hwtLib generated documentation',
     'Michal Orsak', 'manual'),
]


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (master_doc, 'hwtLib', 'hwtLib Documentation',
     [author], 1)
]


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (master_doc, 'hwtLib', 'hwtLib Documentation',
     author, 'hwtLib', 'The library of hardware components and verification utils for hwt library.',
     'Miscellaneous'),
]

# -- Options for Epub output ----------------------------------------------

# Bibliographic Dublin Core info.
epub_title = project
epub_author = author
epub_publisher = author
epub_copyright = copyright

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
#
# epub_identifier = ''

# A unique identification for the text.
#
# epub_uid = ''

# A list of files that should not be packed into the epub file.
epub_exclude_files = ['search.html']

# aafig format, try to get working with pdf
aafig_format = dict(latex='pdf', html='gif')

aafig_default_options = dict(
    scale=.75,
    aspect=0.5,
    proportional=True,
)

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "private-members": True,
    'special-members': True,
    'show-inheritance': True,
}
autodoc_hide_members = (
    '__weakref__',  # special-members
    '__doc__', '__module__', '__dict__',  # undoc-members
)

def skip(app, what, name, obj, skip, options):
    # do not print the doc for common Unit/Interface methods if doc not specified
    # to reduce amount of duplicated doc
    if name in ("_config", "_declr", "_impl") and obj.__doc__ is None:
        return True
    elif name == "_serializeDecision" and obj in (_serializeExclude_eval, _serializeParamsUniq_eval, _serializeOnce_eval):
        return True
    return skip or (name in autodoc_hide_members)


def setup(app):
    app.connect("autodoc-skip-member", skip)


# update *.rst pages
for file in glob.glob("*.rst"):
    if file != "index.rst":
        print("removing: ", file)
        os.remove(file)

excluded_tests = list(find_files("../", "*_test.py")) +\
                 list(find_files("../", "test.py")) +\
                 list(find_files("../", "*.hwt.py")) +\
                 ["../hwtLib/tests"]
apidoc_main(["--module-first", "--full", "--maxdepth", "-1",
             "--output-dir", "../docs", "../hwtLib"] + excluded_tests)
