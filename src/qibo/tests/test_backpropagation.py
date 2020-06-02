import numpy as np
import pytest
from qibo.models import Circuit
from qibo.tensorflow import gates

_BACKENDS = ["DefaultEinsum", "MatmulEinsum"]


@pytest.mark.parametrize("backend", _BACKENDS)
def test_variable_backpropagation(backend):
    """Check that backpropagation works when using `tf.Variable` parameters."""
    import tensorflow as tf
    from qibo.config import DTYPE
    theta = tf.Variable(0.1234, dtype=DTYPE)

    # TODO: Fix parametrized gates so that `Circuit` can be defined outside
    # of the gradient tape
    with tf.GradientTape() as tape:
        c = Circuit(1)
        c.add(gates.X(0).with_backend(backend))
        c.add(gates.RZ(0, theta).with_backend(backend))
        loss = tf.math.real(c()[-1])
    grad = tape.gradient(loss, theta)

    target_loss = np.cos(theta.numpy() / 2.0)
    np.testing.assert_allclose(loss.numpy(), target_loss)

    target_grad = - np.sin(theta.numpy() / 2.0) / 2.0
    np.testing.assert_allclose(grad.numpy(), target_grad)


@pytest.mark.parametrize("backend", _BACKENDS)
def test_two_variables_backpropagation(backend):
    """Check that backpropagation works when using `tf.Variable` parameters."""
    import tensorflow as tf
    from qibo.config import DTYPE
    theta = tf.Variable([0.1234, 0.4321], dtype=DTYPE)

    # TODO: Fix parametrized gates so that `Circuit` can be defined outside
    # of the gradient tape
    with tf.GradientTape() as tape:
        c = Circuit(2)
        c.add(gates.RX(0, theta[0]).with_backend(backend))
        c.add(gates.RY(1, theta[1]).with_backend(backend))
        loss = tf.math.real(c()[0])
    grad = tape.gradient(loss, theta)

    t = np.array([0.1234, 0.4321]) / 2.0
    target_loss = np.cos(t[0]) * np.cos(t[1])
    np.testing.assert_allclose(loss.numpy(), target_loss)

    target_grad1 = - np.sin(t[0]) * np.cos(t[1])
    target_grad2 = - np.cos(t[0]) * np.sin(t[1])
    target_grad = np.array([target_grad1, target_grad2]) / 2.0
    np.testing.assert_allclose(grad.numpy(), target_grad)