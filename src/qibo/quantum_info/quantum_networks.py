"""Module defining the `QuantumNetwork` class and adjacent functions."""

from functools import reduce
from logging import warning
from numbers import Number
from operator import mul
from typing import List, Optional, Tuple, Union

import numpy as np

from qibo.backends import _check_backend
from qibo.config import raise_error


class QuantumNetwork:
    """This class stores the representation of the quantum network as a tensor.
    This is a unique representation of the quantum network.

    A minimum quantum network is a quantum channel, which is a quantum network of the form
    :math:`J[n \\to m]`, where :math:`n` is the dimension of the input system ,
    and :math:`m` is the dimension of the output system.
    A quantum state is a quantum network of the form :math:`J: 1 \\to n`,
    such that the input system is trivial.
    An observable is a quantum network of the form :math:`J: n \\to 1`,
    such that the output system is trivial.

    A quantum network may contain multiple input and output systems.
    For example, a "quantum comb" is a quantum network of the form :math:`J: n', n \\to m, m'`,
    which convert a quantum channel of the form :math:`J: n \\to m`
    to a quantum channel of the form :math:`J: n' \\to m'`.

    Args:
        tensor (ndarray): input Choi operator.
        partition (List[int] or Tuple[int]): partition of ``tensor``.
        system_input (List[bool] or Tuple[bool], optional): mask on the output system of the
            Choi operator. If ``None``, defaults to
            ``(True,False,True,False,...)``, where ``len(system_input)=len(partition)``.
            Defaults to ``None``.
        pure (bool, optional): ``True`` when ``tensor`` is a "pure" representation (e.g. a pure
            state, a unitary operator, etc.), ``False`` otherwise. Defaults to ``False``.
        backend (:class:`qibo.backends.abstract.Backend`, optional): Backend to be used in
            calculations. If ``None``, defaults to :class:`qibo.backends.GlobalBackend`.
            Defaults to ``None``.
    """

    def __init__(
        self,
        tensor,
        partition: Optional[Union[List[int], Tuple[int]]] = None,
        system_input: Optional[Union[List[bool], Tuple[bool]]] = None,
        pure: bool = False,
        backend=None,
    ):
        self._run_checks(partition, system_input, pure)

        self._tensor = tensor
        self.partition = partition
        self.system_input = system_input
        self._pure = pure
        self._backend = backend

        self._set_parameters()

        if len(self.partition) > 0:
            self.dims = reduce(
                mul, self.partition
            )  # should be after `_set_parameters` to ensure `self.partition` is not `None`
        else:
            self.dims = 1

    @staticmethod
    def _order_tensor2operator(n: int):
        order = list(range(0, n * 2, 2)) + list(range(1, n * 2, 2))
        return order

    @staticmethod
    def _order_operator2tensor(n: int):
        order = list(sum(zip(list(range(0, n)), list(range(n, n * 2))), ()))
        return order

    @classmethod
    def _operator2tensor(cls, operator, partition: List[int], system_input: List[bool]):
        n = len(partition)
        order = cls._order_operator2tensor(n)
        try:
            return (
                operator.reshape(list(partition) * 2)
                .transpose(order)
                .reshape([dim**2 for dim in partition])
            )
        except:
            raise_error(
                ValueError,
                "``partition`` does not match the shape of the input matrix. "
                + f"Cannot reshape matrix of size {operator.shape} to partition {partition}",
            )

    @classmethod
    def from_nparray(
        cls,
        arr: np.ndarray,
        partition: Optional[Union[List[int], Tuple[int]]] = None,
        system_input: Optional[Union[List[bool], Tuple[bool]]] = None,
        pure: bool = False,
        backend=None,
    ):
        """Construct a :class:`qibo.quantum_info.quantum_networks.QuantumNetwork` object from a numpy array.
        This method converts a Choi operator to the internal representation of :class:`qibo.quantum_info.quantum_networks.QuantumNetwork`.

        The input array can be a pure state, a Choi operator, a unitary operator, etc.

        Args:
            arr (ndarray): input numpy array.
            partition (List[int] or Tuple[int], optional): partition of ``arr``. If ``None``,
                defaults to the shape of ``arr``. Defaults to ``None``.
            system_input (List[bool] or Tuple[bool], optional): mask on the input system of the
                Choi operator. If ``None``, defaults to
                ``(True,False,True,False...)``, where ``len(system_input)=len(partition)``.
                Defaults to ``None``.
            pure (bool, optional): ``True`` when ``arr`` is a "pure" representation (e.g. a pure
                state, a unitary operator, etc.), ``False`` otherwise. Defaults to ``False``.
            backend (:class:`qibo.backends.abstract.Backend`, optional): Backend to be used in
                calculations. If ``None``, defaults to :class:`qibo.backends.GlobalBackend`.
                Defaults to ``None``.

        Returns:
            :class:`qibo.quantum_info.quantum_networks.QuantumNetwork`:
        """

        if pure:
            if partition is None:
                partition = arr.shape
                tensor = arr
            else:
                try:
                    tensor = arr.reshape(partition)
                except:
                    raise_error(
                        ValueError,
                        "``partition`` does not match the shape of the input matrix. "
                        + f"Cannot reshape matrix of size {arr.shape} to partition {partition}",
                    )
        else:
            # check if arr is a valid choi operator
            len_sys = len(arr.shape)
            if (len_sys % 2 != 0) or (
                arr.shape[: len_sys // 2] != arr.shape[len_sys // 2 :]
            ):
                raise_error(
                    ValueError,
                    "The opertor must be a square operator where the first half of the shape is the same as the second half of the shape. "
                    + f"However, the shape of the input is {arr.shape}. "
                    + "If the input is pure, set `pure=True`.",
                )

            if partition is None:
                partition = arr.shape[: len_sys // 2]

            tensor = cls._operator2tensor(arr, partition, system_input)

        return cls(
            tensor,
            partition=partition,
            system_input=system_input,
            pure=pure,
            backend=backend,
        )

    def operator(self, backend=None, full=False):
        """Returns the Choi operator of the quantum network.
        The shape of the returned operator is :math:`(*self.partition, *self.partition)`.

        Args:
            backend (:class:`qibo.backends.abstract.Backend`, optional): Backend to be used
                to return the Choi operator. If ``None``, defaults to the backend defined
                when initializing the :class:`qibo.quantum_info.quantum_networks.QuantumNetwork`
                object. Defaults to ``None``.
            full (bool, optional): If this is ``False``, and the network is pure, the method
                will only return the eigenvector (unique when the network is pure).
                If ``True``, returns the full tensor of the quantum network. Defaults to ``False``.

        Returns:
            ndarray: Choi operator of the quantum network.
        """
        if backend is None:  # pragma: no cover
            backend = self._backend

        if self.is_pure() and not full:
            return backend.cast(self._tensor, dtype=self._tensor.dtype)

        if self.is_pure():
            tensor = self.full(backend)
        else:
            tensor = self._tensor

        n = len(self.partition)
        order = self._order_tensor2operator(n)

        operator = tensor.reshape(np.repeat(self.partition, 2)).transpose(order)

        return backend.cast(operator, dtype=self._tensor.dtype)

    def matrix(self, backend=None):
        """Returns the Choi operator of the quantum network in the matrix form.
        The shape of the returned operator is :math:`(self.dims, self.dims)`.

        Args:
            backend (:class:`qibo.backends.abstract.Backend`, optional): Backend to be used
                to return the Choi operator. If ``None``, defaults to the backend defined
                when initializing the :class:`qibo.quantum_info.quantum_networks.QuantumNetwork`
                object. Defaults to ``None``.

        Returns:
            ndarray: Choi operator of the quantum network.
        """
        return self.operator(backend, full=True).reshape((self.dims, self.dims))

    def is_pure(self):
        """Returns bool indicading if the Choi operator of the network is pure."""
        return self._pure

    def is_hermitian(
        self, order: Optional[Union[int, str]] = None, precision_tol: float = 1e-8
    ):
        """Returns bool indicating if the Choi operator :math:`\\mathcal{J}` of the network is Hermitian.

        Hermicity is calculated as distance between :math:`\\mathcal{J}` and
        :math:`\\mathcal{J}^{\\dagger}` with respect to a given norm.
        Default is the ``Hilbert-Schmidt`` norm (also known as ``Frobenius`` norm).

        For specifications on the other  possible values of the
        parameter ``order`` for the ``tensorflow`` backend, please refer to
        `tensorflow.norm <https://www.tensorflow.org/api_docs/python/tf/norm>`_.
        For all other backends, please refer to
        `numpy.linalg.norm <https://numpy.org/doc/stable/reference/generated/numpy.linalg.norm.html>`_.

        Args:
            order (str or int, optional): order of the norm. Defaults to ``None``.
            precision_tol (float, optional): threshold :math:`\\epsilon` that defines if
                Choi operator of the network is :math:`\\epsilon`-close to Hermicity in
                the norm given by ``order``. Defaults to :math:`10^{-8}`.

        Returns:
            bool: Hermiticity condition.
        """
        if precision_tol < 0.0:
            raise_error(
                ValueError,
                f"``precision_tol`` must be non-negative float, but it is {precision_tol}",
            )

        if order is None and self._backend.__class__.__name__ == "TensorflowBackend":
            order = "euclidean"

        if self.is_pure():  # if the input is pure, it is always hermitian
            return True

        reshaped = self._backend.cast(
            self.matrix(),
            dtype=self._tensor.dtype,
        )
        mat_diff = self._backend.cast(
            np.transpose(np.conj(reshaped)) - reshaped, dtype=reshaped.dtype
        )
        norm = self._backend.calculate_norm_density_matrix(mat_diff, order=order)

        return float(norm) <= precision_tol

    def is_positive_semidefinite(self, precision_tol: float = 1e-8):
        """Returns bool indicating if Choi operator :math:`\\mathcal{J}` of the network is positive-semidefinite.

        Args:
            precision_tol (float, optional): threshold value used to check if eigenvalues of
                the Choi operator :math:`\\mathcal{J}` are such that
                :math:`\\textup{eigenvalues}(\\mathcal{J}) >= - \\textup{precision_tol}`.
                Note that this parameter can be set to negative values.
                Defaults to :math:`0.0`.

        Returns:
            bool: Positive-semidefinite condition.
        """
        if precision_tol < 0.0:
            raise_error(
                ValueError,
                f"``precision_tol`` must be non-negative float, but it is {precision_tol}",
            )

        if self.is_pure():  # if the input is pure, it is always positive semidefinite
            return True

        reshaped = self._backend.cast(
            self.matrix(),
            dtype=self._tensor.dtype,
        )

        if self.is_hermitian():
            eigenvalues = np.linalg.eigvalsh(reshaped)
        else:
            return False

        return all(eigenvalue >= -precision_tol for eigenvalue in eigenvalues)

    def link_product(self, subscripts: str, second_network):
        """Link product between two quantum networks.

        The link product is not commutative. Here, we assume that
        :math:`A.\\textup{link_product}(B)` means "applying :math:`B` to :math:`A`".
        However, the ``link_product`` is associative, so we override the `@` operation
        in order to simplify notation.

        Args:
            subscripts (str, optional): Specifies the subscript for summation using
                the Einstein summation convention. For more details, please refer to
                `numpy.einsum <https://numpy.org/doc/stable/reference/generated/numpy.einsum.html>`_.
            second_network (:class:`qibo.quantum_info.quantum_networks.QuantumNetwork`): Quantum
                network to be applied to the original network.

        Returns:
            :class:`qibo.quantum_info.quantum_networks.QuantumNetwork`: Quantum network resulting
                from the link product between two quantum networks.
        """

        return link_product(subscripts, self, second_network, backend=self._backend)

    def copy(self):
        """Returns a copy of the :class:`qibo.quantum_info.quantum_networks.QuantumNetwork` object."""
        return self.__class__(
            np.copy(self._tensor),
            partition=self.partition,
            system_input=self.system_input,
            pure=self._pure,
            backend=self._backend,
        )

    def conj(self):
        """Returns the conjugate of the quantum network."""
        return self.__class__(
            np.conj(self._tensor),
            partition=self.partition,
            system_input=self.system_input,
            pure=self._pure,
            backend=self._backend,
        )

    def __add__(self, second_network):
        """Add two Quantum Networks by adding their Choi operators.

        This operation always returns a non-pure Quantum Network.

        Args:
            second_network (:class:`qibo.quantum_info.quantum_networks.QuantumNetwork`): Quantum
                network to be added to the original network.

        Returns:
            (:class:`qibo.quantum_info.quantum_networks.QuantumNetwork`): Quantum network resulting
                from the summation of two Choi operators.
        """
        if not isinstance(second_network, QuantumNetwork):
            raise_error(
                TypeError,
                "It is not possible to add a object of type ``QuantumNetwork`` "
                + f"and and object of type ``{type(second_network)}``.",
            )

        if self.full().shape != second_network.full().shape:
            raise_error(
                ValueError,
                f"The Choi operators must have the same shape, but {self.full().shape} != "
                + f"{second_network.full().shape}.",
            )

        if self.system_input != second_network.system_input:
            raise_error(ValueError, "The networks must have the same input systems.")

        new_first_tensor = self.full()
        new_second_tensor = second_network.full()

        return QuantumNetwork(
            new_first_tensor + new_second_tensor,
            self.partition,
            self.system_input,
            pure=False,
            backend=self._backend,
        )

    def __mul__(self, number: Union[float, int, Number]):
        """Returns quantum network with its Choi operator multiplied by a scalar.

        If the quantum network is pure and ``number > 0.0``, the method returns a pure quantum
        network with its Choi operator multiplied by the square root of ``number``.
        This is equivalent to multiplying `self.to_full()` by the ``number``.
        Otherwise, this method will return a full quantum network.

        Args:
            number (float or int): scalar to multiply the Choi operator of the network with.

        Returns:
            :class:`qibo.quantum_info.quantum_networks.QuantumNetwork`: Quantum network with its
                Choi operator multiplied by ``number``.
        """
        if not isinstance(number, Number):
            raise_error(
                TypeError,
                "It is not possible to multiply a ``QuantumNetwork`` by a non-scalar.",
            )

        if self.is_pure() and number > 0.0:
            return QuantumNetwork(
                np.sqrt(number) * self._tensor,
                partition=self.partition,
                system_input=self.system_input,
                pure=True,
                backend=self._backend,
            )

        tensor = self.full()

        return QuantumNetwork(
            number * tensor,
            partition=self.partition,
            system_input=self.system_input,
            pure=False,
            backend=self._backend,
        )

    def __rmul__(self, number: Union[float, int, Number]):
        """"""
        return self.__mul__(number)

    def __truediv__(self, number: Union[float, int, Number]):
        """Returns quantum network with its Choi operator divided by a scalar.

        If the quantum network is pure and ``number > 0.0``, the method returns a pure quantum
        network with its Choi operator divided by the square root of ``number``.
        This is equivalent to dividing `self.to_full()` by the ``number``.
        Otherwise, this method will return a full quantum network.

        Args:
            number (float or int): scalar to divide the Choi operator of the network with.

        Returns:
            :class:`qibo.quantum_info.quantum_networks.QuantumNetwork`: Quantum network with its
                Choi operator divided by ``number``.
        """
        if not isinstance(number, Number):
            raise_error(
                TypeError,
                "It is not possible to divide a ``QuantumNetwork`` by a non-scalar.",
            )

        number = np.sqrt(number) if self.is_pure() and number > 0.0 else number

        return QuantumNetwork(
            self._tensor / number,
            partition=self.partition,
            system_input=self.system_input,
            pure=self.is_pure(),
            backend=self._backend,
        )

    def __matmul__(self, second_network):
        """Defines matrix multiplication between two ``QuantumNetwork`` objects.

        If ``self.partition == second_network.partition in [2, 4]``, this method is overwritten by
        :meth:`qibo.quantum_info.quantum_networks.QuantumNetwork.link_product`.

        Args:
            second_network (:class:`qibo.quantum_info.quantum_networks.QuantumNetwork`):

        Returns:
            :class:`qibo.quantum_info.quantum_networks.QuantumNetwork`: Quantum network resulting
                from the link product operation.
        """
        if not isinstance(second_network, QuantumNetwork):
            raise_error(
                TypeError,
                "It is not possible to implement matrix multiplication of a "
                + "``QuantumNetwork`` by a non-``QuantumNetwork``.",
            )

        if len(self.partition) == 2:  # `self` is a channel
            if len(second_network.partition) != 2:
                raise_error(
                    ValueError,
                    f"`QuantumNetwork {second_network} is assumed to be a channel, but it is not. "
                    + "Use `link_product` method to specify the subscript.",
                )
            if self.partition[1] != second_network.partition[0]:
                raise_error(
                    ValueError,
                    "partitions of the networks do not match: "
                    + f"{self.partition[1]} != {second_network.partition[0]}.",
                )

            subscripts = "jk,kl -> jl"

        elif len(self.partition) == 4:  # `self` is a super-channel
            if len(second_network.partition) != 2:
                raise_error(
                    ValueError,
                    f"`QuantumNetwork {second_network} is assumed to be a channel, but it is not. "
                    + "Use `link_product` method to specify the subscript.",
                )
            if self.partition[1] != second_network.partition[0]:
                raise_error(
                    ValueError,
                    "Systems of the channel do not match the super-channel: "
                    + f"{self.partition[1], self.partition[2]} != "
                    + f"{second_network.partition[0],second_network.partition[1]}.",
                )

            subscripts = "jklm,kl -> jm"
        else:
            raise_error(
                NotImplementedError,
                "`partitions` do not match any implemented pattern``. "
                + "Use `link_product` method to specify the subscript.",
            )

        return self.link_product(subscripts, second_network)

    def __str__(self):
        """Method to define how to print relevant information of the quantum network."""
        systems = []

        for i, dim in enumerate(self.partition):
            if self.system_input[i]:
                systems.append(f"┍{dim}┑")
            else:
                systems.append(f"┕{dim}┙")

        return f"J[{', '.join(systems)}]"

    def _run_checks(self, partition, system_input, pure):
        """Checks if all inputs are correct in type and value."""
        if not isinstance(partition, (list, tuple)):
            raise_error(
                TypeError,
                "``partition`` must be type ``tuple`` or ``list``, "
                + f"but it is type ``{type(partition)}``.",
            )

        if any(not isinstance(party, int) for party in partition):
            raise_error(
                ValueError,
                "``partition`` must be a ``tuple`` or ``list`` of positive integers, "
                + "but contains non-integers.",
            )

        if any(party <= 0 for party in partition):
            raise_error(
                ValueError,
                "``partition`` must be a ``tuple`` or ``list`` of positive integers, "
                + "but contains non-positive integers.",
            )

        if system_input is not None and len(system_input) != len(partition):
            raise_error(
                ValueError,
                "``len(system_input)`` must be the same as ``len(partition)``, "
                + f"but {len(system_input)} != {len(partition)}.",
            )

        if not isinstance(pure, bool):
            raise_error(
                TypeError,
                f"``pure`` must be type ``bool``, but it is type ``{type(pure)}``.",
            )

    @staticmethod
    def _check_system_input(system_input, partition) -> Tuple[bool]:
        """
        If `system_input` not defined, assume the network follows the order of a quantum Comb.
        """

        if system_input is None:
            system_input = [
                False,
            ] * len(partition)
            for k in range(len(partition) // 2):
                system_input[k * 2] = True
        return tuple(system_input)

    def _set_parameters(self):
        """Standarize the parameters."""
        self._backend = _check_backend(self._backend)

        self.partition = tuple(self.partition)

        self.system_input = self._check_system_input(self.system_input, self.partition)

        try:
            if self._pure:
                self._tensor = np.reshape(self._tensor, self.partition)
            else:
                matrix_partition = [d**2 for d in self.partition]
                self._tensor = np.reshape(self._tensor, matrix_partition)
        except:
            raise_error(
                ValueError,
                "``partition`` does not match the shape of the input matrix. "
                + f"Cannot reshape matrix of size {self._tensor.shape} to partition {self.partition}",
            )

    def full(self, backend=None, update=False):
        """Convert the internal representation to the full tensor of the network.

        Returns:
            ndarray: The full reprentation of the quantum network.
        """
        if backend is None:  # pragma: no cover
            backend = self._backend
        tensor = np.copy(self._tensor)

        if self.is_pure():
            """Reshapes input matrix based on purity."""
            tensor.reshape([self.dims])
            tensor = np.tensordot(tensor, np.conj(tensor), axes=0)
            tensor = self._operator2tensor(tensor, self.partition, self.system_input)

            if update:
                self._tensor = tensor
                self._pure = False

        return tensor


class QuantumComb(QuantumNetwork):
    """Quantum comb is a quantum network such that the systems follows a sequential order.
    It is also called the 'non-Markovian quantum process' in many literatures.

    A quantum channel is a special case of quantum comb, where there are only one input
    system and one output system.

    Args:
        tensor (ndarray): the tensor representations of the quantum Comb.
        partition (List[int] or Tuple[int]): partition of ``matrix``.
        system_input (List[bool] or Tuple[bool], optional): mask on the input system of the
            Choi operator. If ``None``, defaults to
            ``(True,False,True,False,...)``, where ``len(system_input)=len(partition)``.
            Defaults to ``None``.
        pure (bool, optional): ``True`` when ``tensor`` is a "pure" representation (e.g. a pure
            state, a unitary operator, etc.), ``False`` otherwise. Defaults to ``False``.
        backend (:class:`qibo.backends.abstract.Backend`, optional): Backend to be used in
            calculations. If ``None``, defaults to :class:`qibo.backends.GlobalBackend`.
            Defaults to ``None``.
    """

    def __init__(
        self,
        tensor,
        partition: Optional[Union[List[int], Tuple[int]]] = None,
        *,
        system_input: Optional[Union[List[bool], Tuple[bool]]] = None,
        pure: bool = False,
        backend=None,
    ):
        if partition == None:
            if pure:
                partition = tensor.shape
            else:
                partition = (int(np.sqrt(d)) for d in tensor.shape)
        if len(partition) % 2 != 0:
            raise_error(
                ValueError,
                "A quantum comb should only contain equal number of input and output systems. "
                + "For general quantum networks, one should use the ``QuantumNetwork`` class.",
            )
        if system_input is not None:
            warning("system_input is ignored for QuantumComb")

        super().__init__(
            tensor, partition, [True, False] * (len(partition) // 2), pure, backend
        )

    def is_causal(
        self, order: Optional[Union[int, str]] = None, precision_tol: float = 1e-8
    ):
        """Returns bool indicating if the Choi operator :math:`\\mathcal{J}` of the network satisfies the causal order condition.

        Causality is calculated based on a recursive constrains.
        This method reduce a n-comb to a (n-1)-comb at each step, and checks if the reduced comb is independent on the
        last output system.

        Args:
            order (str or int, optional): order of the norm. Defaults to ``None``.
            precision_tol (float, optional): threshold :math:`\\epsilon` that defines
                if Choi operator of the network is :math:`\\epsilon`-close to causality
                in the norm given by ``order``. Defaults to :math:`10^{-8}`.

        Returns:
            bool: Causal order condition.
        """
        if precision_tol < 0.0:
            raise_error(
                ValueError,
                f"``precision_tol`` must be non-negative float, but it is {precision_tol}",
            )

        dim_out = self.partition[-1]
        dim_in = self.partition[-2]

        reduced = np.tensordot(self.full(), trace(dim_out).full(), axes=1)
        sub_comb = np.tensordot(reduced, trace(dim_in).full(), axes=1)
        expected = np.tensordot(sub_comb, trace(dim_in).full() / dim_in, axes=0)

        if order == None:
            norm = self._backend.calculate_norm(reduced - expected)
        else:
            norm = self._backend.calculate_norm(reduced - expected, order=order)
        if norm > precision_tol:
            return False
        elif len(self.partition) == 2:
            return True
        else:
            return QuantumComb(
                sub_comb, self.partition[:-2], pure=False, backend=self._backend
            ).is_causal(order, precision_tol)

    @classmethod
    def from_nparray(
        cls, tensor, partition=None, pure=False, backend=None, inverse=False
    ):
        comb = super().from_nparray(tensor, partition, None, pure, backend)
        if (
            inverse
        ):  # Convert mathmetical convention of Choi operator to physical convention
            comb.partition = comb.partition[::-1]
            comb._tensor = np.transpose(comb._tensor)
        return comb


class QuantumChannel(QuantumComb):

    def __init__(
        self,
        tensor,
        partition: Optional[Union[List[int], Tuple[int]]] = None,
        system_input: Optional[Union[List[bool], Tuple[bool]]] = None,
        pure: bool = False,
        backend=None,
    ):
        if len(partition) > 2:
            raise_error(
                ValueError,
                "A quantum channel should only contain one input system and one output system. "
                + "For general quantum networks, one should use the ``QuantumNetwork`` class.",
            )

        if len(partition) == 1 or partition == None:
            if system_input == None:  # Assume the input is a quantum state
                partition = (1, partition[0])
            elif len(system_input) == 1:
                if system_input:
                    partition = (1, partition[0])
                else:
                    partition = (partition[0], 1)

        super().__init__(tensor, partition, pure=pure, backend=backend)

    def is_unital(
        self, order: Optional[Union[int, str]] = None, precision_tol: float = 1e-8
    ):
        """Returns bool indicating if the Choi operator :math:`\\mathcal{E}` of the network is unital.

        Unitality is calculated as distance between the partial trace of :math:`\\mathcal{E}`
        and the Identity operator :math:`I`, with respect to a given norm.
        Default is the ``Hilbert-Schmidt`` norm (also known as ``Frobenius`` norm).

        For specifications on the other  possible values of the
        parameter ``order`` for the ``tensorflow`` backend, please refer to
        `tensorflow.norm <https://www.tensorflow.org/api_docs/python/tf/norm>`_.
        For all other backends, please refer to
        `numpy.linalg.norm <https://numpy.org/doc/stable/reference/generated/numpy.linalg.norm.html>`_.

        Args:
            order (str or int, optional): order of the norm. Defaults to ``None``.
            precision_tol (float, optional): threshold :math:`\\epsilon` that defines
                if Choi operator of the network is :math:`\\epsilon`-close to unitality
                in the norm given by ``order``. Defaults to :math:`10^{-8}`.

        Returns:
            bool: Unitality condition.
        """
        if precision_tol < 0.0:
            raise_error(
                ValueError,
                f"``precision_tol`` must be non-negative float, but it is {precision_tol}",
            )

        if order is None and self._backend.__class__.__name__ == "TensorflowBackend":
            order = "euclidean"

        reduced = np.tensordot(self.full(), trace(self.partition[1]).full(), axes=1)
        sub_comb = np.tensordot(reduced, trace(self.partition[0]).full(), axes=1)
        expected = np.tensordot(
            sub_comb, trace(self.partition[0]).full() / self.partition[0], axes=0
        )

        norm = self._backend.calculate_norm((reduced - expected), order=order)
        if norm > precision_tol:
            return False
        elif len(self.partition) == 2:
            return True

        self._tensor = self.full()
        self._pure = False

        partial_trace = np.einsum("jkjl -> kl", self._tensor)
        identity = self._backend.cast(
            np.eye(partial_trace.shape[0]), dtype=partial_trace.dtype
        )

        norm = self._backend.calculate_norm_density_matrix(
            partial_trace - identity,
            order=order,
        )

        return float(norm) <= precision_tol

    def is_channel(
        self,
        order: Optional[Union[int, str]] = None,
        precision_tol_causal: float = 1e-8,
        precision_tol_psd: float = 1e-8,
    ):
        """Returns bool indicating if Choi operator :math:`\\mathcal{E}` is a channel.

        Args:
            order (int or str, optional): order of the norm used to calculate causality.
                Defaults to ``None``.
            precision_tol_causal (float, optional): threshold :math:`\\epsilon` that defines if
                Choi operator of the network is :math:`\\epsilon`-close to causality in the norm
                given by ``order``. Defaults to :math:`10^{-8}`.
            precision_tol_psd (float, optional): threshold value used to check if eigenvalues of
                the Choi operator :math:`\\mathcal{E}` are such that
                :math:`\\textup{eigenvalues}(\\mathcal{E}) >= \\textup{precision_tol_psd}`.
                Note that this parameter can be set to negative values.
                Defaults to :math:`0.0`.

        Returns:
            bool: Channel condition.
        """
        return self.is_causal(
            order, precision_tol_causal
        ) and self.is_positive_semidefinite(precision_tol_psd)

    def apply(self, state):
        """Apply the Choi operator :math:`\\mathcal{E}` to ``state`` :math:`\\varrho`.

        It is assumed that ``state`` :math:`\\varrho` is a density matrix.

        Args:
            state (ndarray): density matrix of a ``state``.

        Returns:
            ndarray: Resulting state :math:`\\mathcal{E}(\\varrho)`.
        """
        operator = np.copy(self.operator())

        if self.is_pure():
            return np.einsum("kj,ml,jl -> km", operator, np.conj(operator), state)

        return np.einsum("jklm, km", operator, state)


class StochQuantumNetwork:
    pass


def link_product(
    subscripts: str = "ij,jk -> ik",
    *operands: QuantumNetwork,
    backend=None,
    surpress_warning=False,
    casting: bool = True,
):
    """Link product between two quantum networks.

    The link product is not commutative. Here, we assume that
    :math:`A.\\textup{link_product}(B)` means "applying :math:`B` to :math:`A`".
    However, the ``link_product`` is associative, so we override the `@` operation
    in order to simplify notation.

    Args:
        subscripts (str, optional): Specifies the subscript for summation using
            the Einstein summation convention. For more details, please refer to
            `numpy.einsum <https://numpy.org/doc/stable/reference/generated/numpy.einsum.html>`_.
        operands (:class:`qibo.quantum_info.quantum_networks.QuantumNetwork`): Quantum
            networks to be contracted.

    Returns:
        :class:`qibo.quantum_info.quantum_networks.QuantumNetwork`: Quantum network resulting
            from the link product between two quantum networks.
    """

    if not isinstance(subscripts, str):
        raise_error(
            TypeError,
            f"subscripts must be type str, but it is type {type(subscripts)}.",
        )

    for i, operand in enumerate(operands):
        if not isinstance(operand, QuantumNetwork):
            raise_error(TypeError, f"The {i}th operator is not a ``QuantumNetwork``.")

    tensors = [
        operand.full() if operand.is_pure() else operand._tensor for operand in operands
    ]

    # keep track of the `partition` and `system_input` of the network
    _, contracrtion_list = np.einsum_path(
        subscripts, *tensors, optimize=False, einsum_call=True
    )

    inds, idx_rm, einsum_str, remaining, blas = contracrtion_list[0]
    input_str, results_index = einsum_str.split("->")
    inputs = input_str.split(",")

    # Warning if the same index connects two input or two output systems
    if not surpress_warning:
        for ind in idx_rm:
            found = 0
            for i, script in enumerate(inputs):
                try:
                    index = script.index(ind)
                    found += 1
                    if found > 1:
                        if is_input != operands[inds[i]].system_input[index]:
                            pass
                        else:
                            warning(
                                f"Index {ind} connects two {'input' if is_input else 'output'} systems."
                            )
                    is_input = operands[inds[i]].system_input[index]
                    if found > 2:
                        warning(
                            f"Index {ind} is accores multiple times in the input subscripts {input_str}."
                        )
                except:
                    continue

    # check output systems
    partition = []
    system_input = []
    for ind in results_index:
        found = False
        for i, script in enumerate(inputs):
            try:
                index = script.index(ind)
                if found:
                    warning(
                        f"Index {ind} is repeated in the input subscripts {input_str}."
                    )
                found = True

                partition.append(operands[inds[i]].partition[index])
                system_input.append(operands[inds[i]].system_input[index])

            except:
                continue

    new_tensor = np.einsum(subscripts, *tensors)

    return QuantumNetwork(new_tensor, partition, system_input, backend=backend)


def identity(dim: int, backend=None):
    """Returns the identity channel.

    Args:
        dim (int): Dimension of the identity operator.
        backend (:class:`qibo.backends.abstract.Backend`, optional): Backend to be used
            to return the identity operator. If ``None``, defaults to the backend defined
            when initializing the :class:`qibo.quant
    """

    return QuantumChannel.from_nparray(
        np.eye(dim), [dim, dim], pure=True, backend=backend
    )


def trace(dim: int, backend=None):
    """Returns the trace operator.

    Args:
        dim (int): Dimension to be traced.
        backend (:class:`qibo.backends.abstract.Backend`, optional): Backend to be used
            to return the identity operator. If ``None``, defaults to the backend defined
            when initializing the :class:`qibo.quant
    """

    return QuantumNetwork.from_nparray(
        np.eye(dim), [dim], [True], pure=False, backend=backend
    )
