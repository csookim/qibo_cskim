import copy
import random

import numpy as np

from qibo import gates
from qibo.backends import GlobalBackend
from qibo.config import raise_error
from qibo.hamiltonians.abstract import AbstractHamiltonian
from qibo.hamiltonians.hamiltonians import SymbolicHamiltonian
from qibo.models import Circuit
from qibo.symbols import Z


class Parameter:
    def __init__(self, func, trainablep, featurep=None):
        self._trainablep = trainablep
        self._featurep = featurep
        self.nparams = len(trainablep)
        self.lambdaf = func

    def _apply_func(self, fixed_params=None):
        params = []
        if self._featurep is not None:
            params.append(self._featurep)
        if fixed_params:
            params.extend(fixed_params)
        else:
            params.extend(self._trainablep)
        return self.lambdaf(*params)

    def _update_params(self, trainablep=None, feature=None):
        if trainablep:
            self._trainablep = trainablep
        if feature:
            self._featurep = feature

    def get_params(self, trainablep=None, feature=None):
        self._update_params(trainablep=trainablep, feature=feature)
        return self._apply_func()

    def get_indices(self, start_index):
        return [start_index + i for i in range(self.nparams)]

    def get_fixed_part(self, trainablep_idx):
        params = [0] * self.nparams
        params[trainablep_idx] = self._trainablep[trainablep_idx]
        return self._apply_func(fixed_params=params)

    def get_scaling_factor(self, trainablep_idx):
        params = [0] * self.nparams
        params[trainablep_idx] = 1.0
        return self._apply_func(fixed_params=params)


def calculate_gradients(optimizer, feature):
    """
    Full parameter-shift rule's implementation
    Args:
        this_feature: np.array 2**nqubits-long containing the state vector assciated to a data
    Returns: np.array of the observable's gradients with respect to the variational parameters
    """

    obs_gradients = np.zeros(optimizer.nparams, dtype=np.float64)

    ham = SymbolicHamiltonian(
        np.prod([Z(i) for i in range(1)]), backend=GlobalBackend()
    )

    # parameter shift
    if optimizer.options["shift_rule"] == "psr":
        if isinstance(optimizer.paramInputs, np.ndarray):
            for ipar in range(optimizer.nparams):
                obs_gradients[ipar] = parameter_shift(
                    optimizer._circuit,
                    ham,
                    ipar,
                    initial_state=None,
                    scale_factor=1,
                    nshots=None,
                )
        else:
            count = 0
            for ipar, Param in enumerate(optimizer.paramInputs):
                for nparam in range(Param.nparams):
                    scaling = Param.get_scaling_factor(nparam, feature)

                    obs_gradients[count] = parameter_shift(
                        optimizer._circuit,
                        ham,
                        ipar,
                        initial_state=None,
                        scale_factor=scaling,
                        nshots=None,
                    )
                    count += 1

    # stochastic parameter shift
    elif optimizer.options["shift_rule"] == "spsr":
        for ipar, Param in enumerate(optimizer.parameters):
            ntrainable_params = Param.nparams
            obs_gradients[ipar : ipar + ntrainable_params] = stochastic_parameter_shift(
                optimizer._circuit,
                ham,
                ipar,
                initial_state=None,
                scale_factor=1,
                nshots=None,
            )

    # finite differences (central difference)
    else:
        for ipar in range(optimizer.nparams):
            obs_gradients[ipar] = finite_differences(
                optimizer._circuit,
                ham,
                ipar,
                initial_state=None,
                scale_factor=1,
                nshots=None,
            )

    return obs_gradients


def parameter_shift(
    circuit,
    hamiltonian,
    parameter_index,
    initial_state=None,
    scale_factor=1,
    nshots=None,
):
    """In this method the parameter shift rule (PSR) is implemented.
    Given a circuit U and an observable H, the PSR allows to calculate the derivative
    of the expected value of H on the final state with respect to a variational
    parameter of the circuit.
    There is also the possibility of setting a scale factor. It is useful when a
    circuit's parameter is obtained by combination of a variational
    parameter and an external object, such as a training variable in a Quantum
    Machine Learning problem. For example, performing a re-uploading strategy
    to embed some data into a circuit, we apply to the quantum state rotations
    whose angles are in the form: theta' = theta * x, where theta is a variational
    parameter and x an input variable. The PSR allows to calculate the derivative
    with respect of theta' but, if we want to optimize a system with respect its
    variational parameters we need to "free" this procedure from the x depencency.
    If the `scale_factor` is not provided, it is set equal to one and doesn't
    affect the calculation.
    If the PSR is needed to be executed on a real quantum device, it is important
    to set `nshots` to some integer value. This enables the execution on the
    hardware by calling the proper methods.

    Args:
        circuit (:class:`qibo.models.circuit.Circuit`): custom quantum circuit.
        hamiltonian (:class:`qibo.hamiltonians.Hamiltonian`): target observable.
            if you want to execute on hardware, a symbolic hamiltonian must be
            provided as follows (example with Pauli Z and ``nqubits=1``):
            ``SymbolicHamiltonian(np.prod([ Z(i) for i in range(1) ]))``.
        parameter_index (int): the index which identifies the target parameter
            in the ``circuit.get_parameters()`` list.
        initial_state (ndarray, optional): initial state on which the circuit
            acts. Default is ``None``.
        scale_factor (float, optional): parameter scale factor. Default is ``1``.
        nshots (int, optional): number of shots if derivative is evaluated on
            hardware. If ``None``, the simulation mode is executed.
            Default is ``None``.

    Returns:
        (float): Value of the derivative of the expectation value of the hamiltonian
            with respect to the target variational parameter.

    Example:

        .. testcode::

            import qibo
            import numpy as np
            from qibo import hamiltonians, gates
            from qibo.models import Circuit
            from qibo.derivative import parameter_shift

            # defining an observable
            def hamiltonian(nqubits = 1):
                m0 = (1/nqubits)*hamiltonians.Z(nqubits).matrix
                ham = hamiltonians.Hamiltonian(nqubits, m0)

                return ham

            # defining a dummy circuit
            def circuit(nqubits = 1):
                c = Circuit(nqubits = 1)
                c.add(gates.RY(q = 0, theta = 0))
                c.add(gates.RX(q = 0, theta = 0))
                c.add(gates.M(0))

                return c

            # initializing the circuit
            c = circuit(nqubits = 1)

            # some parameters
            test_params = np.random.randn(2)
            c.set_parameters(test_params)

            test_hamiltonian = hamiltonian()

            # running the psr with respect to the two parameters
            grad_0 = parameter_shift(circuit=c, hamiltonian=test_hamiltonian, parameter_index=0)
            grad_1 = parameter_shift(circuit=c, hamiltonian=test_hamiltonian, parameter_index=1)

    """

    # some raise_error
    if parameter_index > len(circuit.get_parameters()):
        raise_error(ValueError, """This index is out of bounds.""")

    if not isinstance(hamiltonian, AbstractHamiltonian):
        raise_error(
            TypeError,
            "hamiltonian must be a qibo.hamiltonians.Hamiltonian or qibo.hamiltonians.SymbolicHamiltonian object",
        )

    # inheriting hamiltonian's backend
    backend = hamiltonian.backend

    # getting the gate's type
    gate = circuit.associate_gates_with_parameters()[parameter_index]

    # getting the generator_eigenvalue
    generator_eigenval = gate.generator_eigenvalue()

    # defining the shift according to the psr
    s = np.pi / (4 * generator_eigenval)

    # saving original parameters and making a copy
    original = np.asarray(circuit.get_parameters()).copy()
    shifted = original.copy()

    # forward shift
    shifted[parameter_index] += s
    circuit.set_parameters(shifted)

    if nshots is None:
        # forward evaluation
        forward = hamiltonian.expectation(
            backend.execute_circuit(
                circuit=circuit, initial_state=initial_state
            ).state()
        )

        # backward shift and evaluation
        shifted[parameter_index] -= 2 * s
        circuit.set_parameters(shifted)

        backward = hamiltonian.expectation(
            backend.execute_circuit(
                circuit=circuit, initial_state=initial_state
            ).state()
        )

    # same but using expectation from samples
    else:
        forward = backend.execute_circuit(
            circuit=circuit, initial_state=initial_state, nshots=nshots
        ).expectation_from_samples(hamiltonian)

        shifted[parameter_index] -= 2 * s
        circuit.set_parameters(shifted)

        backward = backend.execute_circuit(
            circuit=circuit, initial_state=initial_state, nshots=nshots
        ).expectation_from_samples(hamiltonian)

    circuit.set_parameters(original)

    # float() necessary to not return a 0-dim ndarray
    result = float(generator_eigenval * (forward - backward) * scale_factor)
    return result


def generate_new_stochastic_params(Param, ipar):
    """Generates the three-gate parameters needed for the stochastic parameter-shift rule"""

    sampling = random.random()
    trainable_param = Param._trainablep[ipar]
    F = Param.get_fixed_part(ipar)
    scaling = Param.get_scaling_factor(ipar)

    return [sampling * F, trainable_param, (1 - sampling) * F], scaling


def stochastic_parameter_shift(
    circuit,
    hamiltonian,
    parameter_index,
    parameter: Parameter,
    initial_state=None,
    nshots=None,
):
    """In this method the stochastic parameter shift rule (SPSR) is implemented.
    Given a circuit U and an observable H, the SPSR allows to calculate the derivative
    of the expected value of H on the final state with respect to a variational
    parameter of the circuit. The SPSR can calculate gradient approximations on
    a larger family of gates than the standard PSR.
    There is also the possibility of setting a scale factor. It is useful when a
    circuit's parameter is obtained by combination of a variational
    parameter and an external object, such as a training variable in a Quantum
    Machine Learning problem. For example, performing a re-uploading strategy
    to embed some data into a circuit, we apply to the quantum state rotations
    whose angles are in the form: theta' = theta * x, where theta is a variational
    parameter and x an input variable. The PSR allows to calculate the derivative
    with respect of theta' but, if we want to optimize a system with respect its
    variational parameters we need to "free" this procedure from the x depencency.
    If the `scale_factor` is not provided, it is set equal to one and doesn't
    affect the calculation.
    If the PSR is needed to be executed on a real quantum device, it is important
    to set `nshots` to some integer value. This enables the execution on the
    hardware by calling the proper methods.

    Args:
        circuit (:class:`qibo.models.circuit.Circuit`): custom quantum circuit.
        hamiltonian (:class:`qibo.hamiltonians.Hamiltonian`): target observable.
            if you want to execute on hardware, a symbolic hamiltonian must be
            provided as follows (example with Pauli Z and ``nqubits=1``):
            ``SymbolicHamiltonian(np.prod([ Z(i) for i in range(1) ]))``.
        parameter_index (int): the index which identifies the target parameter
            in the ``circuit.get_parameters()`` list.
        initial_state (ndarray, optional): initial state on which the circuit
            acts. Default is ``None``.
        scale_factor (float, optional): parameter scale factor. Default is ``1``.
        nshots (int, optional): number of shots if derivative is evaluated on
            hardware. If ``None``, the simulation mode is executed.
            Default is ``None``.

    Returns:
        (float): Value of the derivative of the expectation value of the hamiltonian
            with respect to the target variational parameter.

    Example:

        .. testcode::

            import qibo
            import numpy as np
            from qibo import hamiltonians, gates
            from qibo.models import Circuit
            from qibo.derivative import parameter_shift

            # defining an observable
            def hamiltonian(nqubits = 1):
                m0 = (1/nqubits)*hamiltonians.Z(nqubits).matrix
                ham = hamiltonians.Hamiltonian(nqubits, m0)

                return ham

            # defining a dummy circuit
            def circuit(nqubits = 1):
                c = Circuit(nqubits = 1)
                c.add(gates.RY(q = 0, theta = 0))
                c.add(gates.RX(q = 0, theta = 0))
                c.add(gates.M(0))

                return c

            # initializing the circuit
            c = circuit(nqubits = 1)

            # some parameters
            test_params = np.random.randn(2)
            c.set_parameters(test_params)

            test_hamiltonian = hamiltonian()

            # running the psr with respect to the two parameters
            grad_0 = stochastic_parameter_shift(circuit=c, hamiltonian=test_hamiltonian, parameter_index=0)
            grad_1 = stochastic_parameter_shift(circuit=c, hamiltonian=test_hamiltonian, parameter_index=1)

    """

    # some raise_error
    if parameter_index > len(circuit.get_parameters()):
        raise_error(ValueError, """This index is out of bounds.""")

    if not isinstance(hamiltonian, AbstractHamiltonian):
        raise_error(
            TypeError,
            "hamiltonian must be a qibo.hamiltonians.Hamiltonian or qibo.hamiltonians.SymbolicHamiltonian object",
        )

    # inheriting hamiltonian's backend
    backend = hamiltonian.backend

    # getting the gate's type
    gate = circuit.associate_gates_with_parameters()[parameter_index]

    # getting the generator_eigenvalue
    generator_eigenval = gate.generator_eigenvalue()

    # defining the shift according to the psr
    s = np.pi / (4 * generator_eigenval)

    # saving original parameters and making a copy
    original = np.asarray(circuit.get_parameters()).copy()
    shifted = original.copy()

    # new circuit
    ancilla_gate = copy.deepcopy(gate)
    ancilla_gate2 = copy.deepcopy(gate)
    circuit.add(ancilla_gate, position=parameter_index)
    circuit.add(ancilla_gate2, position=parameter_index)

    # gradients
    grads = np.zeros(parameter.nparams)

    # forward shift
    shifted = np.insert(shifted, parameter_index, [0, 0])

    for iparam in range(parameter.nparams):
        new_params, scaling = generate_new_stochastic_params(parameter, iparam)
        new_params[1] += s
        shifted[parameter_index : parameter_index + 3] = new_params

        circuit.set_parameters(shifted)

        if nshots is None:
            # forward evaluation
            forward = hamiltonian.expectation(
                backend.execute_circuit(
                    circuit=circuit, initial_state=initial_state
                ).state()
            )

            # backward shift and evaluation
            shifted[parameter_index + 1] -= s * 2
            circuit.set_parameters(shifted)

            backward = hamiltonian.expectation(
                backend.execute_circuit(
                    circuit=circuit, initial_state=initial_state
                ).state()
            )

        # same but using expectation from samples
        else:
            forward = backend.execute_circuit(
                circuit=circuit, initial_state=initial_state, nshots=nshots
            )

            shifted[parameter_index + 1] -= s * 2
            circuit.set_parameters(shifted)

            backward = backend.execute_circuit(
                circuit=circuit, initial_state=initial_state, nshots=nshots
            ).expectation_from_samples(hamiltonian)

        # float() necessary to not return a 0-dim ndarray
        result = float(generator_eigenval * (forward - backward) * scaling)
        grads[iparam] = result

    # cleanup
    circuit.remove(ancilla_gate)
    circuit.remove(ancilla_gate2)
    circuit.set_parameters(original)

    return grads


def finite_differences(
    circuit,
    hamiltonian,
    parameter_index,
    initial_state=None,
    step_size=1e-1,
    nshots=None,
):
    """
    Calculate derivative of the expectation value of `hamiltonian` on the
    final state obtained by executing `circuit` on `initial_state` with
    respect to the variational parameter identified by `parameter_index`
    in the circuit's parameters list. This method can be used only in
    exact simulation mode.

    Args:
        circuit (:class:`qibo.models.circuit.Circuit`): custom quantum circuit.
        hamiltonian (:class:`qibo.hamiltonians.Hamiltonian`): target observable.
            if you want to execute on hardware, a symbolic hamiltonian must be
            provided as follows (example with Pauli Z and ``nqubits=1``):
            ``SymbolicHamiltonian(np.prod([ Z(i) for i in range(1) ]))``.
        parameter_index (int): the index which identifies the target parameter
            in the ``circuit.get_parameters()`` list.
        initial_state (ndarray, optional): initial state on which the circuit
            acts. Default is ``None``.
        step_size (float): step size used to evaluate the finite difference
            (default 1e-7).

    Returns:
        (float): Value of the derivative of the expectation value of the hamiltonian
            with respect to the target variational parameter.
    """

    if parameter_index > len(circuit.get_parameters()):
        raise_error(ValueError, f"""Index {parameter_index} is out of bounds.""")

    if not isinstance(hamiltonian, AbstractHamiltonian):
        raise_error(
            TypeError,
            "hamiltonian must be a qibo.hamiltonians.Hamiltonian or qibo.hamiltonians.SymbolicHamiltonian object",
        )

    backend = hamiltonian.backend

    # parameters copies
    parameters = np.asarray(circuit.get_parameters()).copy()
    shifted = parameters.copy()

    # shift the parameter_index element
    shifted[parameter_index] += step_size
    circuit.set_parameters(shifted)

    if nshots is None:
        # forward evaluation
        forward = hamiltonian.expectation(
            backend.execute_circuit(
                circuit=circuit, initial_state=initial_state
            ).state()
        )

        # backward shift and evaluation
        shifted[parameter_index] -= 2 * step_size
        circuit.set_parameters(shifted)

        backward = hamiltonian.expectation(
            backend.execute_circuit(
                circuit=circuit, initial_state=initial_state
            ).state()
        )

    # same but using expectation from samples
    else:
        forward = backend.execute_circuit(
            circuit=circuit, initial_state=initial_state, nshots=nshots
        ).expectation_from_samples(hamiltonian)

        shifted[parameter_index] -= 2 * step_size
        circuit.set_parameters(shifted)

        backward = backend.execute_circuit(
            circuit=circuit, initial_state=initial_state, nshots=nshots
        ).expectation_from_samples(hamiltonian)

    circuit.set_parameters(parameters)

    result = (forward - backward) / (2 * step_size)

    return result
