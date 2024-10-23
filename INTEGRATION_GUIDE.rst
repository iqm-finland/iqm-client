=================
Integration Guide
=================

IQM client is designed to be the Python adapter to IQM's quantum computers for application-level
quantum computing frameworks.  For example integrations maintained by IQM, please refer to the
`Qiskit <https://github.com/iqm-finland/qiskit-on-iqm>`_ and
`Cirq <https://github.com/iqm-finland/cirq-on-iqm>`_ packages.

IQM client offers the functionality to submit quantum circuits to an IQM quantum computer, query a
job or a job status, and retrieve the quantum architecture of the quantum computer.

The following sections illustrate how to integrate IQM quantum computers into your quantum computing
framework.

Code example
------------

Initialising the IQM client is simple, and in case you perform authentication as described below,
requires only the URL of the IQM quantum computer.

.. code-block:: python

    from iqm.iqm_client import IQMClient

    server_url = "https://IQM_SERVER_URL"

    iqm_client = IQMClient(server_url)

To submit a quantum circuit for execution, it has to be specified using the :class:`.Circuit` class.
The available native instructions are documented in the :class:`.Instruction` class.

.. code-block:: python

    from iqm.iqm_client import Circuit, Instruction

    instructions = (
        Instruction(
            name="prx", qubits=("QB1",), args={"phase_t": 0.7, "angle_t": 0.25}
        ),
        Instruction(name="cz", qubits=("QB1", "QB2"), args={}),
        Instruction(name="measure", qubits=("QB2",), args={"key": "Qubit 2"}),
    )

    circuit = Circuit(name="quantum_circuit", instructions=instructions)

Then the circuit can be submitted, and its status and result can be queried with the job id.

.. code-block:: python

    job_id = iqm_client.submit_circuits([circuit])

    job_status = iqm_client.get_run_status(job_id)

    job_result = iqm_client.wait_for_results(job_id)

A dict containing arbitrary metadata can be attached to the circuit before submitting it for
execution. The attached metadata should consist only of values of JSON serializable datatypes.
A utility function :func:`~.iqm_client.util.to_json_dict` can be used to convert supported datatypes,
e.g. :class:`numpy.ndarray`, to equivalent JSON serializable types.

The progress of the job can be followed with :meth:`.IQMClient.get_run_status`. Once the job is ready,
the results can be read with :meth:`.IQMClient.get_run`. Both of these actions are combined in
:meth:`.IQMClient.wait_for_results` which waits until the job is ready and then returns the result.

In addition to the actual results, job result contains also metadata of the job execution.
The metadata includes the original request, ID of the calibration set used in the execution, and
a collection of timestamps describing the duration of the execution.

Job phases and related timestamps
---------------------------------

The timestamps returned with job results are stored as an optional dict called ``timestamps`` in the metadata of
:class:`.RunResult` of the job. Each timestamp is stored in the dict with a key describing the point in job processing where
the timestamp was stored. For example, the timestamp stored at the start of circuit compilation step is stored with
key ``compile_start``. Other timestamps are stored in the same way, with keys containing the step name,
``compile``, ``submit`` or ``execution``, and either a ``_start`` or ``_end`` suffix. In addition, there are
also timestamps for starting and ending the job itself, ``job_start`` and ``job_end``. If the job processing is
terminated before it is complete the timestamps of steps not processed will not be present in the dict.

The first timestamp stored is the ``job_start`` timestamp. It is stored when the server receives the job request.

The job processing starts with compilation step where the circuits are converted to pulse schedules that can be
sent for execution. Compilation step produces timestamps ``compile_start`` and ``compile_end``.

The pulse schedules are then submitted for execution. This step produces timestamps
``submit_start`` and ``submit_end``.

After submitting the pulse schedules the server waits for the execution results.
This step produces timestamps ``execution_start`` and ``execution_end``.

Finally, when job processing is complete, regardless whether the job was successful or not, the timestamp
``job_end`` is stored.


Authentication
--------------

IQM uses bearer token authentication to manage access to quantum computers.
Currently, there are three mutually exclusive ways of providing an authentication
token to IQM client:

1. The recommended way is to use `Cortex CLI <https://github.com/iqm-finland/cortex-cli>`_
to manage the authentication tokens and store them into a file. IQM client can then read
the token from the file and use it for authentication. The file path can be provided to
IQM client in environment variable ``IQM_TOKENS_FILE``.
Alternatively, the tokens file path can be provided as argument ``tokens_file`` to
:class:`.IQMClient` constructor.

2. It is also possible to use plaintext token obtained from a server dashboard. These
tokens may have longer lifespan than access tokens generated by Cortex CLI, and thus
IQM client won't attempt to refresh them. The generated token can be provided to IQM
client in environment variable ``IQM_TOKEN``.
Alternatively, the token can be provided as argument ``token`` to :class:`.IQMClient`
constructor.

3. The third way is to provide server URL, username and password for obtaining the
token from an authentication server. IQM client will maintain a login session with
the authentication server and read and refresh the token as needed. The server URL,
username and password can be provided to IQM client in environment variables
``IQM_AUTH_SERVER``, ``IQM_AUTH_USERNAME`` and ``IQM_AUTH_PASSWORD``.
Alternatively, the values can be provided as arguments ``auth_server_url``,
``username`` and ``password`` to :class:`.IQMClient` constructor.
Note, that all the values must be provided as either environment variables or
as constructor arguments, not mixed.

Circuit transpilation
---------------------

IQM does not provide an open source circuit transpilation library, so this will have to be supplied
by the quantum computing framework or a third party library.  To obtain the necessary information
for circuit transpilation, :meth:`.IQMClient.get_dynamic_quantum_architecture` returns the names of the
QPU components (qubits and computational resonators), and the native operations available
in the given calibration set. This information should enable circuit transpilation for IQM quantum architectures.

The notable exception is the transpilation of MOVE gates for IQM quantum computers with
computational resonators, for which some specialized transpilation logic is provided.  The MOVE gate
moves the state of a qubit to an empty computational resonator, and vice versa, so that the qubit
can interact with other qubits connected to the resonator.  For this, we provide users with two
transpilation functions: :func:`.transpile_insert_moves` and :func:`.transpile_remove_moves`.  These
functions can be used to insert or remove MOVE gates from the circuit, respectively.

:func:`.transpile_insert_moves` is a transpiler pass for inserting MOVE gates into a circuit for
devices with a computational resonator.  It assumes that the circuit is already transpiled by third
party software to an architecture where the computational resonator has been abstracted away.  To
abstract away the computational resonator, the connectivity graph is modified such that all the
qubits connected to a common resonator are instead connected directly to each other.  The function
can take a ``qubit_mapping`` to rename the qubits in the circuit to match the physical qubit names.
Additionally, the function can take the optional argument ``existing_moves`` to specify how this
transpiler pass should handle the case where some MOVE gates are already present in the circuit. The
options are specified by the enum :class:`.ExistingMoveHandlingOptions`.  By default the function
warns the user if MOVE gates are already present in the circuit but the ``existing_moves`` argument
is not given, before proceeding to remove the existing MOVE gates and inserting new ones.

:func:`.transpile_remove_moves` is a helper function for :func:`.transpile_insert_moves` to remove
existing MOVE gates from a quantum circuit.  It can be also used standalone to remove the MOVE gates
from an existing circuit such that it can be used on a device without a computational resonator, or
optimized by third party software that does not support the MOVE gate.  For example, a user might
want to run a circuit that was originally transpiled for a device with a computational resonator on
a device without a computational resonator.  This function allows the user to remove the MOVE gates
from the circuit before transpiling it to another quantum architecture.


.. code-block:: python

    from iqm.iqm_client import Circuit, IQMClient, transpile_insert_moves, transpile_remove_moves

    circuit = Circuit(name="quantum_circuit", instructions=[...])
    backend_with_resonator = IQMClient("url_to_backend_with_resonator")
    backend_without_resonator = IQMClient("url_to_backend_without_resonator")

    # intended use
    circuit_with_moves = transpile_insert_moves(circuit, backend_with_resonator.get_dynamic_quantum_architecture())
    circuit_without_moves = transpile_remove_moves(circuit_with_moves)

    backend_with_resonator.submit_circuits([circuit_with_moves])
    backend_without_resonator.submit_circuits([circuit_without_moves])

    # Using the transpile_insert_moves on a device that does not support MOVE gates does nothing.
    assert circuit == transpile_insert_moves(circuit, backend_without_resonator.get_dynamic_quantum_architecture())
    # Unless the circuit had MOVE gates, then it can remove them with the existing_moves argument.
    alt_circuit_without_moves = transpile_insert_moves(circuit, backend_without_resonator.get_dynamic_quantum_architecture(), existing_moves=ExistingMoveHandlingOptions.REMOVE)


Note on qubit mapping
---------------------

We encourage to transpile circuits to use the physical IQM qubit names before submitting them to IQM
quantum computers.  In case the quantum computing framework does not allow for this, providing a
qubit mapping can do the translation from the framework qubit names to IQM qubit names.  Note, that
qubit mapping is not supposed to be associated with individual circuits, but rather with the entire
job request to IQM server.  Typically, you would have some local representation of the QPU and
transpile the circuits against that representation, then use qubit mapping along with the generated
circuits to map from the local representation to the IQM representation of qubit names.  We
discourage exposing this feature to end users of the quantum computing framework.

Note on circuit duration check
------------------------------

Before performing circuit execution, IQM server checks how long it would take to run each circuit.
If any circuit in a job would take too long to execute compared to the T2 time of the qubits,
the server will disqualify the job, not execute any circuits, and return a detailed error message.
In some special cases, it makes sense to adjust or disable this check using
the :attr:`max_circuit_duration_over_t2` attribute of :class:`.CircuitCompilationOptions`,
and then passing the options to :meth:`.IQMClient.submit_circuits`.

Note on environment variables
-----------------------------

Set :envvar:`IQM_CLIENT_REQUESTS_TIMEOUT` environment variable to override the network requests default
timeout value. The default value is 60 seconds and might not be sufficient when fetching run results
of larger circuits via slow network connections.

On Linux:

.. code-block:: bash

  $ export IQM_CLIENT_REQUESTS_TIMEOUT=120

On Windows:

.. code-block:: batch

  set IQM_CLIENT_REQUESTS_TIMEOUT=120

Once set, this environment variable will control network request timeouts for :class:`.IQMClient` methods
``abort_job``, ``get_quantum_architecture``, ``get_dynamic_quantum_architecture``, ``get_run``, and ``get_run_status``.

Set :envvar:`IQM_CLIENT_SECONDS_BETWEEN_CALLS` to control the polling frequency when waiting for
compilation and run results with the :meth:`.IQMClient.wait_for_compilation` and
:meth:`.IQMClient.wait_for_results` methods. The default value is set to 1 second.

Set :envvar:`IQM_CLIENT_DEBUG=1` to print the run request when it is submitted for execution in
:meth:`.IQMClient.submit_circuits` or :meth:`.IQMClient.submit_run_request`. To inspect the run request without sending
it for execution, use :meth:`.IQMClient.create_run_request`.

Integration testing
-------------------

IQM provides a demo environment to test the integration against a mock quantum computer. If you'd
like to request access to that environment, please contact `IQM <info@meetiqm.com>`_.
