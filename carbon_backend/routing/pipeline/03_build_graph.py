"""Build a directed, mode-aware road graph from the LEZ OSM extract.

Graph model
  * node  = OSM node where a road starts/ends or where two road ways meet (intersection);
  * edge  = road piece between two such nodes, one record per travel direction (u -> v);
  * every edge carries a 0/1 flag per mode (motorcycle, car, bicycle, foot) saying whether that
    mode may travel u -> v, from OSM access tags + one-way rules + Vietnamese defaults below.
  * edge length = geodesic length of the full OSM geometry (WGS84 ellipsoid).
Speed, travel time and CO2 are NOT computed here; they come from the speed model in the next step.
Raw tags needed for it (highway, maxspeed, lanes, traffic signals) are kept on the edges.

Input : data/osm/lez_buffer_1km.osm.pbf, data/lez/lez_union.geojson
Output: data/graph/nodes.csv, edges.csv, edges.geojson, summary.json, graph_preview.png
"""
import csv
import json
import time
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import osmium
import shapely
from pyproj import Geod
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "osm" / "lez_buffer_1km.osm.pbf"
LEZ = ROOT / "data" / "lez" / "lez_union.geojson"
OUT = ROOT / "data" / "graph"

MODES = ("motorcycle", "car", "bicycle", "foot")

# ---------------------------------------------------------------------------------------------
# Access rules (assumptions, documented for the thesis)
# ---------------------------------------------------------------------------------------------
# Roads open to all modes unless tagged otherwise.
GENERAL_ROADS = {
    "trunk", "trunk_link", "primary", "primary_link", "secondary", "secondary_link",
    "tertiary", "tertiary_link", "unclassified", "residential", "living_street",
    "service", "road", "track",
}
# Default modes per highway type when no access tag says otherwise.
DEFAULT_MODES = {
    **{hw: set(MODES) for hw in GENERAL_ROADS},
    # Vietnamese traffic law: motorcycles, bicycles and pedestrians may not use expressways.
    "motorway": {"car"},
    "motorway_link": {"car"},
    "pedestrian": {"foot"},
    "footway": {"foot"},
    "steps": {"foot"},
    "bridleway": {"foot"},
    "path": {"foot", "bicycle"},
    "cycleway": {"bicycle", "foot"},
    "busway": set(),  # bus only
}
ROUTABLE = set(DEFAULT_MODES)  # construction / proposed / platform / corridor ... are dropped

# OSM access-key hierarchy, most specific first.
ACCESS_KEYS = {
    "motorcycle": ("motorcycle", "motor_vehicle", "vehicle", "access"),
    "car": ("motorcar", "motor_vehicle", "vehicle", "access"),
    "bicycle": ("bicycle", "vehicle", "access"),
    "foot": ("foot", "access"),
}
ALLOW = {"yes", "designated", "permissive", "destination", "customers", "delivery", "official", "discouraged"}
DENY = {"no", "private", "agricultural", "forestry", "emergency", "military", "restricted",
        "use_sidepath", "dismount"}

ONEWAY_KEYS = {
    "motorcycle": ("oneway:motorcycle", "oneway:motor_vehicle", "oneway:vehicle", "oneway"),
    "car": ("oneway:motorcar", "oneway:motor_vehicle", "oneway:vehicle", "oneway"),
    "bicycle": ("oneway:bicycle", "oneway:vehicle", "oneway"),
    "foot": ("oneway:foot",),  # pedestrians ignore one-way streets
}
ONEWAY_VALUES = {"yes": 1, "1": 1, "true": 1, "-1": -1, "reverse": -1, "no": 0, "0": 0, "false": 0}


def allowed(tags, mode):
    hw = tags["highway"]
    if mode in ("bicycle", "foot") and tags.get("motorroad") == "yes":
        return False
    for key in ACCESS_KEYS[mode]:
        value = tags.get(key)
        if value in ALLOW:
            return True
        if value in DENY:
            return False
    return mode in DEFAULT_MODES[hw]


def oneway(tags, mode):
    """+1 = only along the way's node order, -1 = only against it, 0 = both directions."""
    if mode == "bicycle" and tags.get("cycleway", "").startswith("opposite"):
        return 0  # contra-flow cycle lane
    for key in ONEWAY_KEYS[mode]:
        if key in tags:
            return ONEWAY_VALUES.get(tags[key], 0)
    if mode == "foot":
        return 0
    if tags.get("junction") in ("roundabout", "circular") or tags["highway"] in ("motorway", "motorway_link"):
        return 1
    return 0


# ---------------------------------------------------------------------------------------------
# Reading OSM
# ---------------------------------------------------------------------------------------------
def read_osm():
    coords, signals, ways = {}, set(), []
    keep_tags = ("highway", "name", "maxspeed", "lanes", "oneway", "junction", "bridge", "tunnel",
                 "motorroad", "cycleway", "area", *{k for ks in ACCESS_KEYS.values() for k in ks},
                 *{k for ks in ONEWAY_KEYS.values() for k in ks})
    for obj in osmium.FileProcessor(str(SRC)):
        if obj.is_node():
            coords[obj.id] = (obj.location.lon, obj.location.lat)
            if obj.tags.get("highway") == "traffic_signals":
                signals.add(obj.id)
        elif obj.is_way():
            hw = obj.tags.get("highway")
            if hw in ROUTABLE and obj.tags.get("area") != "yes" and len(obj.nodes) >= 2:
                tags = {k: obj.tags[k] for k in keep_tags if k in obj.tags}
                ways.append((obj.id, tags, [n.ref for n in obj.nodes]))
    return coords, signals, ways


def split_into_segments(ways):
    """Cut every way at intersections (nodes used by >1 way or >1 time) and at its ends."""
    use = Counter(r for _, _, refs in ways for r in refs)
    for way_id, tags, refs in ways:
        start = 0
        for i in range(1, len(refs)):
            if i == len(refs) - 1 or use[refs[i]] > 1:
                seg = refs[start:i + 1]
                if not (len(seg) == 2 and seg[0] == seg[1]):
                    yield way_id, tags, seg
                start = i


# ---------------------------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------------------------
def build():
    coords, signals, ways = read_osm()
    geod = Geod(ellps="WGS84")
    edges = []
    for way_id, tags, seg in split_into_segments(ways):
        if any(r not in coords for r in seg):
            continue  # node missing from the extract (should not happen with complete ways)
        lons, lats = zip(*(coords[r] for r in seg))
        length = geod.line_length(lons, lats)
        flags = {m: (allowed(tags, m), oneway(tags, m)) for m in MODES}
        for direction, nodes in ((1, seg), (-1, seg[::-1])):
            modes = {m: int(ok and ow in (0, direction)) for m, (ok, ow) in flags.items()}
            if not any(modes.values()):
                continue
            edges.append({
                "u": nodes[0], "v": nodes[-1], "way_id": way_id,
                "highway": tags["highway"], "name": tags.get("name", ""),
                "length_m": round(length, 2),
                "maxspeed": tags.get("maxspeed", ""), "lanes": tags.get("lanes", ""),
                "oneway": tags.get("oneway", ""), "junction": tags.get("junction", ""),
                "bridge": tags.get("bridge", ""), "tunnel": tags.get("tunnel", ""),
                "n_signals": sum(1 for r in nodes[1:] if r in signals),  # signals met when entering them
                **modes,
                "geometry": [coords[r] for r in nodes],
            })
    for i, e in enumerate(edges):
        e["edge_id"] = i
    return coords, signals, edges


def largest_scc(edges, mode, index):
    """Largest strongly connected component of the sub-graph a mode may use."""
    sub = [e for e in edges if e[mode]]
    nodes = {n for e in sub for n in (e["u"], e["v"])}
    if not sub:
        return set(), 0
    rows = [index[e["u"]] for e in sub]
    cols = [index[e["v"]] for e in sub]
    n = len(index)
    _, labels = connected_components(coo_matrix((np.ones(len(sub)), (rows, cols)), shape=(n, n)),
                                     directed=True, connection="strong")
    used = np.array([index[x] for x in nodes])
    biggest = np.bincount(labels[used]).argmax()
    rev = {i: x for x, i in index.items()}
    return {rev[i] for i in used if labels[i] == biggest}, len(nodes)


def main():
    t0 = time.time()
    coords, signals, edges = build()
    graph_nodes = sorted({n for e in edges for n in (e["u"], e["v"])})
    index = {n: i for i, n in enumerate(graph_nodes)}

    lez = shape(json.loads(LEZ.read_text(encoding="utf-8"))["features"][0]["geometry"])
    shapely.prepare(lez)
    in_lez = {n for n in graph_nodes if shapely.contains_xy(lez, *coords[n])}

    lcc, stats = {}, {}
    for m in MODES:
        lcc[m], n_mode = largest_scc(edges, m, index)
        for e in edges:
            e[f"lcc_{m}"] = int(e[m] and e["u"] in lcc[m] and e["v"] in lcc[m])
        stats[m] = {
            "edges": sum(e[m] for e in edges),
            "edges_in_lcc": sum(e[f"lcc_{m}"] for e in edges),
            "nodes": n_mode,
            "nodes_in_lcc": len(lcc[m]),
            "lez_nodes_in_lcc": len(lcc[m] & in_lez),
            "km_in_lcc": round(sum(e["length_m"] for e in edges if e[f"lcc_{m}"]) / 1000, 1),
        }

    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "nodes.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["node_id", "lon", "lat", "in_lez", "traffic_signals", *[f"lcc_{m}" for m in MODES]])
        for n in graph_nodes:
            w.writerow([n, f"{coords[n][0]:.7f}", f"{coords[n][1]:.7f}", int(n in in_lez), int(n in signals),
                        *[int(n in lcc[m]) for m in MODES]])

    cols = ["edge_id", "u", "v", "way_id", "highway", "name", "length_m", "maxspeed", "lanes", "oneway",
            "junction", "bridge", "tunnel", "n_signals", *MODES, *[f"lcc_{m}" for m in MODES]]
    with open(OUT / "edges.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([*cols, "geometry_wkt"])
        for e in edges:
            wkt = "LINESTRING (" + ", ".join(f"{x:.7f} {y:.7f}" for x, y in e["geometry"]) + ")"
            w.writerow([*(e[c] for c in cols), wkt])
    (OUT / "edges.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {c: e[c] for c in cols},
         "geometry": {"type": "LineString", "coordinates": e["geometry"]}} for e in edges]},
        ensure_ascii=False), encoding="utf-8")

    summary = {
        "source": SRC.name,
        "nodes": len(graph_nodes), "nodes_in_lez": len(in_lez),
        "directed_edges": len(edges), "traffic_signal_nodes": len(signals),
        "highway_types": dict(Counter(e["highway"] for e in edges).most_common()),
        "modes": stats,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    preview(edges, coords)

    print(f"nodes {len(graph_nodes):,} (in LEZ {len(in_lez):,}) | directed edges {len(edges):,} | "
          f"signal nodes {len(signals):,} | {time.time() - t0:.0f}s")
    print(f"{'mode':11s} {'edges':>7s} {'in LCC':>7s} {'nodes':>7s} {'in LCC':>7s} {'LEZ in LCC':>11s} {'km':>7s}")
    for m, s in stats.items():
        print(f"{m:11s} {s['edges']:7,} {s['edges_in_lcc']:7,} {s['nodes']:7,} {s['nodes_in_lcc']:7,} "
              f"{s['lez_nodes_in_lcc']:11,} {s['km_in_lcc']:7}")


def preview(edges, coords):
    lez = json.loads(LEZ.read_text(encoding="utf-8"))["features"][0]["geometry"]
    lez = shape(lez)
    fig, axes = plt.subplots(2, 2, figsize=(16, 13), dpi=100)
    for ax, m in zip(axes.flat, MODES):
        for e in edges:
            if e[m]:
                xs, ys = zip(*e["geometry"])
                ax.plot(xs, ys, lw=0.4 if e[f"lcc_{m}"] else 1.2, color="black" if e[f"lcc_{m}"] else "red")
        for p in getattr(lez, "geoms", [lez]):
            ax.plot(*p.exterior.xy, color="royalblue", lw=1.5)
        ax.set_aspect(1 / 0.983)
        ax.set_title(f"{m}: black = largest strongly connected component, red = cut off")
        ax.tick_params(labelsize=6)
    fig.savefig(OUT / "graph_preview.png", bbox_inches="tight")


if __name__ == "__main__":
    main()
