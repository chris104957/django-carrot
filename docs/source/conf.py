#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# carrot documentation build configuration file, created by
# sphinx-quickstart on Tue Sep 26 15:41:05 2017.
#

import sys
import os
import sphinx_bootstrap_theme
import django
from carrot import __version__


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, os.path.abspath('.'))
sys.path.append(BASE_DIR)
sys.path.append(os.path.dirname(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'doc_settings')
django.setup()

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.coverage',
]

templates_path = ['_templates']

source_suffix = '.rst'

master_doc = 'index'

# General information about the project.
project = 'django-carrot'
copyright = '2017-2018, Christopher Davies'
author = 'Christopher Davies'

version = __version__
release = __version__

language = None

exclude_patterns = []

pygments_style = 'sphinx'

todo_include_todos = False

html_theme = 'bootstrap'
html_theme_path = sphinx_bootstrap_theme.get_html_theme_path()

html_theme_options = {
    # Tab name for entire site. (Default: "Site")
    'navbar_site_name': "Topics",

    'navbar_links': [
        ("Home", "index"),
        ("What's new", "release-notes"),
        ("Getting started", "quick-start"),
        ("Monitor", "monitor"),
        ("Configuration", "settings"),
        ("API", "api"),

    ],

    # Render the next and previous page links in navbar. (Default: true)
    'navbar_sidebarrel': False,

    'globaltoc_depth': -1,

    # Render the current pages TOC in the navbar. (Default: true)
    'navbar_pagenav': False,

    # Location of link to source.
    'source_link_position': None,

    # - Bootstrap 3: https://bootswatch.com/3
    'bootswatch_theme': "united",
}

html_static_path = ['_static']

htmlhelp_basename = 'carrotdoc'


latex_elements = {}

latex_documents = [
    (master_doc, 'carrot.tex', 'carrot Documentation',
     'Christopher Davies', 'manual'),
]

man_pages = [
    (master_doc, 'carrot', 'carrot Documentation',
     [author], 1)
]

texinfo_documents = [
    (master_doc, 'carrot', 'carrot Documentation',
     author, 'carrot', 'One line description of project.',
     'Miscellaneous'),
]

intersphinx_mapping = {'https://docs.python.org/': None}


def setup(app):
    app.add_stylesheet('carrot.css')

