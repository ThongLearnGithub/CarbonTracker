"""Build the LEZ study-area polygon: old District 1 + old District 3 + Thu Thiem peninsula.

Inputs  (from 00_export_sources.cmd):
    data/sources/admin_boundaries.geojson     Q1 (rel 2587287), Q3 (rel 3819816), Phuong An Khanh (rel 7351897)
    data/sources/tran_nao_candidates.geojson  Tran Nao road segments
Outputs:
    data/lez/lez_zones.geojson        one feature per zone (Q1, Q3, Thu Thiem)
    data/lez/lez_union.geojson        the LEZ as a single (multi)polygon -> sample origin/destination points here
    data/lez/lez_buffer_1km.geojson   LEZ + 1 km buffer -> extent of the road graph
    data/lez/lez_preview.png

Thu Thiem definition (assumption, verify against the official Thu Thiem plan):
    the part of the new Phuong An Khanh west of Tran Nao road and south of Cau Sai Gon,
    closed to the Saigon River along Rach Ca Tre Lon (south end of Tran Nao -> river).
"""
import json
import unicodedata
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import shapely
from pyproj import Transformer
from shapely import ops
from shapely.geometry import LineString, Polygon, mapping, shape

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "sources"
OUT = ROOT / "data" / "lez"
BUFFER_M = 1000

REL_Q1, REL_Q3, REL_AN_KHANH = "2587287", "3819816", "7351897"
# Where Rach Ca Tre Lon meets the Saigon River (read off the OSM water polygons).
RACH_CA_TRE_MOUTH = (106.7345, 10.7768)
# Tran Nao vertices north of this latitude belong to the Cau Sai Gon / Xa lo Ha Noi interchange.
TRAN_NAO_NORTH_LAT = 10.7980
LAT_BAND = 0.0005  # ~55 m

_TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:32648", always_xy=True)  # UTM 48N, metres
_TO_WGS = Transformer.from_crs("EPSG:32648", "EPSG:4326", always_xy=True)


def _reproject(transformer):
    return lambda geom: shapely.transform(
        geom, lambda xy: np.column_stack(transformer.transform(xy[:, 0], xy[:, 1])))


to_utm, to_wgs = _reproject(_TO_UTM), _reproject(_TO_WGS)


def nfc(s):
    return unicodedata.normalize("NFC", s or "")


def load(name):
    return json.loads((SRC / name).read_text(encoding="utf-8"))["features"]


def area_km2(geom):
    return to_utm(geom).area / 1e6


def tran_nao_line():
    """Centre line of Tran Nao from just south of the Cau Sai Gon interchange to its south end.

    The road is split into many ways (dual carriageway + interchange ramps), so instead of
    merging ways we average all its vertices per latitude band.
    """
    segs = [shape(f["geometry"]) for f in load("tran_nao_candidates.geojson")
            if nfc(f["properties"].get("name")) == nfc("Trần Não")]
    if not segs:
        raise SystemExit("Tran Nao road not found in sources")
    bands = {}
    for g in segs:
        for lon, lat in g.coords:
            if lat <= TRAN_NAO_NORTH_LAT:
                bands.setdefault(round(lat / LAT_BAND), []).append((lon, lat))
    coords = [tuple(np.mean(pts, axis=0)) for _, pts in sorted(bands.items(), reverse=True)]  # north -> south
    return LineString(coords)


def build_thu_thiem(an_khanh):
    road = tran_nao_line()
    north, south = road.coords[0], road.coords[-1]
    # Everything west of Tran Nao, south of the Cau Sai Gon latitude, closed along Rach Ca Tre Lon.
    cutter = Polygon([
        (106.690, north[1]), north, *road.coords[1:-1], south,
        RACH_CA_TRE_MOUTH, (RACH_CA_TRE_MOUTH[0], 10.740), (106.690, 10.740),
    ])
    tt = an_khanh.intersection(cutter)
    # keep only the main peninsula piece (drop tiny slivers created by the cut)
    parts = list(getattr(tt, "geoms", [tt]))
    return max(parts, key=area_km2), road


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    admin = {f["properties"]["osm_id"]: shape(f["geometry"]) for f in load("admin_boundaries.geojson")}
    missing = {REL_Q1, REL_Q3, REL_AN_KHANH} - admin.keys()
    if missing:
        raise SystemExit(f"Missing boundary relations: {missing}")

    q1, q3 = admin[REL_Q1].buffer(0), admin[REL_Q3].buffer(0)
    thu_thiem, road = build_thu_thiem(admin[REL_AN_KHANH].buffer(0))

    zones = [
        ("Quận 1 (cũ)", "OSM relation 2587287, boundary=historic, end_date=2025-06-30", q1),
        ("Quận 3 (cũ)", "OSM relation 3819816, boundary=historic, end_date=2025-06-30", q3),
        ("Thủ Thiêm (bán đảo)", "Phường An Khánh (OSM relation 7351897) cut at Trần Não + rạch Cá Trê Lớn", thu_thiem),
    ]
    union = ops.unary_union([z[2] for z in zones])
    buffered = to_wgs(to_utm(union).buffer(BUFFER_M))

    def write(name, features):
        fc = {"type": "FeatureCollection", "features": features}
        (OUT / name).write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")

    write("lez_zones.geojson", [
        {"type": "Feature", "properties": {"name": n, "source": s, "area_km2": round(area_km2(g), 3)},
         "geometry": mapping(g)} for n, s, g in zones])
    write("lez_union.geojson", [
        {"type": "Feature", "properties": {"name": "LEZ", "area_km2": round(area_km2(union), 3)},
         "geometry": mapping(union)}])
    write("lez_buffer_1km.geojson", [
        {"type": "Feature", "properties": {"name": f"LEZ + {BUFFER_M} m", "area_km2": round(area_km2(buffered), 3)},
         "geometry": mapping(buffered)}])

    for n, _, g in zones:
        print(f"{n:22s} {area_km2(g):6.2f} km2")
    print(f"{'LEZ union':22s} {area_km2(union):6.2f} km2")
    print(f"{'LEZ + 1 km buffer':22s} {area_km2(buffered):6.2f} km2   bbox {tuple(round(v, 4) for v in buffered.bounds)}")

    fig, ax = plt.subplots(figsize=(10, 9), dpi=110)
    for (n, _, g), c in zip(zones, ["red", "darkorange", "purple"]):
        for p in getattr(g, "geoms", [g]):
            ax.fill(*p.exterior.xy, color=c, alpha=0.25)
            ax.plot(*p.exterior.xy, color=c, lw=1.5)
        ax.annotate(n, (g.representative_point().x, g.representative_point().y), fontsize=9, weight="bold")
    for p in getattr(buffered, "geoms", [buffered]):
        ax.plot(*p.exterior.xy, color="black", lw=1, ls="--")
    ax.plot(*road.xy, color="navy", lw=1.5)
    ax.set_aspect(1 / 0.983)
    ax.grid(True, lw=0.3)
    ax.set_title("LEZ = Q1 cu + Q3 cu + Thu Thiem; dashed = 1 km buffer; navy = Tran Nao")
    fig.savefig(OUT / "lez_preview.png", bbox_inches="tight")


if __name__ == "__main__":
    main()
