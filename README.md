![Logo](https://raw.githubusercontent.com/qiboteam/qibo/c3031c606464650856d6d278b799eeee4a1f49fe/doc/source/_static/qibo_logo_dark.svg)

This repository contains the tasks of Changsoo Kim during his internship with Qibo.

## Improve Qibo SABRE

### Issues

#### Issue [#3](https://github.com/csookim/qibo_transpiler_cskim/issues/3)

> [Notebook](https://github.com/csookim/qibo_transpiler_cskim/blob/master/cskim/docs/transpiler_general/3_sabre_qiskit_qibo.ipynb)

- For QFT(10), the average number of CZ gates is similar, but the minimum number of CZ gates is smaller when using Qiskit SABRE.
- For random CZ circuits, both the average and minimum number of CZ gates are smaller when using Qiskit SABRE.
- Qiskit shows more fluctuation.
- This indicates that Qiskit SABRE has the potential to generate routings with fewer CZ gates.

#### Issue [#4](https://github.com/csookim/qibo_transpiler_cskim/issues/4)

> [Notebook](https://github.com/csookim/qibo_transpiler_cskim/blob/master/cskim/docs/transpiler_general/4_shortestpath_sabre.ipynb)

- For QFT(5) + Cycle, Shortestpath has fewer CNOTs than SABRE. Shortestpath has the potential to generate routings with fewer CZ gates in 5-qubit circuits.

## Improve KAK

#### Issue [#20](https://github.com/csookim/qibo_transpiler_cskim/issues/20)

- The matrix reassembled after the KAK decomposition is different from the original matrix when using Identity and CNOT matrices.

## Design a Placer with New Cost Function

- Variables to consider: Coherence time, Qubit fidelity
- Example Cost Function: C = func(Fid_SWAP_ij, ti, tj)
- Fid_SWAP_ij = #SWAPS * fidelity
- Choose SWAP path with the highest fidelity
