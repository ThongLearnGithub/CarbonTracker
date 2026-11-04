"""Edge weights: travel time t and CO2 c for every (vehicle profile, time slot).

Model (all parameters in config/weights_model.json)
  * running speed v = off-peak speed of the highway class, capped by OSM maxspeed, x peak factor at peak;
  * t = length / v + n_signals x signal delay;
  * c = length x CO2/km(v_avg), v_avg = length / t (so waiting at signals raises CO2/km);
    petrol: COPERT energy curve (EMEP/EEA) x 69.3 g CO2/MJ; electric: Wh/km x grid factor; bicycle/foot: 0.

Input : data/graph/edges.csv, config/weights_model.json
Output: data/weights/edge_weights.csv  (edge_id, t_<profile>_<slot> [s], co2_<profile>_<slot> [g];
                                        empty where the profile's mode may not use the edge)
        data/weights/summary.json, data/weights/co2_curves.png
"""
import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # carbon_backend
from routing.model import WEIGHTS, co2_g_per_km, edge_weights, load_config, load_edges

SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]  # categorical slots 1-3


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = load_config()
    edges = load_edges()
    WEIGHTS.mkdir(parents=True, exist_ok=True)

    columns, summary = {}, {}
    for profile, p in cfg["profiles"].items():
        usable = edges[p["graph_mode"]] == 1
        lcc = usable & (edges[f"lcc_{p['graph_mode']}"] == 1)
        for slot in cfg["slots"]:
            t, c = edge_weights(edges, cfg, profile, slot)
            columns[f"t_{profile}_{slot}"] = np.where(usable, t, np.nan)
            if p["energy"] is not None:
                columns[f"co2_{profile}_{slot}"] = np.where(usable, c, np.nan)
            km = edges["length_m"][lcc].sum() / 1000
            summary[f"{profile}/{slot}"] = {
                "mean_speed_kmh": round(km / (t[lcc].sum() / 3600), 1),
                "mean_co2_g_per_km": round(c[lcc].sum() / km, 1),
            }

    with open(WEIGHTS / "edge_weights.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["edge_id", *columns])
        for i, eid in enumerate(edges["edge_id"]):
            w.writerow([eid, *("" if np.isnan(col[i]) else f"{col[i]:.2f}" for col in columns.values())])
    (WEIGHTS / "summary.json").write_text(json.dumps(
        {"config": "config/weights_model.json", "network_means_lcc": summary}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    plot_curves(cfg)

    print(f"edges   : {len(edges['edge_id']):,}   columns: {len(columns)}")
    print(f"{'profile/slot':32s} {'speed km/h':>10s} {'CO2 g/km':>9s}")
    for k, s in summary.items():
        print(f"{k:32s} {s['mean_speed_kmh']:10.1f} {s['mean_co2_g_per_km']:9.1f}")
    print(f"output  : {WEIGHTS / 'edge_weights.csv'}")


def plot_curves(cfg):
    v = np.linspace(5, 60, 221)
    fig, ax = plt.subplots(figsize=(8, 4.8), dpi=120)
    profiles = [k for k, p in cfg["profiles"].items() if p["energy"] is not None]
    for color, profile in zip(SERIES, profiles):
        y = co2_g_per_km(cfg["profiles"][profile]["energy"], v)
        ax.plot(v, y, color=color, lw=2, label=cfg["profiles"][profile]["label"])
        ax.annotate(f"{y[-1]:.0f}", (v[-1], y[-1]), xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=9, color="#52514e")
    ax.axvspan(10, 30, color="#f0efec", zorder=0)
    ax.text(20, 35, "dải tốc độ nội đô", ha="center", va="center", fontsize=9, color="#52514e")
    ax.set_xlabel("Tốc độ trung bình trên cạnh (km/h)")
    ax.set_ylabel("g CO₂ / km")
    ax.set_title("CO₂ theo tốc độ (EMEP/EEA COPERT; xe điện = Wh/km × hệ số lưới)", fontsize=11, loc="left")
    ax.set_ylim(bottom=0)
    ax.grid(axis="y", color="#e6e5e0", lw=0.8)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(frameon=False, fontsize=9)
    fig.savefig(WEIGHTS / "co2_curves.png", bbox_inches="tight", facecolor="#fcfcfb")


if __name__ == "__main__":
    main()
