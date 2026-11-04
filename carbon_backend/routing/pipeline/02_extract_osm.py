"""Cut the Vietnam OSM extract down to the LEZ + 1 km buffer ("complete ways" strategy).

Keeps:
  * every node inside the buffer polygon,
  * every way with at least one node inside, together with ALL its nodes (no clipped edges),
  * every relation with a kept node/way as member (e.g. turn restrictions, routes).

Input : Vietnam extract (argument or OSM_PBF env var), data/lez/lez_buffer_1km.geojson
Output: data/osm/lez_buffer_1km.osm.pbf  (compact, for QGIS / pyosmium)
        data/osm/lez_buffer_1km.osm      (XML, for OSMnx graph_from_xml)
        data/osm/extract_preview.png
"""
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import osmium
import shapely
from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[1]
PBF = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("OSM_PBF", ""))  # Geofabrik vietnam-*.osm.pbf, kept outside the repo
POLY = ROOT / "data" / "lez" / "lez_buffer_1km.geojson"
OUT_DIR = ROOT / "data" / "osm"
OUT_PBF = OUT_DIR / "lez_buffer_1km.osm.pbf"
OUT_XML = OUT_DIR / "lez_buffer_1km.osm"


def select(polygon):
    """Pass 1: decide which nodes / ways / relations to keep."""
    minx, miny, maxx, maxy = polygon.bounds
    shapely.prepare(polygon)
    inside, ways, rels, needed = set(), set(), set(), set()
    for obj in osmium.FileProcessor(str(PBF)):
        if obj.is_node():
            loc = obj.location
            if loc.valid() and minx <= loc.lon <= maxx and miny <= loc.lat <= maxy \
                    and shapely.contains_xy(polygon, loc.lon, loc.lat):
                inside.add(obj.id)
        elif obj.is_way():
            refs = [n.ref for n in obj.nodes]
            if any(r in inside for r in refs):
                ways.add(obj.id)
                needed.update(refs)
        elif obj.is_relation():
            if any((m.type == "n" and m.ref in inside) or (m.type == "w" and m.ref in ways) for m in obj.members):
                rels.add(obj.id)
    return needed | inside, ways, rels


def write(nodes, ways, rels, bounds):
    """Pass 2: copy the selected objects (input order is preserved, so the output stays sorted)."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    header = osmium.io.Header()
    header.add_box(osmium.osm.Box(osmium.osm.Location(bounds[0], bounds[1]),
                                  osmium.osm.Location(bounds[2], bounds[3])))
    coords, highways = {}, []
    with osmium.SimpleWriter(str(OUT_PBF), overwrite=True, header=header) as w:
        for obj in osmium.FileProcessor(str(PBF)):
            if obj.is_node() and obj.id in nodes:
                w.add_node(obj)
                coords[obj.id] = (obj.location.lon, obj.location.lat)
            elif obj.is_way() and obj.id in ways:
                w.add_way(obj)
                if "highway" in obj.tags:
                    highways.append((obj.tags["highway"], [n.ref for n in obj.nodes]))
            elif obj.is_relation() and obj.id in rels:
                w.add_relation(obj)
    with osmium.SimpleWriter(str(OUT_XML), overwrite=True, header=header) as w:
        for obj in osmium.FileProcessor(str(OUT_PBF)):
            if obj.is_node():
                w.add_node(obj)
            elif obj.is_way():
                w.add_way(obj)
            else:
                w.add_relation(obj)
    return coords, highways


def preview(polygon, coords, highways):
    major = {"motorway", "trunk", "primary", "secondary", "tertiary"}
    fig, ax = plt.subplots(figsize=(11, 9), dpi=110)
    for hw, refs in highways:
        xy = [coords[r] for r in refs if r in coords]
        if len(xy) > 1:
            xs, ys = zip(*xy)
            base = hw.removesuffix("_link")
            ax.plot(xs, ys, lw=1.2 if base in major else 0.35, color="black" if base in major else "gray")
    lez = json.loads((ROOT / "data" / "lez" / "lez_zones.geojson").read_text(encoding="utf-8"))["features"]
    for f, c in zip(lez, ["red", "darkorange", "purple"]):
        g = shape(f["geometry"])
        for p in getattr(g, "geoms", [g]):
            ax.plot(*p.exterior.xy, color=c, lw=2)
    for p in getattr(polygon, "geoms", [polygon]):
        ax.plot(*p.exterior.xy, color="blue", lw=1, ls="--")
    ax.set_aspect(1 / 0.983)
    ax.set_title("OSM extract: roads (black = tertiary and above), LEZ zones, 1 km buffer (dashed)")
    fig.savefig(OUT_DIR / "extract_preview.png", bbox_inches="tight")


def main():
    if not PBF.is_file():
        sys.exit("usage: 02_extract_osm.py <vietnam-*.osm.pbf>  (or set OSM_PBF)")
    polygon = shape(json.loads(POLY.read_text(encoding="utf-8"))["features"][0]["geometry"])
    t0 = time.time()
    nodes, ways, rels = select(polygon)
    t1 = time.time()
    coords, highways = write(nodes, ways, rels, polygon.bounds)
    t2 = time.time()
    preview(polygon, coords, highways)

    print(f"source         : {PBF}")
    print(f"selected       : {len(nodes):,} nodes, {len(ways):,} ways, {len(rels):,} relations")
    print(f"highway ways   : {len(highways):,}")
    for hw, n in Counter(h for h, _ in highways).most_common(20):
        print(f"   {hw:16s} {n:6,}")
    print(f"time           : select {t1 - t0:.0f}s, write {t2 - t1:.0f}s")
    for p in (OUT_PBF, OUT_XML):
        print(f"output         : {p}  ({p.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
