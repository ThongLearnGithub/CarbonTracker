"""Graph data and the edge weight model (speed -> time, speed -> CO2).

Shared by the offline pipeline (04_edge_weights.py, 05_validation_sample.py) and the API.
"""
import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent  # carbon_backend/routing
GRAPH = ROOT / "data" / "graph"
WEIGHTS = ROOT / "data" / "weights"
CONFIG = ROOT / "config" / "weights_model.json"


def load_config(path=CONFIG):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_edges(with_geometry=False):
    """edges.csv -> dict of numpy arrays (plus string columns as lists)."""
    with open(GRAPH / "edges.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    ints = ["edge_id", "u", "v", "n_signals", "motorcycle", "car", "bicycle", "foot",
            "lcc_motorcycle", "lcc_car", "lcc_bicycle", "lcc_foot"]
    cols = {c: np.array([int(r[c]) for r in rows], dtype=np.int64) for c in ints}
    cols["length_m"] = np.array([float(r["length_m"]) for r in rows])
    cols["maxspeed"] = np.array([_maxspeed(r["maxspeed"]) for r in rows])
    for c in ("highway", "name"):
        cols[c] = [r[c] for r in rows]
    if with_geometry:
        cols["geometry_wkt"] = [r["geometry_wkt"] for r in rows]
    return cols


def load_nodes():
    with open(GRAPH / "nodes.csv", encoding="utf-8") as f:
        return {int(r["node_id"]): r for r in csv.DictReader(f)}


def _maxspeed(value):
    """OSM maxspeed -> km/h (nan if missing / not numeric). Values like '50;40' take the lowest."""
    try:
        return min(float(x) for x in value.replace(" ", "").split(";") if x)
    except ValueError:
        return np.nan


def slot_for_time(cfg, hhmm):
    """'17:30' -> 'peak' if inside one of cfg['peak_hours'], else 'offpeak'."""
    minutes = lambda s: int(s[:2]) * 60 + int(s[3:5])
    t = minutes(hhmm)
    return "peak" if any(minutes(a) <= t < minutes(b) for a, b in cfg["peak_hours"]) else "offpeak"


# ---------------------------------------------------------------------------------------------
# Weight model
# ---------------------------------------------------------------------------------------------
def speed_kmh(edges, cfg, speed_class, slot):
    """Running speed per edge (km/h) for one speed class and time slot, before signal delay."""
    table = cfg["speeds_kmh"][speed_class]
    base = np.array([table.get(hw, table["default"]) for hw in edges["highway"]], dtype=float)
    if speed_class in ("motorcycle", "car"):
        base = np.fmin(base, edges["maxspeed"])  # fmin ignores nan (no maxspeed tag)
    if slot == "peak":
        major = set(cfg["major_roads"])
        f = cfg["peak_factor"][speed_class]
        base *= np.array([f["major"] if hw in major else f["minor"] for hw in edges["highway"]])
    return base


def travel_time_s(edges, cfg, speed_class, slot):
    v = speed_kmh(edges, cfg, speed_class, slot)
    return edges["length_m"] / (v / 3.6) + edges["n_signals"] * cfg["signal_delay_s"][speed_class][slot]


def co2_g_per_km(energy, v_kmh):
    """CO2 per km at average speed v. COPERT form: EC = (a v^2 + b v + g + d/v) / (e v^2 + z v + h) * (1 - RF), MJ/km."""
    if energy is None:
        return np.zeros_like(np.asarray(v_kmh, dtype=float))
    if energy["type"] == "electric":
        return np.full_like(np.asarray(v_kmh, dtype=float), energy["wh_per_km"] * energy["grid_kg_co2_per_kwh"])
    v = np.clip(np.asarray(v_kmh, dtype=float), energy["v_min"], energy["v_max"])
    ec = ((energy["alpha"] * v**2 + energy["beta"] * v + energy["gamma"] + energy["delta"] / v)
          / (energy["epsilon"] * v**2 + energy["zita"] * v + energy["hta"]) * (1 - energy["reduction_factor"]))
    return ec * energy["co2_g_per_mj"]


def edge_weights(edges, cfg, profile, slot):
    """(t seconds, CO2 grams) per edge. CO2 uses the edge's average speed including signal waiting."""
    p = cfg["profiles"][profile]
    t = travel_time_s(edges, cfg, p["speed_class"], slot)
    v_avg = edges["length_m"] / t * 3.6
    c = co2_g_per_km(p["energy"], v_avg) * edges["length_m"] / 1000
    return t, c
