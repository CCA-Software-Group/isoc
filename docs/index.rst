Documentation
=============

Welcome to the docs for ``isoc``, a Python package for querying and retrieving 
isochrones from the MIST/MESA and Padova/PARSEC databases (or from local files
obtained from these databases). It has a simple user interface and relies on 
`ezpadova <https://github.com/mfouesneau/ezpadova/tree/master>`_ as a backend for 
queries to the Padova PARSEC database, and a custom backend for queries to the MIST database.

Install ``isoc`` with *pip*:

.. code-block:: bash

    pip install isoc

See the :doc:`quickstart tutorial <demo>` for a simple overview of how to use the package.
Or see the API for more detail. If you have any questions or suggestions, please 
`open an issue <https://github.com/CCA-Software-Group/isoc/issues>`_.

.. toctree:: 
   :maxdepth: 1
   :caption: Tutorials

    Quickstart <demo>

.. toctree:: 
   :maxdepth: 1
   :caption: Reference

    API <py_API>
    Index <genindex>
    GitHub repo <https://github.com/CCA-Software-Group/isoc>