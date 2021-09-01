How to develop and contribute
-----------------------------

IQM client is an open source Python project.
You can contribute by creating GitHub issues to report bugs or request new features,
or by opening a pull request to submit your own improvements to the codebase.

To start developing the project, clone the
`GitHub repository <https://github.com/iqm-finland/iqm-client>`_
and install it in editable mode with all the extras:

.. code-block:: bash

   $ git clone git@github.com:iqm-finland/iqm-client.git
   $ cd iqm-client
   $ pip install -e ".[dev,docs,testing]"


Build and view the docs:

.. code-block:: bash

   $ tox -e docs

To view the documentation, open the file ``build/sphinx/html/index.html``
in a browser.


Run the tests:

.. code-block:: bash

   $ tox
