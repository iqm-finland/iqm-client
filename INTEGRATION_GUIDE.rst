=================
Integration Guide
=================

IQM client is designed to be the python adapter to IQMs quantum computers for application level quantum computing frameworks.
For example integrations maintained by IQM please refer to the `Qiskit <https://github.com/iqm-finland/qiskit-on-iqm>`_ and `Cirq <https://github.com/iqm-finland/cirq-on-iqm>`_ integrations.

IQM client offers the functionality to submit circuits to an IQM quantum computer, query a job or a job status and retrieve the quantum architecture of the quantum computer being used.

The following sections give some information on how to integrate IQM quantum computers into your quantum computing framework.

Code example
------------

Initialising the IQM client is simple and in case you perform authentication as described below requires only the URL to the IQM quantum computer.

.. code-block:: python

    from iqm_client import IQMClient

    server_url = "https://my_iqm.qc.fi"

    iqm_client = IQMClient(server_url)

To submit a circuit the circuit has to be specified in the IQM transfer format.

.. code-block:: python

    from iqm_client import Circuit, Instruction

    instructions = (
        Instruction(
            name="phased_rx", qubits=("QB1",), args={"phase_t": 0.7, "angle_t": 0.25}
        ),
        Instruction(name="cz", qubits=("QB1", "QB2"), args={}),
        Instruction(name="measurement", qubits=("QB2",), args={"key": "Qubit 2"}),
    )

    circuit = Circuit(name="quantum_circuit", instructions=instructions)

Then the circuit can be submitted and its status and result can be queried with the job id.

.. code-block:: python

    job_id = iqm_client.submit_circuits([circuit])

    job_status = iqm_client.get_run_status(job_id)

    job = iqm_client.wait_for_results(job_id)

A dict containing arbitrary metadata an be attached to the circuit before submitting it for
execution. The attached metadata should consist only of values of JSON serializable datatypes.
An utility function ``util.to_json_dict`` can be used to convert supported datatypes,
e.g. ``numpy.ndarray``, to equivalent JSON serializable types.

Authentication
--------------

IQM uses OAuth 2.0 authentication to manage access to quantum computers. 
For easy token management we have developed `Cortex CLI <https://github.com/iqm-finland/cortex-cli>`_ which is the recommended way to generate and refresh tokens.
IQM client can use these tokens by reading an environment variable ``IQM_TOKENS_FILE`` pointing to the tokens file managed by Cortex CLI.

Circuit compilation
-------------------

IQM does not provide an open source circuit transpilation library so this will have to be supplied by the quantum computing framework or a third party library.
To provide the necessary information to do circuit transpilation :meth:`IQMClient.get_quantum_architecture` returns the qubits, qubit connectivity and native operations.
This information should enable circuit transpilation for IQM quantum architectures.

Note on qubit mapping
---------------------

We encourage to transpile circuits to use the physical IQM qubit names before submitting them to IQM quantum computers.
In case the quantum computing framework does not allow for this, providing a qubit mapping can do the translation from the framework qubit names to IQM qubit names.
Note, that qubit mapping is not supposed to be associated with individual circuits, but rather with the entire job request to IQM server.
Typically, you would have some local representation of the QPU and transpile the circuits against that representation, then use qubit mapping along with the generated circuits to map from the local representation to the IQM representation of qubit names.
We discourage exposing this feature to end users of the quantum computing framework.

Integration testing
-------------------

IQM provides a demo environment to test the integration against a simulated quantum computer. If you want access to that environment contact `IQM <info@meetiqm.com>`_.
