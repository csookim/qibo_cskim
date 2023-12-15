"""Tests for quantum_info.quantum_networks submodule"""

import numpy as np
import pytest

from qibo import gates
from qibo.quantum_info.quantum_networks import QuantumNetwork
from qibo.quantum_info.random_ensembles import random_density_matrix, random_unitary


def test_errors(backend):
    lamb = float(np.random.rand())
    channel = gates.DepolarizingChannel(0, lamb)
    nqubits = len(channel.target_qubits)
    dims = 2**nqubits
    partition = (dims, dims)
    network = QuantumNetwork(
        channel.to_choi(backend=backend), partition, backend=backend
    )

    state = random_density_matrix(dims, backend=backend)
    network_state = QuantumNetwork(state, (1, 2), backend=backend)

    with pytest.raises(ValueError):
        network.is_hermitian(precision_tol=-1e-8)

    with pytest.raises(ValueError):
        network.is_unital(precision_tol=-1e-8)

    with pytest.raises(ValueError):
        network.is_causal(precision_tol=-1e-8)

    with pytest.raises(TypeError):
        network + 1

    with pytest.raises(ValueError):
        network + network_state


def test_parameters(backend):
    lamb = float(np.random.rand())
    channel = gates.DepolarizingChannel(0, lamb)

    nqubits = len(channel.target_qubits)
    dims = 2**nqubits
    partition = (dims, dims)

    network = QuantumNetwork(
        channel.to_choi(backend=backend), partition, backend=backend
    )

    backend.assert_allclose(network.matrix(backend=backend).shape, (2, 2, 2, 2))
    backend.assert_allclose(network.dims, 4)
    backend.assert_allclose(network.partition, partition)
    backend.assert_allclose(network.system_output, (False, True))

    assert network.is_causal()
    assert network.is_unital()
    assert network.is_hermitian()
    assert network.is_positive_semidefinite()


def test_with_states(backend):
    nqubits = 1
    dims = 2**nqubits

    state = random_density_matrix(dims, backend=backend)
    network_state = QuantumNetwork(state, (1, 2), backend=backend)

    lamb = float(np.random.rand())
    channel = gates.DepolarizingChannel(0, lamb)
    network_channel = QuantumNetwork(
        channel.to_choi(backend=backend), (dims, dims), backend=backend
    )

    state_output = channel.apply_density_matrix(backend, state, nqubits)
    state_output_network = network_channel.apply(state)
    state_output_link = network_state.link_product(
        network_channel, subscripts="ij,jk -> ik"
    )

    backend.assert_allclose(state_output_network, state_output)
    backend.assert_allclose(
        state_output_link.matrix(backend=backend).reshape((dims, dims)), state_output
    )

    assert network_state.is_hermitian()
    assert network_state.is_positive_semidefinite()


def test_with_unitaries(backend):
    nqubits = 2
    dims = 2**nqubits

    unitary_1 = random_unitary(dims, backend=backend)
    unitary_2 = random_unitary(dims, backend=backend)

    network_1 = QuantumNetwork(unitary_1, (dims, dims), is_pure=True, backend=backend)
    network_2 = QuantumNetwork(unitary_2, (dims, dims), is_pure=True, backend=backend)
    network_3 = QuantumNetwork(
        unitary_2 @ unitary_1, (dims, dims), is_pure=True, backend=backend
    )

    subscript = "ij,jk -> ik"
    backend.assert_allclose(
        network_1.link_product(network_2, subscript).matrix(backend=backend),
        network_3._full(),
    )
