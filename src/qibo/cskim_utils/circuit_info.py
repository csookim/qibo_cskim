from qibo import gates

def count_czs_qibo(circuit):
    """
    Count the number of CZ gates in a Qibo circuit.
    """
    count = 0
    for gate in circuit.queue:
        if isinstance(gate, gates.CZ):
            count += 1
    return count

def count_czs_qiskit(circuit):
    """
    Count the number of CZ gates in a Qiskit circuit.
    """
    count = 0
    for instr, _, _ in circuit.data:
        if instr.name == "cz":
            count += 1
    return count
    
def count_swaps_qibo(circuit):
    count = 0
    for gate in circuit.queue:
        if isinstance(gate, gates.SWAP):
            count += 1
    return count

def count_swaps_qiskit(circuit):
    count = 0
    for instr, _, _ in circuit.data:
        if instr.name == "swap":
            count += 1
    return count

def count_gates_qibo(circuit):
    count = 0
    for gate in circuit.queue:
        count += 1
    return count

def count_gates_qiskit(circuit):
    count = 0
    for instr, _, _ in circuit.data:
        count += 1
    return count