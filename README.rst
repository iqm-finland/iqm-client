|CI badge| |Release badge| |Black badge|

.. |CI badge| image:: https://github.com/iqm-finland/iqm-client/actions/workflows/ci.yml/badge.svg
.. |Release badge| image:: https://img.shields.io/github/release/iqm-finland/iqm-client.svg
.. |Black badge| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black

IQM Client
###########


**The IQM Client GitHub repository has been archived. The iqm-client package, including the source code, is available
at** `PyPI <https://pypi.org/project/iqm-client/>`_  **and the latest documentation is available at**
`<https://docs.meetiqm.com/iqm-client/>`_.

Client-side Python library for connecting to an `IQM <https://meetiqm.com/>`_ quantum computer.

Installation
============

IQM client is not intended to be used directly by human users. For executing code on an IQM quantum computer,
you can use for example the `Qiskit on IQM <https://iqm-finland.github.io/qiskit-on-iqm/>`_ library.

If you want just this library, though, you can install it from the Python Package Index (PyPI), e.g.:

.. code-block:: bash

    $ uv pip install iqm-client

.. note::

    `uv <https://docs.astral.sh/uv/>`_ is highly recommended for practical Python environment and package management.

Documentation
=============

Documentation for the latest version is `available online <https://docs.meetiqm.com/iqm-client/>`_.
You can build documentation for any older version locally by downloading the corresponding package from PyPI,
and running the docs builder. For versions 20.12 and later this is done by running ``./docbuild`` in the
``iqm-client`` root directory, and for earlier versions by running ``tox run -e docs``.

``./docbuild`` or ``tox run -e docs`` will build the documentation at ``./build/sphinx/html``.
These commands require the ``sphinx`` and ``sphinx-book-theme`` Python packages.

Copyright
=========

IQM client is free software, released under the Apache License, version 2.0.

Copyright 2021-2025 IQM client developers.
