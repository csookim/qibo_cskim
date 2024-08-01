import networkx as nx
import numpy as np

def star_connectivity_nx():
    """
    Returns a star graph with 5 nodes and 4 edges.
    """
    Q = [i for i in range(5)]
    chip = nx.Graph()
    chip.add_nodes_from(Q)
    graph_list = [(Q[i], Q[2]) for i in range(5) if i != 2]
    chip.add_edges_from(graph_list)
    return chip

def star_connectivity_cmap():
    """
    Returns a star graph with 5 nodes and 4 edges.
    """
    Q = [i for i in range(5)]
    chip = nx.Graph()
    chip.add_nodes_from(Q)
    graph_list = [[Q[i], Q[2]] for i in range(5) if i != 2]
    graph_list_rev = [[Q[2], Q[i]] for i in range(5) if i != 2]
    graph_list.extend(graph_list_rev)
    return graph_list

def cycle_connectivity_nx(n):
    """
    Returns a cycle graph with n nodes and n edges.
    Return nx.Graph.
    For Qibo.
    """
    Q = [i for i in range(n)]
    chip = nx.Graph()
    chip.add_nodes_from(Q)
    graph_list = [(Q[i] % n, (Q[i]+1) % n) for i in range(n)]
    # print(graph_list)
    chip.add_edges_from(graph_list)
    return chip

def complete_connectivity_nx(n):
    Q = [i for i in range(n)]
    chip = nx.Graph()
    chip.add_nodes_from(Q)

    elements = np.arange(n)
    graph_list = []
    for i in range(len(elements)):
        for j in range(i + 1, len(elements)):
            graph_list.append((elements[i], elements[j]))
    # print(graph_list)
    chip.add_edges_from(graph_list)
    return chip

def line_connectivity_nx(n):
    """
    Returns a line graph with n nodes and n-1 edges.
    Return nx.Graph.
    For Qibo.
    """
    Q = [i for i in range(n)]
    chip = nx.Graph()
    chip.add_nodes_from(Q)
    graph_list = [(Q[i], (Q[i]+1) % n) for i in range(n-1)]
    # print(graph_list)
    chip.add_edges_from(graph_list)
    return chip

def cycle_connectivity_cmap(n):
    """
    Returns a cycle graph with n nodes and n edges.
    Return list of lists (Coupling map).
    For Qiskit.
    """
    Q = [i for i in range(n)]
    chip = nx.Graph()
    chip.add_nodes_from(Q)
    graph_list = [[Q[i] % n, (Q[i]+1) % n] for i in range(n)]
    graph_list_rev = [[(Q[i]+1) % n, (Q[i]) % n] for i in range(n)]
    graph_list.extend(graph_list_rev)
    # print(graph_list)

    return graph_list

def complete_connectivity_cmap(n):
    Q = [i for i in range(n)]
    chip = nx.Graph()
    chip.add_nodes_from(Q)

    elements = np.arange(n)
    graph_list = []
    for i in range(len(elements)):
        for j in range(i + 1, len(elements)):
            graph_list.append([elements[i], elements[j]])
        
    graph_list_rev = []
    for i in range(len(elements)):
        for j in range(i + 1, len(elements)):
            graph_list_rev.append([elements[j], elements[i]])
    
    graph_list.extend(graph_list_rev)
    # print(graph_list)

    return graph_list

def line_connectivity_cmap(n):
    """
    Returns a line graph with n nodes and n-1 edges.
    Return list of lists (Coupling map).
    For Qiskit.
    """
    Q = [i for i in range(n)]
    chip = nx.Graph()
    chip.add_nodes_from(Q)

    graph_list = [[Q[i], (Q[i]+1) % n] for i in range(n-1)]
    graph_list_rev = [[(Q[i]+1) % n, (Q[i]) % n] for i in range(n-1)]
    graph_list.extend(graph_list_rev)
    # print(graph_list)

    return graph_list

def iqm_connectivity_nx():
    """
    Returns the connectivity graph of the IQM-20 chip architecture (For Qibo).
    """
    g = nx.Graph()
    edges = [(0, 1), (0, 3), (2, 3), (1, 4), (3, 4), (4, 5),
            (9, 10), (5, 6), (6, 11), (10, 11), (11, 16), (15, 16), 
            (15, 19), (14, 15), (18, 19), (10, 15), (14, 18), (17, 18), 
            (13, 17), (13, 14), (12, 13), (9, 14), (8, 13), (7, 12), 
            (8, 9), (7, 8), (2, 7), (5, 10), (4, 9), (3, 8)]

    g.add_edges_from(edges)
    # nx.draw(g, with_labels=True)
    return g

def iqm_connectivity_cmap():
    """
    Returns the connectivity coupling graph of the IQM-20 chip architecture (For Qiskit).
    """
    edges = [(0, 1), (0, 3), (2, 3), (1, 4), (3, 4), (4, 5),
            (9, 10), (5, 6), (6, 11), (10, 11), (11, 16), (15, 16), 
            (15, 19), (14, 15), (18, 19), (10, 15), (14, 18), (17, 18), 
            (13, 17), (13, 14), (12, 13), (9, 14), (8, 13), (7, 12), 
            (8, 9), (7, 8), (2, 7), (5, 10), (4, 9), (3, 8)]
    
    graph_list = [[edges[i][0], edges[i][1]] for i in range(len(edges))]
    graph_list_rev = [[edges[i][1], edges[i][0]] for i in range(len(edges))]
    graph_list.extend(graph_list_rev)
    # print(len(graph_list))
    return graph_list


def nakamura_connectivitiy_nx():
    g = nx.Graph()
    edges = []
    for i in range(16):
        if i % 4 != 3:
            edges.append((i, i + 1))
        if i < 12:
            edges.append((i, i + 4))

    g.add_edges_from(edges)
    return g

def nakamura_connectivity_cmap():
    graph_list = []
    edges = []
    for i in range(16):
        if i % 4 != 3:
            edges.append((i, i + 1))
        if i < 12:
            edges.append((i, i + 4))

    for e in edges:
        graph_list.append([e[0], e[1]])
        graph_list.append([e[1], e[0]])

    return graph_list