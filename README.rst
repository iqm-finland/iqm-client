|CI badge| |Release badge| |Black badge|

.. |CI badge| image:: https://github.com/iqm-finland/iqm-client/actions/workflows/ci.yml/badge.svg
.. |Release badge| image:: https://img.shields.io/github/release/iqm-finland/iqm-client.svg
.. |Black badge| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black

IQM Client
###########

Client-side Python library for connecting to an `IQM <https://meetiqm.com/>`_ quantum computer.

Installation
============

IQM client is not intended to be used directly by human users. For executing code on an IQM quantum computer,
you can use for example the `Qiskit on IQM <https://iqm-finland.github.io/qiskit-on-iqm/>`_ library.

If you want just this library, though, you can install it from the Python Package Index (PyPI):

.. code-block:: bash

    $ pip install iqm-client

Documentation
=============

Documentation for the latest version is `available online <https://iqm-finland.github.io/iqm-client/>`_. 
You can build documentation for any older version locally by cloning the Git repository, checking out the 
corresponding tag, and running the docs builder. For example, to build the documentation for version ``15.4``:

.. code-block:: bash

    $ git clone git@github.com:iqm-finland/iqm-client.git
    $ cd iqm-client
    $ git checkout 15.4
    $ tox run -e docs

(Unless you need to build documentation for multiple versions, consider passing ``git clone`` options to
only clone the commit for the specific version tag, e.g. ``--branch 15.4 --depth 1`` for version ``15.4``.
This will be much faster than cloning the full repository, because some large files have been stored
in the commit history.)

``tox run -e docs`` will build the documentation at ``./build/sphinx/html``. This command requires the ``tox,``, ``sphinx`` and
``sphinx-book-theme`` Python packages (see the ``docs`` optional dependency in ``pyproject.toml``); 
you can install the necessary packages with ``pip install -e ".[dev,docs]"``

Copyright
=========

IQM client is free software, released under the Apache License, version 2.0.

Copyright 2021-2024 IQM client developers.
