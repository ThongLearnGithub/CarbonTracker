"""Routing algorithms on a directed multigraph with per-edge weight lists.

A path is a list of edge indices. Weights are plain Python lists indexed by edge (faster than numpy
scalar indexing inside the search loops).

  dijkstra / shortest_path   single objective (fastest = t, greenest = c, shortest = d)
  yen_k_shortest             K loopless shortest paths on one objective (Yen 1971), spur searches are A*
                             with exact reverse-Dijkstra distances as heuristic
  larac                      constrained shortest path: min CO2 s.t. time <= bound (Lagrangian relaxation,
                             Juttner et al. 2001); fast but may miss the exact optimum
  pareto_boa                 full Pareto front on (time, CO2): bi-objective A* (BOA*, Hernandez et al. 2023)
"""
import heapq
import math
from collections import defaultdict

import numpy as np

INF = math.inf


class Graph:
    """Adjacency of one travel mode, restricted to that mode's largest strongly connected component."""

    def __init__(self, edges, mode):
        keep = np.flatnonzero((edges[mode] == 1) & (edges[f"lcc_{mode}"] == 1))
        self.eu = edges["u"].tolist()
        self.ev = edges["v"].tolist()
        self.adj, self.radj = defaultdict(list), defaultdict(list)
        for i in keep.tolist():
            self.adj[self.eu[i]].append((self.ev[i], i))
            self.radj[self.ev[i]].append((self.eu[i], i))
        self.nodes = set(self.adj) | set(self.radj)


def dijkstra(adj, source, w, target=None, h=None, banned_nodes=(), banned_edges=()):
    """Dijkstra (A* when h is given: dict node -> lower bound to target). Returns (dist, prev_edge)."""
    dist, prev, done = {source: 0.0}, {}, set()
    heap = [(h.get(source, INF) if h else 0.0, 0.0, source)]
    while heap:
        _, d, x = heapq.heappop(heap)
        if x in done:
            continue
        done.add(x)
        if x == target:
            break
        for y, e in adj.get(x, ()):
            if y in banned_nodes or e in banned_edges:
                continue
            nd = d + w[e]
            if nd < dist.get(y, INF):
                f = nd + (h.get(y, INF) if h else 0.0)
                if f < INF:
                    dist[y], prev[y] = nd, e
                    heapq.heappush(heap, (f, nd, y))
    return dist, prev


def _trace(g, prev, source, target):
    path, x = [], target
    while x != source:
        e = prev[x]
        path.append(e)
        x = g.eu[e]
    return path[::-1]


def path_cost(path, w):
    return sum(w[e] for e in path)


def shortest_path(g, source, target, w, h=None):
    dist, prev = dijkstra(g.adj, source, w, target=target, h=h)
    return _trace(g, prev, source, target) if target in dist else None


def distances_to(g, target, w):
    """Exact cost from every node to target (reverse Dijkstra) - an exact, consistent A* heuristic."""
    return dijkstra(g.radj, target, w)[0]


def yen_k_shortest(g, source, target, w, k, h=None):
    h = h or distances_to(g, target, w)
    first = shortest_path(g, source, target, w, h)
    if first is None:
        return []
    found, candidates, seen = [first], [], {tuple(first)}
    while len(found) < k:
        last = found[-1]
        nodes = [source] + [g.ev[e] for e in last]
        for i in range(len(last)):
            root = last[:i]
            banned_edges = {p[i] for p in found if len(p) > i and p[:i] == root}
            banned_nodes = set(nodes[:i])
            dist, prev = dijkstra(g.adj, nodes[i], w, target=target, h=h,
                                  banned_nodes=banned_nodes, banned_edges=banned_edges)
            if target not in dist:
                continue
            path = root + _trace(g, prev, nodes[i], target)
            if tuple(path) not in seen:
                seen.add(tuple(path))
                heapq.heappush(candidates, (path_cost(path, w), path))
        if not candidates:
            break
        found.append(heapq.heappop(candidates)[1])
    return found


def larac(g, source, target, cost, delay, max_delay):
    """LARAC: path minimising `cost` with sum(delay) <= max_delay. Returns (path, status)."""
    pc = shortest_path(g, source, target, cost)
    if path_cost(pc, delay) <= max_delay:
        return pc, "optimal"
    pd = shortest_path(g, source, target, delay)
    if path_cost(pd, delay) > max_delay:
        return None, "infeasible"
    for _ in range(50):
        lam = (path_cost(pc, cost) - path_cost(pd, cost)) / (path_cost(pd, delay) - path_cost(pc, delay))
        mixed = [c + lam * d for c, d in zip(cost, delay)]
        r = shortest_path(g, source, target, mixed)
        if math.isclose(path_cost(r, mixed), path_cost(pc, mixed), rel_tol=1e-9, abs_tol=1e-9):
            return pd, "lagrangian"
        if path_cost(r, delay) <= max_delay:
            pd = r
        else:
            pc = r
    return pd, "lagrangian"


def pareto_boa(g, source, target, w1, w2, h1=None, h2=None, max_w1=INF, eps=0.0):
    """Pareto-optimal paths for (w1, w2), sorted by w1. eps > 0 drops solutions that improve w2 by
    less than a fraction eps of the best w2 found so far (epsilon-approximate front, fewer labels)."""
    h1 = h1 or distances_to(g, target, w1)
    h2 = h2 or distances_to(g, target, w2)
    if source not in h1:
        return [], 0
    g2min = defaultdict(lambda: INF)
    labels = [(None, -1)]  # (edge, parent label)
    heap = [(h1[source], h2[source], 0.0, 0.0, source, 0)]
    solutions, expanded = [], 0
    while heap:
        f1, f2, g1, g2, x, lid = heapq.heappop(heap)
        if g2 >= g2min[x] or f2 >= g2min[target] * (1 - eps):
            continue
        g2min[x] = g2
        expanded += 1
        if x == target:
            solutions.append(lid)
            continue
        for y, e in g.adj.get(x, ()):
            n1, n2 = g1 + w1[e], g2 + w2[e]
            if y not in h1 or n2 >= g2min[y] or n2 + h2[y] >= g2min[target] * (1 - eps) or n1 + h1[y] > max_w1:
                continue
            labels.append((e, lid))
            heapq.heappush(heap, (n1 + h1[y], n2 + h2[y], n1, n2, y, len(labels) - 1))
    paths = []
    for lid in solutions:
        path = []
        while labels[lid][0] is not None:
            path.append(labels[lid][0])
            lid = labels[lid][1]
        paths.append(path[::-1])
    return paths, expanded
