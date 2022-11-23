=================
Integration Guide
=================

IQM client is designed to be the python adapter to IQMs quantum computers for application level quantum computing libraries.
For example integrations maintained by IQM please refer to the `Qiskit <https://github.com/iqm-finland/qiskit-on-iqm>`_ and `Cirq <https://github.com/iqm-finland/cirq-on-iqm>`_ integrations.

IQM client offers the functionality to submit circuits to an IQM quantum computer, query a job or a job status and retrieving the quantum architecture of the quantum computer being used.

The following sections give some information on how to integrate IQM quantum computers into your quantum computing framework.

Authentication
--------------

IQM uses OAuth 2.0 authentication to manage access to quantum computers. 
For easy token management we have developed `Cortex CLI<https://github.com/iqm-finland/cortex-cli>`_ which is the recommended way to generate and refresh tokens.
IQM client can read these tokens by providing the environment variable ``IQM_TOKENS_FILE`` pointing to the tokens file managed by Cortex CLI.

Circuit compilation
-------------------

IQM does not provide an open source circuit transpilation library so this will have to be supplied by the quantum computing framework or a third party library.
To provide the necessary information to do circuit transpilation :method:`IQMClient.get_quantum_architecture` returns the qubits, qubit connectivity and native operations.
This information should enable circuit transpilation for IQM quantum architectures.

Note on qubit mapping
---------------------

We encourage to transpile circuits to use the physical IQM qubit names before submitting them to IQM quantum computers.
In case the quantum computing framework does not allow for this, providing a qubmit mapping can do the translation from the framework qubit names to IQM qubit names.
We discourage exposing this feature to end users of the quantum computing framework.

Integration testing
-------------------

IQM provides a demo environment to test the integration against a simulated quantum computer. If you want access to that environment contact `IQM <info@meetiqm.com>`_.