import sympy
from qibo import gates, K
from qibo.config import raise_error


class HamiltonianTerm:
    """Single term in a :class:`qibo.core.hamiltonians.SymbolicHamiltonian`.

    This Hamiltonian is represented by a sum of such terms which are held in
    its ``.terms`` attribute which is a list.

    Args:
        matrix (np.ndarray): Full matrix corresponding to the term representation
            in the computational basis. Has size (2^n, 2^n) where n is the
            number of target qubits of this term.
        q (list): List of target qubit ids.
    """

    def __init__(self, matrix, *q):
        for qi in q:
            if qi < 0:
                raise_error(ValueError, "Invalid qubit id {} < 0 was given "
                                        "in Hamiltonian term".format(qi))
        if not (matrix is None or isinstance(matrix, K.qnp.numeric_types) or
                isinstance(matrix, K.qnp.tensor_types)):
            raise_error(TypeError, "Invalid type {} of symbol matrix."
                                   "".format(type(matrix)))
        dim = int(matrix.shape[0])
        if 2 ** len(q) != dim:
            raise_error(ValueError, "Matrix dimension {} given in Hamiltonian "
                                    "term is not compatible with the number "
                                    "of target qubits {}."
                                    "".format(dim, len(q)))
        self.target_qubits = tuple(q)
        self._gate = None
        self.hamiltonian = None
        self._matrix = matrix

    @property
    def matrix(self):
        return self._matrix

    @property
    def gate(self):
        """Qibo gate that implements the action of the term on states."""
        if self._gate is None:
            self._gate = gates.Unitary(self.matrix, *self.target_qubits)
        return self._gate

    def exp(self, x):
        """Matrix exponentiation of the term."""
        return K.qnp.expm(-1j * x * self.matrix)

    def expgate(self, x):
        """Unitary gate implementing the matrix exponentiation of the term."""
        return gates.Unitary(self.exp(x), *self.target_qubits)

    def merge(self, term):
        """Creates a new term by merging the given term to the current one.

        The target qubits of the given term should be a subset of the target
        qubits of the current term.
        """
        if not set(term.target_qubits).issubset(set(self.target_qubits)):
            raise_error(ValueError, "Cannot merge HamiltonianTerm acting on "
                                    "qubits {} to term on qubits {}."
                                    "".format(term.target_qubits, self.target_qubits))
        matrix = K.np.kron(term.matrix, K.qnp.eye(2 ** (len(self) - len(term))))
        matrix = K.np.reshape(matrix, 2 * len(self) * (2,))
        order = []
        i = len(term)
        for qubit in self.target_qubits:
            if qubit in term.target_qubits:
                order.append(term.target_qubits.index(qubit))
            else:
                order.append(i)
                i += 1
        order.extend([x + len(order) for x in order])
        matrix = K.np.transpose(matrix, order)
        matrix = K.np.reshape(matrix, 2 * (2 ** len(self),))
        return HamiltonianTerm(self.matrix + matrix, *self.target_qubits)

    def __len__(self):
        return len(self.target_qubits)

    def __mul__(self, x):
        return HamiltonianTerm(x * self.matrix, *self.target_qubits)

    def __rmul__(self, x):
        return self.__mul__(x)

    def __call__(self, state, density_matrix=False):
        """Applies the term on a given state vector or density matrix."""
        if density_matrix:
            self.gate.density_matrix = True
            return self.gate._density_matrix_half_call(state)
        return self.gate(state) # pylint: disable=E1102


class SymbolicTerm(HamiltonianTerm):
    """:class:`qibo.core.terms.HamiltonianTerm` constructed from ``sympy`` symbols.

    Example:
        ::

            from qibo.symbols import X, Y
            from qibo.core.terms import SymbolicTerm
            sham = X(0) * X(1) + 2 * Y(0) * Y(1)
            termsdict = sham.as_coefficients_dict()
            sterms = [SymbolicTerm(c, f) for f, c in termsdict.items()]

    Args:
        coefficient (complex): Complex number coefficient of the underlying
            term in the Hamiltonian.
        factors (sympy.Expr): Sympy expression for the underlying term.
        matrix_map (dict): Dictionary that maps symbols in the given ``factors``
            expression to tuples of (target qubit id, matrix).
            This is required only if the expression is not created using Qibo
            symbols and to keep compatibility with older versions where Qibo
            symbols were not available.
    """

    def __init__(self, coefficient, factors=[], matrix_map={}):
        self.coefficient = complex(coefficient)
        self.factors = factors
        self.matrix_map = matrix_map
        self._matrix = None
        self._gate = None
        self.hamiltonian = None
        self.target_qubits = tuple(sorted(self.matrix_map.keys()))

    @classmethod
    def from_factors(cls, coefficient, factors, symbol_map=None):
        if factors == 1:
            return cls(coefficient)

        _factors = []
        _matrix_map = {}
        for factor in factors.as_ordered_factors():
            if isinstance(factor, sympy.Pow):
                factor, pow = factor.args
                assert isinstance(pow, sympy.Integer)
                assert isinstance(factor, sympy.Symbol)
                pow = int(pow)
            else:
                pow = 1

            if symbol_map is not None and factor in symbol_map:
                from qibo.symbols import Symbol
                q, matrix = symbol_map.get(factor)
                factor = Symbol(q, matrix, name=factor.name)

            if isinstance(factor, sympy.Symbol):
                if isinstance(factor.matrix, K.qnp.tensor_types):
                    _factors.extend(pow * [factor])
                    q = factor.target_qubit
                    if q in _matrix_map:
                        _matrix_map[q].extend(pow * [factor.matrix])
                    else:
                        _matrix_map[q] = pow * [factor.matrix]
                else:
                    coefficient *= factor.matrix
            elif factor == sympy.I:
                coefficient *= 1j
            else: # pragma: no cover
                raise_error(TypeError, "Cannot parse factor {}.".format(factor))

        return cls(coefficient, _factors, _matrix_map)

    @property
    def matrix(self):
        """Calculates the full matrix corresponding to this term.

        Returns:
            Matrix as a ``np.ndarray`` of shape ``(2 ** ntargets, 2 ** ntargets)``
            where ``ntargets`` is the number of qubits included in the factors
            of this term.
        """
        if self._matrix is None:
            def matrices_product(matrices):
                if len(matrices) == 1:
                    return matrices[0]
                matrix = K.np.copy(matrices[0])
                for m in matrices[1:]:
                    matrix = matrix @ m
                return matrix

            self._matrix = self.coefficient
            for q in self.target_qubits:
                matrix = matrices_product(self.matrix_map.get(q))
                self._matrix = K.np.kron(self._matrix, matrix)
        return self._matrix

    def __mul__(self, x):
        new = self.__class__(self.coefficient, self.factors, self.matrix_map)
        new._matrix = self._matrix
        new._gate = self._gate
        new.coefficient *= x
        return new

    def __call__(self, state, density_matrix=False):
        for factor in self.factors:
            if density_matrix:
                factor.gate.density_matrix = True
                state = factor.gate._density_matrix_half_call(state)
            else:
                state = factor.gate(state)
        return self.coefficient * state


class TermGroup(list):
    """Collection of multiple :class:`qibo.core.terms.HamiltonianTerm` objects.

    Allows merging multiple terms to a single one for faster exponentiation.

    Args:
        term (:class:`qibo.core.terms.HamiltonianTerm`): Parent term of the group.
            All terms appended later should target a subset of the parents'
            target qubits.
    """

    def __init__(self, term):
        super().__init__([term])
        self.target_qubits = set(term.target_qubits)
        self._term = None

    def append(self, term):
        """Appends a new :class:`qibo.core.terms.HamiltonianTerm` to the collection."""
        super().append(term)
        self.target_qubits |= set(term.target_qubits)
        self._term = None

    def can_append(self, term):
        """Checks if a term can be appended to the group based on its target qubits."""
        return set(term.target_qubits).issubset(self.target_qubits)

    @classmethod
    def from_terms(cls, terms):
        """Groups a list of terms to multiple groups.

        Args:
            terms (list): List of :class:`qibo.core.terms.HamiltonianTerm` objects.

        Returns:
            List of :class:`qibo.core.terms.TermGroup` objects that contain
            all the given terms.
        """
        orders = {}
        for term in terms:
            if len(term) in orders:
                orders[len(term)].append(term)
            else:
                orders[len(term)] = [term]

        groups = []
        for order in sorted(orders.keys())[::-1]:
            for child in orders[order]:
                flag = True
                for i, group in enumerate(groups):
                    if group.can_append(child):
                        group.append(child)
                        flag = False
                        break
                if flag:
                    groups.append(cls(child))
        return groups

    @property
    def term(self):
        """Returns a single :class:`qibo.core.terms.HamiltonianTerm`. after merging all terms in the group."""
        if self._term is None:
            self._term = self.to_term()
        return self._term

    def to_term(self, coefficients={}):
        """Calculates a single :class:`qibo.core.terms.HamiltonianTerm` by merging all terms in the group.

        Args:
            coefficients (dict): Optional dictionary that allows passing a different
                coefficient to each term according to its parent Hamiltonian.
                Useful for :class:`qibo.core.adiabatic.AdiabaticHamiltonian` calculations.
        """
        c = coefficients.get(self[0].hamiltonian)
        merged = self[0] * c if c is not None else self[0]
        for term in self[1:]:
            c = coefficients.get(term.hamiltonian)
            merged = merged.merge(term * c if c is not None else term)
        return merged
