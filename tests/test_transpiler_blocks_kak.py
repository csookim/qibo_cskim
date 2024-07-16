import numpy as np
from qibo import gates
from qibo.transpiler.blocks import Block
import pytest

@pytest.mark.parametrize("qubits", [(0, 1), (2, 1)])
def test_block_kak(qubits):
    """
    Test the KAK decomposition of a block.
    """

    # Create a block with H, S, CNOT, TDG gates
    block = Block(
        qubits=qubits,
        # No error
        gates = [gates.H(0), gates.S(1), gates.TDG(0), gates.CNOT(0, 1), gates.CNOT(1, 0)],
        
        # error
        # gates = [gates.H(0), gates.S(1), gates.CNOT(1, 0), gates.TDG(0), gates.CNOT(0, 1), gates.CNOT(1, 0)],
    )

    # Obtain the unitary matrix of the block
    U = block.unitary()

    # Perform the KAK decomposition
    A0, A1, K, B0, B1 = block.kak_decompose()

    # Reassemble the decomposed matrices
    orig = (np.kron(A0, A1) @ heisenberg_unitary(K) @ np.kron(B0.conj().T, B1.conj().T))

    # Check that the original and decomposed matrices are equal
    assert ( np.linalg.norm(orig - U) < 1e-8 )

def heisenberg_unitary(k):
    from scipy.linalg import expm

    PAULI_X = np.array([[0, 1], [1, 0]])
    PAULI_Y = np.array([[0, -1j], [1j, 0]])
    PAULI_Z = np.array([[1, 0], [0, -1]])

    PXX = np.kron(PAULI_X, PAULI_X)
    PYY = np.kron(PAULI_Y, PAULI_Y)
    PZZ = np.kron(PAULI_Z, PAULI_Z)

    H = k[0] * np.eye(4) + k[1] * PXX + k[2] * PYY + k[3] * PZZ
    return expm(1j * H)