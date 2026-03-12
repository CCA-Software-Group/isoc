isoc
----

[![Tests](https://github.com/CCA-Software-Group/isoc/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/CCA-Software-Group/isoc/actions/workflows/tests.yml)
[![Coverage](https://cca-software-group.github.io/isoc/coverage/badge.svg)](https://cca-software-group.github.io/py_template/isoc/index.html)
[![Docs](https://github.com/CCA-Software-Group/isoc/actions/workflows/docs.yml/badge.svg)](https://cca-software-group.github.io/isoc/)

`isoc` is a Python package for querying and retrieving 
isochrones from the MIST/MESA and Padova/PARSEC databases (or from local files
obtained from these databases). It has a simple user interface and relies on 
`ezpadova <https://github.com/mfouesneau/ezpadova/tree/master>`_ as a backend for 
queries to the Padova PARSEC database, and a custom backend for queries to the MIST database.

Install `isoc` with *pip*:
.. code-block:: bash

    pip install isoc

or *uv*:
.. code-block:: bash

    uv pip install isoc

See the [docs](https://cca-software-group.github.io/isoc/) for a short overview of how to use the package, as well as the
API. If you have any questions or suggestions, please open an issue.