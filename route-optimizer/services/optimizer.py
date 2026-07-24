"""
OR-Tools TSP solver for open routes (rep doesn't need to return to start).

Architecture:
  - The start location is node 0 in the matrix.
  - Doctor stops are nodes 1…N.
  - We add a dummy end depot (node N+1) with 0-cost arcs from everywhere,
    so OR-Tools finds the cheapest open path from 0 through all nodes 1…N.
  - Falls back to Nearest-Neighbor heuristic if OR-Tools is unavailable or
    the solver times out without a solution.
"""
from __future__ import annotations

import logging
import math

logger = logging.getLogger(__name__)

try:
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    OR_TOOLS_AVAILABLE = True
    logger.info("[optimizer] OR-Tools loaded OK")
except ImportError:
    OR_TOOLS_AVAILABLE = False
    logger.warning("[optimizer] OR-Tools not installed — using nearest-neighbor fallback")


# ─── Public entry point ────────────────────────────────────────────────────────

def solve_tsp(duration_matrix: list[list[int]], start_index: int = 0) -> list[int]:
    """
    Given a symmetric NxN duration matrix (seconds), return the optimal visit
    order as a list of node indices.  start_index is always first in the result.

    Example: solve_tsp([[0,300,600],[300,0,400],[600,400,0]], start_index=0)
             → [0, 2, 1]  (start at 0, go to 2, then 1)
    """
    n = len(duration_matrix)
    if n == 0:
        return []
    if n == 1:
        return [0]

    if OR_TOOLS_AVAILABLE:
        result = _ortools_solve(duration_matrix, start_index)
        if result:
            return result

    logger.warning("[optimizer] Falling back to nearest-neighbor heuristic")
    return _nearest_neighbor(duration_matrix, start_index)


# ─── OR-Tools solver ──────────────────────────────────────────────────────────

def _ortools_solve(matrix: list[list[int]], start: int) -> list[int] | None:
    n = len(matrix)
    dummy = n  # dummy end depot

    # Build augmented (n+1) × (n+1) matrix; dummy row/col is all zeros
    aug_size = n + 1
    aug = [[0] * aug_size for _ in range(aug_size)]
    for i in range(n):
        for j in range(n):
            aug[i][j] = matrix[i][j]

    manager = pywrapcp.RoutingIndexManager(aug_size, 1, [start], [dummy])
    routing = pywrapcp.RoutingModel(manager)

    def _callback(from_idx: int, to_idx: int) -> int:
        fn = manager.IndexToNode(from_idx)
        tn = manager.IndexToNode(to_idx)
        return aug[fn][tn]

    cb_idx = routing.RegisterTransitCallback(_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(cb_idx)

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.seconds = 5

    solution = routing.SolveWithParameters(params)
    if not solution:
        return None

    order: list[int] = []
    idx = routing.Start(0)
    while not routing.IsEnd(idx):
        node = manager.IndexToNode(idx)
        if node != dummy:
            order.append(node)
        idx = solution.Value(routing.NextVar(idx))

    return order if order else None


# ─── Nearest-neighbor fallback ────────────────────────────────────────────────

def _nearest_neighbor(matrix: list[list[int]], start: int) -> list[int]:
    n = len(matrix)
    visited = {start}
    order = [start]
    current = start

    while len(order) < n:
        nearest = min(
            (j for j in range(n) if j not in visited),
            key=lambda j: matrix[current][j],
            default=None,
        )
        if nearest is None:
            break
        order.append(nearest)
        visited.add(nearest)
        current = nearest

    return order


# ─── Haversine distance (meters) ──────────────────────────────────────────────

def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> int:
    R = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return int(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def build_haversine_matrix(coords: list[tuple[float, float]]) -> list[list[int]]:
    """coords = list of (lat, lng). Returns duration proxy (seconds ~ distance/14 m/s)."""
    n = len(coords)
    mat = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                d = haversine_m(coords[i][0], coords[i][1], coords[j][0], coords[j][1])
                mat[i][j] = int(d / 14)  # ~50 km/h urban speed
    return mat
