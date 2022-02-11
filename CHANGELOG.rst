=========
Changelog
=========

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
