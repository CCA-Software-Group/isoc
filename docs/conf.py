# Configuration file for the Sphinx documentation builder.
#
# This file does only contain a selection of the most common options. For a
# full list see the documentation:
# http://www.sphinx-doc.org/en/master/config

import datetime

# -- Project information -----------------------------------------------------
# The full version, including alpha/beta/rc tags
from isoc import __version__

release = __version__

project = "isoc"
author = "CCA Software Group"
copyright = f"{datetime.datetime.now().year}, {author}"  # noqa: A001

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named "sphinx.ext.*") or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.coverage",
    "sphinx.ext.inheritance_diagram",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.doctest",
    "sphinx.ext.mathjax",
    "sphinx_automodapi.automodapi",
    "sphinx_automodapi.smart_resolver",
    "nbsphinx",
    "sphinx_thebe",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# The master toctree document.
master_doc = "index"

# Treat everything in single ` as a Python reference.
default_role = "py:obj"

# -- Options for intersphinx extension ---------------------------------------

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {"python": ("https://docs.python.org/", None)}

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "pydata_sphinx_theme"

html_theme_options = {
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/CCA-Software-Group/isoc",
            "icon": "fa-brands fa-github",
            "type": "fontawesome",
        },
    ],
    "secondary_sidebar_items": [],
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
html_css_files = ["custom.css"]


# By default, when rendering docstrings for classes, sphinx.ext.autodoc will
# make docs with the class-level docstring and the class-method docstrings,
# but not the __init__ docstring, which often contains the parameters to
# class constructors across the scientific Python ecosystem. The option below
# will append the __init__ docstring to the class-level docstring when rendering
# the docs. For more options, see:
# https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#confval-autoclass_content
autoclass_content = "both"

# -- Other options ----------------------------------------------------------

# -- Thebe (interactive notebooks) ------------------------------------------
# Connects the "Run interactively" button to Binder via sphinx-thebe.
thebe_config = {
    "repository_url": "https://github.com/CCA-Software-Group/isoc",
    "repository_branch": "main",
}

# Add icon buttons at the top of every notebook page:
#   ▶  run interactively via Thebe/Binder
#   ⬇  download the raw .ipynb file from GitHub
nbsphinx_prolog = r"""
.. raw:: html

   <script>
   async function _nbDownload(name) {
       const url = 'https://raw.githubusercontent.com/CCA-Software-Group/isoc/main/docs/' + name + '.ipynb';
       try {
           const r = await fetch(url);
           const blob = await r.blob();
           const a = document.createElement('a');
           a.href = URL.createObjectURL(blob);
           a.download = name + '.ipynb';
           document.body.appendChild(a);
           a.click();
           document.body.removeChild(a);
           URL.revokeObjectURL(a.href);
       } catch (_) { window.open(url); }
   }
   </script>
   <div class="nb-toolbar">
     <button class="thebe-launch-button"
             onclick="initThebe()"
             title="Run notebook interactively (via Binder)">
       <i class="fa-solid fa-play" aria-hidden="true"></i>
       <span>Run interactively</span>
     </button>
     <button class="nb-download-link"
             onclick="_nbDownload('{{ env.docname.split('/')[-1] }}')"
             title="Download notebook (.ipynb)">
       <i class="fa-solid fa-download" aria-hidden="true"></i>
       <span>Download notebook</span>
     </button>
   </div>
"""
