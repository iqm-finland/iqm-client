=========
Changelog
=========

Version 9.2
===========

* New external token is now obtained from tokens file if old token expired. `#58 <https://github.com/iqm-finland/iqm-client/pull/58>`_

Version 9.1
===========

* Update documentation. `#57 <https://github.com/iqm-finland/iqm-client/pull/57>`_

Version 9.0
===========

* The method ``IQMClient.get_quantum_architecture`` now return the architecture specification instead of the top level object. `#56 <https://github.com/iqm-finland/iqm-client/pull/56>`_

Version 8.4
===========

* Update documentation of Metadata. `#54 <https://github.com/iqm-finland/iqm-client/pull/54>`_

Version 8.3
===========

* Improved error message when ``qubit_mapping`` does not cover all qubits in a circuit. `#53 <https://github.com/iqm-finland/iqm-client/pull/53>`_
* Better type definitions and code cleanup. `#53 <https://github.com/iqm-finland/iqm-client/pull/53>`_, `#52 <https://github.com/iqm-finland/iqm-client/pull/52>`_

Version 8.2
===========

* Add method ``IQMClient.get_quantum_architecture``. `#51 <https://github.com/iqm-finland/iqm-client/pull/51>`_

Version 8.1
===========

* Change ``Circuit.instructions`` and ``Instruction.qubits`` from list to tuple. `#49 <https://github.com/iqm-finland/iqm-client/pull/49>`_

Version 8.0
===========

* Remove settings from RunRequest, add custom_settings. `#48 <https://github.com/iqm-finland/iqm-client/pull/48>`_

Version 7.3
===========

* Increase job result poll interval while waiting for circuit execution. `#47 <https://github.com/iqm-finland/iqm-client/pull/47>`_

Version 7.2
===========

* Add description of calibration set ID of RunResult metadata in the documentation. `#45 <https://github.com/iqm-finland/iqm-client/pull/45>`_

Version 7.1
===========

* Increase timeout of requests. `#43 <https://github.com/iqm-finland/iqm-client/pull/43>`_

Version 7.0
===========

* Add calibration set ID to RunResult metadata. `#42 <https://github.com/iqm-finland/iqm-client/pull/42>`_

Version 6.2
===========

* Enable mypy checks. `#41 <https://github.com/iqm-finland/iqm-client/pull/41>`_
* Update source code according to new checks in pylint v2.15.0. `#41 <https://github.com/iqm-finland/iqm-client/pull/41>`_

Version 6.1
===========

* Add optional ``calibration_set_id`` parameter to ``IQMClient.submit_circuit``. `#40 <https://github.com/iqm-finland/iqm-client/pull/40>`_

Version 6.0
===========

* ``IQMClient.close`` renamed to ``IQMClient.close_auth_session`` and raises an exception when asked to close an externally managed authentication session. `#39 <https://github.com/iqm-finland/iqm-client/pull/39>`_
* Try to automatically close the authentication session when the client is deleted. `#39 <https://github.com/iqm-finland/iqm-client/pull/39>`_
* Show CoCoS error on 401 response. `#39 <https://github.com/iqm-finland/iqm-client/pull/39>`_

Version 5.0
===========

* ``settings`` are moved from the constructor of ``IQMClient`` to ``IQMClient.submit_circuit``. `#31 <https://github.com/iqm-finland/iqm-client/pull/31>`_
* Changed the type of ``qubit_mapping`` argument of ``IQMClient.submit_circuit`` to ``dict[str, str]``. `#31 <https://github.com/iqm-finland/iqm-client/pull/31>`_
* User can now import from iqm_client using `from iqm_client import x` instead of `from iqm_client.iqm_client import x`. `#31 <https://github.com/iqm-finland/iqm-client/pull/31>`_

Version 4.3
===========

* Parse new field metadata for job result requests to the IQM quantum computer. `#37 <https://github.com/iqm-finland/iqm-client/pull/37>`_

Version 4.2
===========

* Update documentation to include development version and certain released versions in a subdirectory. `#36 <https://github.com/iqm-finland/iqm-client/pull/36>`_

Version 4.1
===========

* Add support for authentication without username/password, using externally managed tokens file. `#35 <https://github.com/iqm-finland/iqm-client/pull/35>`_

Version 4.0
===========

* Implement functionality to submit a batch of circuits in one job. `#34 <https://github.com/iqm-finland/iqm-client/pull/34>`_

Version 3.3
===========

* Make ``settings`` an optional parameter for ``IQMClient``. `#30 <https://github.com/iqm-finland/iqm-client/pull/30>`_

Version 3.2
===========

* Add function ``get_run_status`` to check status of execution without getting measurement results. `#29 <https://github.com/iqm-finland/iqm-client/pull/29>`_

Version 3.1
===========

* Update documentation to mention barriers. `#28 <https://github.com/iqm-finland/iqm-client/pull/28>`_

Version 3.0
===========

* Update HTTP endpoints for circuit execution and results retrieval. `#26 <https://github.com/iqm-finland/iqm-client/pull/26>`_
* Requires CoCoS 4.0

Version 2.2
===========

* Publish JSON schema for the circuit run request sent to an IQM server. `#24 <https://github.com/iqm-finland/iqm-client/pull/24>`_

Version 2.1
===========

* Add support for Python 3.10. `#23 <https://github.com/iqm-finland/iqm-client/pull/23>`_

Version 2.0
===========

* Update user authentication to use access token. `#22 <https://github.com/iqm-finland/iqm-client/pull/22>`_
* Add token management to IQMClient. `#22 <https://github.com/iqm-finland/iqm-client/pull/22>`_

Version 1.10
============

* Make ``qubit_mapping`` an optional parameter in ``IQMClient.submit_circuit``. `#21 <https://github.com/iqm-finland/iqm-client/pull/21>`_

Version 1.9
===========

* Validate that the schema of IQM server URL is http or https. `#20 <https://github.com/iqm-finland/iqm-client/pull/20>`_

Version 1.8
===========

* Add 'Expect: 100-Continue' header to the post request. `#18 <https://github.com/iqm-finland/iqm-client/pull/18>`_
* Bump pydantic dependency. `#13 <https://github.com/iqm-finland/iqm-client/pull/13>`_
* Minor updates in docs. `#13 <https://github.com/iqm-finland/iqm-client/pull/13>`_

Version 1.7
===========

* Emit warnings in server response as python UserWarning. `#15 <https://github.com/iqm-finland/iqm-client/pull/15>`_

Version 1.6
===========

* Configure automatic tagging and releasing. `#7 <https://github.com/iqm-finland/iqm-client/pull/7>`_

Version 1.5
===========

* Implement HTTP Basic auth. `#9 <https://github.com/iqm-finland/iqm-client/pull/9>`_

Version 1.4
===========

* Increase default timeout. `#8 <https://github.com/iqm-finland/iqm-client/pull/8>`_

Version 1.3
===========

Features
--------

* Document the native instruction types. `#5 <https://github.com/iqm-finland/iqm-client/pull/5>`_


Version 1.2
===========

Fixes
-----

* Remove unneeded args field from Circuit. `#4 <https://github.com/iqm-finland/iqm-client/pull/4>`_


Version 1.1
===========

Fixes
-----

* Changed example instruction phased_rx to measurement. `#2 <https://github.com/iqm-finland/iqm-client/pull/2>`_


Version 1.0
===========

Features
--------

* Split IQM client from the Cirq on IQM library
