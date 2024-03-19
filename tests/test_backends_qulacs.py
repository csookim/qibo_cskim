import random

import pytest

from qibo import gates
from qibo.backends import NumpyBackend, QulacsBackend
from qibo.quantum_info import random_clifford

numpy_bkd = NumpyBackend()


@pytest.mark.parametrize("optimize", [True, False])
def test_qulacs(optimize):
    c = random_clifford(3, backend=numpy_bkd)
    measured_qubits = random.sample([0, 1, 2], 2)
    c.add(gates.M(*measured_qubits))
    qulacs_bkd = QulacsBackend()
    nshots = 1000
    qulacs_res = qulacs_bkd.execute_circuit(c, nshots=nshots, optimize=optimize)
    numpy_res = numpy_bkd.execute_circuit(c, nshots=nshots)
    numpy_bkd.assert_allclose(numpy_res.probabilities(), qulacs_res.probabilities())
    numpy_freq = numpy_res.frequencies(binary=True)
    qulacs_freq = qulacs_res.frequencies(binary=True)
    numpy_freq = [numpy_freq.get(state, 0) / nshots for state in range(8)]
    qulacs_freq = [qulacs_freq.get(state, 0) / nshots for state in range(8)]
    numpy_bkd.assert_allclose(numpy_freq, qulacs_freq, atol=1e-1)
