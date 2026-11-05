"""RoutingEngine: loads the graph once, keeps weights per (profile, slot) and answers route queries."""
import math
import time
from collections import OrderedDict

import numpy as np
import shapely
from scipy.spatial import cKDTree

from . import algorithms as alg
from .model import edge_weights, load_config, load_edges, load_nodes, slot_for_time

ALGORITHMS = ("pareto", "fastest", "greenest", "shortest", "yen", "csp")
M_PER_DEG = 111_320.0
MAX_SNAP_M = 300


class RoutingError(ValueError):
    pass


class RoutingEngine:
    def __init__(self):
        t0 = time.time()
        self.cfg = load_config()
        edges, nodes = load_edges(with_geometry=True), load_nodes()
        self.length = edges["length_m"].tolist()
        self.name = edges["name"]
        self.geometry = [g.coords[:] for g in shapely.from_wkt(edges["geometry_wkt"])]
        modes = {p["graph_mode"] for p in self.cfg["profiles"].values()}
        self.graphs = {m: alg.Graph(edges, m) for m in modes}
        self.weights = {}
        for profile in self.cfg["profiles"]:
            for slot in self.cfg["slots"]:
                t, c = edge_weights(edges, self.cfg, profile, slot)
                self.weights[profile, slot] = (t.tolist(), c.tolist())
        lat0 = math.radians(np.mean([float(n["lat"]) for n in nodes.values()]))
        self.coslat = math.cos(lat0)
        self.trees = {}
        for m, g in self.graphs.items():
            ids = sorted(g.nodes)
            xy = np.array([(float(nodes[i]["lon"]) * self.coslat, float(nodes[i]["lat"])) for i in ids])
            self.trees[m] = (cKDTree(xy), ids, xy)
        self.load_seconds = round(time.time() - t0, 1)

    # -----------------------------------------------------------------------------------------
    def snap(self, mode, lat, lon):
        tree, ids, xy = self.trees[mode]
        d, i = tree.query((lon * self.coslat, lat))
        meters = d * M_PER_DEG
        if meters > MAX_SNAP_M:
            raise RoutingError(f"point ({lat:.6f}, {lon:.6f}) is {meters:.0f} m from the nearest road usable by "
                               f"{mode}; the graph only covers the LEZ + 1 km buffer")
        return ids[i], round(meters, 1), (xy[i][1], xy[i][0] / self.coslat)

    def route(self, origin, destination, vehicle, depart_at=None, slot=None, algorithm="pareto", k=3,
              max_extra_time=0.2):
        if vehicle not in self.cfg["profiles"]:
            raise RoutingError(f"unknown vehicle '{vehicle}', expected one of {list(self.cfg['profiles'])}")
        if algorithm not in ALGORITHMS:
            raise RoutingError(f"unknown algorithm '{algorithm}', expected one of {list(ALGORITHMS)}")
        slot = slot or slot_for_time(self.cfg, depart_at or "10:30")
        if slot not in self.cfg["slots"]:
            raise RoutingError(f"unknown slot '{slot}', expected one of {list(self.cfg['slots'])}")
        profile = self.cfg["profiles"][vehicle]
        g = self.graphs[profile["graph_mode"]]
        t, c = self.weights[vehicle, slot]
        s, s_off, s_xy = self.snap(profile["graph_mode"], *origin)
        d, d_off, d_xy = self.snap(profile["graph_mode"], *destination)
        if s == d:
            raise RoutingError("origin and destination snap to the same node")

        t0 = time.perf_counter()
        info = {}
        ht = alg.distances_to(g, d, t)
        fastest = alg.shortest_path(g, s, d, t, ht)
        has_co2 = profile["energy"] is not None
        if algorithm == "fastest":
            paths = [("fastest", fastest)]
        elif algorithm == "greenest":
            paths = [("fastest", fastest), ("greenest", alg.shortest_path(g, s, d, c))] if has_co2 else [("fastest", fastest)]
        elif algorithm == "shortest":
            paths = [("fastest", fastest), ("shortest", alg.shortest_path(g, s, d, self.length))]
        elif algorithm == "yen":
            paths = [(f"yen_{i + 1}", p) for i, p in enumerate(alg.yen_k_shortest(g, s, d, t, k, ht))]
        elif algorithm == "csp":
            bound = alg.path_cost(fastest, t) * (1 + max_extra_time)
            p, status = alg.larac(g, s, d, c, t, bound) if has_co2 else (fastest, "no_co2")
            info.update(time_bound_s=round(bound, 1), larac_status=status)
            paths = [("fastest", fastest), ("csp", p)]
        else:  # pareto
            if not has_co2:
                paths = [("fastest", fastest)]
            else:
                front, expanded = alg.pareto_boa(g, s, d, t, c, h1=ht)
                info.update(pareto_size=len(front), labels_expanded=expanded)
                paths = [(f"pareto_{i + 1}", p) for i, p in enumerate(pick_spread(front, c, k))]
        info["compute_ms"] = round((time.perf_counter() - t0) * 1000, 1)

        base_t, base_c = alg.path_cost(fastest, t), alg.path_cost(fastest, c)
        fastest_edges = set(fastest)
        routes, seen = [], set()
        for label, p in paths:
            if p is None or tuple(p) in seen:
                continue
            seen.add(tuple(p))
            pt, pc, pd = alg.path_cost(p, t), alg.path_cost(p, c), alg.path_cost(p, self.length)
            routes.append({
                "label": label,
                "time_min": round(pt / 60, 2),
                "co2_g": round(pc, 1),
                "distance_km": round(pd / 1000, 3),
                "extra_time_min": round((pt - base_t) / 60, 2),
                "co2_saving_pct": round(100 * (base_c - pc) / base_c, 1) if base_c else 0.0,
                "shared_with_fastest_pct": round(100 * sum(self.length[e] for e in p if e in fastest_edges) / pd, 1),
                "via": self.via(p),
                "geometry": {"type": "LineString", "coordinates": self.line(p)},
            })
        return {
            "vehicle": vehicle, "slot": slot, "algorithm": algorithm,
            "origin": {"node": s, "lat": s_xy[0], "lon": s_xy[1], "snap_m": s_off},
            "destination": {"node": d, "lat": d_xy[0], "lon": d_xy[1], "snap_m": d_off},
            "google_maps_url": google_url(s_xy, d_xy, profile["graph_mode"]),  # snapped points = where the model's routes start/end
            "info": info,
            "routes": routes,
        }

    def via(self, path, top=3):
        """Main named streets of a path, in travel order."""
        length = OrderedDict()
        for e in path:
            if self.name[e]:
                length[self.name[e]] = length.get(self.name[e], 0) + self.length[e]
        main = sorted(length, key=length.get, reverse=True)[:top]
        return [n for n in length if n in main]

    def line(self, path):
        coords = []
        for e in path:
            pts = self.geometry[e]
            coords.extend(pts if not coords else pts[1:])
        return [[round(x, 7), round(y, 7)] for x, y in coords]


def pick_spread(front, c, k):
    """k paths of a Pareto front (sorted by time): fastest, greenest, and the rest spread evenly in CO2."""
    if len(front) <= k:
        return front
    costs = [alg.path_cost(p, c) for p in front]
    chosen = {0, len(front) - 1}
    for level in np.linspace(costs[0], costs[-1], k)[1:-1]:
        rest = [i for i in range(len(front)) if i not in chosen]
        chosen.add(min(rest, key=lambda i: abs(costs[i] - level)))
    return [front[i] for i in sorted(chosen)]


GOOGLE_MODE = {"motorcycle": "two-wheeler", "car": "driving", "bicycle": "bicycling", "foot": "walking"}


def google_url(origin, destination, mode):
    return (f"https://www.google.com/maps/dir/?api=1&origin={origin[0]:.6f},{origin[1]:.6f}"
            f"&destination={destination[0]:.6f},{destination[1]:.6f}&travelmode={GOOGLE_MODE[mode]}")
