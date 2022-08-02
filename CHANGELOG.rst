=========
Changelog
=========

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
