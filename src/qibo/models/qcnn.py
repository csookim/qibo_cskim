import numpy as np

import qibo
from qibo import gates, matrices
from qibo.models import Circuit


class QuantumCNN:
    def __init__(self, nqubits, nlayers, nclasses=2, params=None):
        """
        Class for a multi-task variational quantum classifier
        Args:
            nclasses: int number of classes to be classified. Default setting of 2 (phases).
            nqubits: int number of qubits employed in the quantum circuit
        """
        self.nclasses = nclasses
        self.nqubits = nqubits
        self.nlayers = nlayers

        self.nparams_conv = 15
        self.nparams_pool = 6
        self.nparams_layer = self.nparams_conv + self.nparams_pool
        self.measured_qubits = int(np.ceil(np.log2(self.nclasses)))

        if self.nqubits <= 1:
            raise ValueError("nqubits must be larger than 1")

        self._circuit = self.ansatz(nlayers, params=params)

    def quantum_conv_circuit(self, bits, symbols):
        c = Circuit(self.nqubits)
        for first, second in zip(bits[0::2], bits[1::2]):
            c += self.two_qubit_unitary([first, second], symbols)

        # check that there are more than 2 qubits to prevent double conv
        if len(bits) > 2:
            for first, second in zip(bits[1::2], bits[2::2] + [bits[0]]):
                c += self.two_qubit_unitary([first, second], symbols)
        return c

    def quantum_pool_circuit(self, source_bits, sink_bits, symbols):
        c = Circuit(self.nqubits)
        for source, sink in zip(source_bits, sink_bits):
            c += self.two_qubit_pool(source, sink, symbols)
        return c

    def ansatz(self, nlayers, params=None):
        """
        Args:
            theta: list or numpy.array with the angles to be used in the circuit
            nlayers: int number of layers of the varitional circuit ansatz
        Returns:
            Circuit implementing the QCNN variational ansatz
        """

        nparams_conv = self.nparams_conv
        nparams_layer = self.nparams_layer

        if params is not None:
            symbols = params
        else:
            symbols = [0 for _ in range(nlayers * nparams_layer)]

        nbits = self.nqubits

        qubits = [_ for _ in range(nbits)]
        c = Circuit(self.nqubits)
        for layer in range(nlayers):
            conv_start = int(nbits - nbits / (2**layer))
            pool_start = int(nbits - nbits / (2 ** (layer + 1)))
            param_start = layer * nparams_layer
            c += self.quantum_conv_circuit(
                qubits[conv_start:], symbols[param_start : param_start + nparams_conv]
            )
            c += self.quantum_pool_circuit(
                qubits[conv_start:pool_start],
                qubits[pool_start:],
                symbols[param_start + nparams_conv : param_start + nparams_layer],
            )

        # Measurements
        c.add(gates.M(*[nbits - 1 - i for i in range(self.measured_qubits)]))

        return c

    def one_qubit_unitary(self, bit, symbols):
        """Make a circuit enacting a rotation of the bloch sphere about the X,
        Y and Z axis, that depends on the values in `symbols`.
        Symbols should be a list of length 3.
        """
        c = Circuit(self.nqubits)
        c.add(gates.RX(bit, symbols[0]))
        c.add(gates.RY(bit, symbols[1]))
        c.add(gates.RZ(bit, symbols[2]))

        return c

    def two_qubit_unitary(self, bits, symbols):
        """Make a circuit that creates an arbitrary two qubit unitary.
        Symbols should be a list of length 15.
        """
        c = Circuit(self.nqubits)
        c += self.one_qubit_unitary(bits[0], symbols[0:3])
        c += self.one_qubit_unitary(bits[1], symbols[3:6])
        c.add(gates.RZZ(bits[0], bits[1], symbols[6]))
        c.add(gates.RYY(bits[0], bits[1], symbols[7]))
        c.add(gates.RXX(bits[0], bits[1], symbols[8]))

        c += self.one_qubit_unitary(bits[0], symbols[9:12])
        c += self.one_qubit_unitary(bits[1], symbols[12:])

        return c

    def two_qubit_pool(self, source_qubit, sink_qubit, symbols):
        """Make a circuit to do a parameterized 'pooling' operation, which
        attempts to reduce entanglement down from two qubits to just one.
        Symbols should be a list of 6 params.
        """
        pool_circuit = Circuit(self.nqubits)
        sink_basis_selector = self.one_qubit_unitary(sink_qubit, symbols[0:3])
        source_basis_selector = self.one_qubit_unitary(source_qubit, symbols[3:6])
        pool_circuit += sink_basis_selector
        pool_circuit += source_basis_selector
        pool_circuit.add(gates.CNOT(source_qubit, sink_qubit))
        pool_circuit += sink_basis_selector.invert()

        return pool_circuit

    def set_circuit_params(self, angles):

        params = list(angles)
        expanded_params = []
        nbits = self.nqubits
        for layer in range(self.nlayers):
            nleft = nbits / (2**layer)
            param_start = layer * self.nparams_layer
            conv_params = params[param_start : param_start + self.nparams_conv]
            pool_params = params[
                param_start + self.nparams_conv : param_start + self.nparams_layer
            ]
            pool_params += [-pool_params[2], -pool_params[1], -pool_params[0]]
            expanded_params += conv_params * int(nleft if nleft > 2 else 1)
            expanded_params += pool_params * int(nleft / 2)

        self._circuit.set_parameters(expanded_params)

    def Classifier_circuit(self, theta):
        """
        Args:
            theta: list or numpy.array with the biases and the angles to be used in the circuit
            nlayers: int number of layers of the varitional circuit ansatz
            RY: if True, parameterized Rx,Rz,Rx gates are used in the circuit
                if False, parameterized Ry gates are used in the circuit (default=False)
        Returns:
            Circuit implementing the variational ansatz for angles "theta"
        """
        bias = np.array(theta[0 : self.measured_qubits])
        angles = theta[self.measured_qubits :]

        self.set_circuit_params(angles)
        return self._circuit

    def Predictions(self, circuit, theta, init_state, nshots=10000):
        """
        Args:
            theta: list or numpy.array with the biases to be used in the circuit
            init_state: numpy.array with the quantum state to be classified
            nshots: int number of runs of the circuit during the sampling process (default=10000)
        Returns:
            numpy.array() with predictions for each qubit, for the initial state
        """
        bias = np.array(theta[0 : self.measured_qubits])
        circuit_exec = circuit(init_state, nshots)
        result = circuit_exec.frequencies(binary=False)
        prediction = np.zeros(self.measured_qubits)

        for qubit in range(self.measured_qubits):
            for clase in range(self.nclasses):
                binary = bin(clase)[2:].zfill(self.measured_qubits)
                prediction[qubit] += result[clase] * (1 - 2 * int(binary[-qubit - 1]))

        return prediction / nshots + bias

    def square_loss(self, labels, predictions):
        """
        Args:
            labels: list or numpy.array with the qubit labels of the quantum states to be classified
            predictions: list or numpy.array with the qubit predictions for the quantum states to be classified
        Returns:
            numpy.float32 with the value of the square-loss function
        """
        loss = 0
        for l, p in zip(labels, predictions):
            for qubit in range(self.measured_qubits):
                loss += (l[qubit] - p[qubit]) ** 2

        return loss / len(labels)

    def Cost_function(self, theta, data=None, labels=None, nshots=10000):
        """
        Args:
            theta: list or numpy.array with the biases and the angles to be used in the circuit
            nlayers: int number of layers of the varitional circuit ansatz
            data: numpy.array data[page][word]  (this is an array of kets)
            labels: list or numpy.array with the labels of the quantum states to be classified
            nshots: int number of runs of the circuit during the sampling process (default=10000)
        Returns:
            numpy.float32 with the value of the square-loss function
        """
        circ = self.Classifier_circuit(theta)

        Bias = np.array(theta[0 : self.measured_qubits])
        predictions = np.zeros(shape=(len(data), self.measured_qubits))

        for i, text in enumerate(data):
            predictions[i] = self.Predictions(circ, Bias, text, nshots)

        s = self.square_loss(labels, predictions)

        return s

    def minimize(
        self, init_theta, data=None, labels=None, nshots=10000, method="Powell"
    ):
        """
        Args:
            theta: list or numpy.array with the angles to be used in the circuit
            nlayers: int number of layers of the varitional ansatz
            init_state: numpy.array with the quantum state to be Schmidt-decomposed
            nshots: int number of runs of the circuit during the sampling process (default=10000)
            RY: if True, parameterized Rx,Rz,Rx gates are used in the circuit
                if False, parameterized Ry gates are used in the circuit (default=True)
            method: str 'classical optimizer for the minimization'. All methods from scipy.optimize.minmize are suported (default='Powell')
        Returns:
            numpy.float64 with value of the minimum found, numpy.ndarray with the optimal angles
        """
        from scipy.optimize import minimize

        result = minimize(
            self.Cost_function, init_theta, args=(data, labels, nshots), method=method
        )
        loss = result.fun
        optimal_angles = result.x

        self._optimal_angles = optimal_angles

        self.set_circuit_params(optimal_angles[self.measured_qubits :])
        return loss, optimal_angles

    def Accuracy(self, labels, predictions, sign=True, tolerance=1e-2):
        """
        Args:
            labels: numpy.array with the labels of the quantum states to be classified
            predictions: numpy.array with the predictions for the quantum states classified
            sign: if True, labels = np.sign(labels) and predictions = np.sign(predictions) (default=True)
            tolerance: float tolerance level to consider a prediction correct (default=1e-2)
        Returns:
            float with the proportion of states classified successfully
        """
        if sign == True:
            labels = [np.sign(label) for label in labels]
            predictions = [np.sign(prediction) for prediction in predictions]

        accur = 0
        for l, p in zip(labels, predictions):
            if np.allclose(l, p, rtol=0.0, atol=tolerance):
                accur += 1

        accur = accur / len(labels)

        return accur

    def predict(self, init_state, nshots=10000):
        return self.Predictions(
            self._circuit, self._optimal_angles, init_state, nshots=nshots
        )
