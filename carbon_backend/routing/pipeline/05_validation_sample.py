"""Validation sample for the manual Google Maps check.

Samples origin/destination pairs inside the LEZ (stratified by zone pair), routes each with the model's
fastest path (petrol motorcycle, off-peak and peak), and writes an Excel sheet with a Google Maps link per
pair and empty columns for the times/distances read from Google. Every 4th pair is a held-out test pair:
it is not used to fit the speeds, only to report the error after calibration.

Input : data/graph/*, data/lez/lez_zones.geojson, config/weights_model.json
Output: data/validation/google_check.xlsx   (fill in the yellow columns)
        data/validation/od_pairs.csv, model_routes.geojson (open in QGIS)
"""
import csv
import json
import random
import sys
from pathlib import Path

import numpy as np
import shapely
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from pyproj import Geod
from shapely.geometry import shape

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # carbon_backend
from routing.algorithms import Graph, shortest_path
from routing.model import ROOT, edge_weights, load_config, load_edges, load_nodes

OUT = ROOT / "data" / "validation"
ZONES = ROOT / "data" / "lez" / "lez_zones.geojson"
PROFILE = "motorcycle_petrol"
SEED = 2026
# (zone A, zone B, number of pairs); zone keys: Q1, Q3, TT (Thu Thiem peninsula)
STRATA = [("Q1", "Q3", 8), ("Q1", "TT", 8), ("Q3", "TT", 6), ("Q1", "Q1", 6), ("Q3", "Q3", 6), ("TT", "TT", 6)]
MIN_KM, MAX_KM = 1.0, 6.0  # straight-line distance between origin and destination
# O/D nodes must touch a named street of these classes, so Google snaps them to the same road.
OD_ROADS = {"primary", "secondary", "tertiary", "residential", "unclassified", "living_street"}


def zone_of(lon, lat, zones):
    for key, poly in zones.items():
        if shapely.contains_xy(poly, lon, lat):
            return key
    return None


def candidate_nodes(edges, nodes, zones):
    """LEZ nodes reachable by motorcycle and car, on a named street suitable for Google."""
    names = {}
    for i, hw in enumerate(edges["highway"]):
        if hw in OD_ROADS and edges["name"][i]:
            names.setdefault(int(edges["u"][i]), edges["name"][i])
    by_zone = {k: [] for k in zones}
    for nid, n in nodes.items():
        if n["in_lez"] == "1" and n["lcc_motorcycle"] == "1" and n["lcc_car"] == "1" and nid in names:
            z = zone_of(float(n["lon"]), float(n["lat"]), zones)
            if z:
                by_zone[z].append(nid)
    return by_zone, names


def sample_pairs(by_zone, nodes, geod, rng):
    pairs = []
    for za, zb, k in STRATA:
        got = 0
        while got < k:
            a, b = rng.choice(by_zone[za]), rng.choice(by_zone[zb])
            (lon1, lat1), (lon2, lat2) = [(float(nodes[x]["lon"]), float(nodes[x]["lat"])) for x in (a, b)]
            km = geod.inv(lon1, lat1, lon2, lat2)[2] / 1000
            if a != b and MIN_KM <= km <= MAX_KM:
                pairs.append((za, zb, a, b, km))
                got += 1
    return pairs


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = load_config()
    edges, nodes = load_edges(with_geometry=True), load_nodes()
    zones = {key: shape(f["geometry"]) for key, f in zip(("Q1", "Q3", "TT"),
             json.loads(ZONES.read_text(encoding="utf-8"))["features"])}
    for p in zones.values():
        shapely.prepare(p)
    geod, rng = Geod(ellps="WGS84"), random.Random(SEED)

    by_zone, names = candidate_nodes(edges, nodes, zones)
    pairs = sample_pairs(by_zone, nodes, geod, rng)
    graph = Graph(edges, cfg["profiles"][PROFILE]["graph_mode"])
    weights = {slot: edge_weights(edges, cfg, PROFILE, slot) for slot in cfg["slots"]}

    rows, features = [], []
    for i, (za, zb, a, b, km) in enumerate(pairs, start=1):
        row = {"id": i, "set": "test" if i % 4 == 0 else "calib", "zones": f"{za} → {zb}",
               "origin": a, "dest": b, "crow_km": km,
               "o_lat": float(nodes[a]["lat"]), "o_lon": float(nodes[a]["lon"]), "o_name": names[a],
               "d_lat": float(nodes[b]["lat"]), "d_lon": float(nodes[b]["lon"]), "d_name": names[b]}
        for slot, (t, c) in weights.items():
            path = shortest_path(graph, a, b, t.tolist())
            row[f"{slot}_min"] = t[path].sum() / 60
            row[f"{slot}_km"] = edges["length_m"][path].sum() / 1000
            row[f"{slot}_co2_g"] = c[path].sum()
            features.append({"type": "Feature", "properties": {"id": i, "slot": slot, "minutes": round(row[f"{slot}_min"], 1),
                             "km": round(row[f"{slot}_km"], 2), "co2_g": round(row[f"{slot}_co2_g"], 1)},
                             "geometry": shapely.geometry.mapping(shapely.line_merge(shapely.multilinestrings(
                                 [shapely.from_wkt(edges["geometry_wkt"][e]) for e in path])))})
        rows.append(row)

    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "od_pairs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    (OUT / "model_routes.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": features},
                                                         ensure_ascii=False), encoding="utf-8")
    write_excel(rows, cfg)

    ratio = np.array([r["offpeak_km"] / r["crow_km"] for r in rows])
    print(f"pairs   : {len(rows)} ({sum(r['set'] == 'test' for r in rows)} test)")
    print(f"route/crow-fly distance ratio: median {np.median(ratio):.2f}, max {ratio.max():.2f}")
    print(f"minutes : off-peak median {np.median([r['offpeak_min'] for r in rows]):.1f}, "
          f"peak median {np.median([r['peak_min'] for r in rows]):.1f}")
    print(f"output  : {OUT / 'google_check.xlsx'}")


HELP = [
    "KIỂM TRA THỜI GIAN ĐI BẰNG GOOGLE MAPS (xe máy)",
    "",
    "Mục đích: so thời gian của mô hình với Google để hiệu chỉnh tốc độ. Chỉ điền các cột màu vàng ở sheet 'Kiem tra'.",
    "",
    "Cho mỗi dòng:",
    "1. Bấm link ở cột 'Google Maps' (trên điện thoại sẽ mở app Google Maps).",
    "2. Chọn chế độ XE MÁY (biểu tượng xe máy). Nếu không có, chọn ô tô và ghi 'ô tô' vào cột Ghi chú.",
    "3. Chọn 'Khởi hành lúc' (Depart at) → một ngày THỨ BA sắp tới, giờ {offpeak} → ghi thời gian Google báo.",
    "   Google thường báo một khoảng, ví dụ 'thường mất 12-18 phút': ghi 12 vào cột 'min', 18 vào cột 'max'.",
    "   Nếu chỉ có một con số, ghi số đó vào cả hai cột.",
    "4. Ghi quãng đường (km) của tuyến Google đề xuất ĐẦU TIÊN.",
    "5. Đổi giờ sang {peak} (cùng ngày Thứ Ba) → ghi tiếp như bước 3-4.",
    "6. Nếu app xe máy không cho chọn giờ khởi hành: xem trực tiếp đúng khung giờ đó, ghi ngày giờ thực tế vào Ghi chú.",
    "",
    "Lưu ý:",
    "- Điểm đi/đến nằm trên con đường ghi ở cột 'Đường (đi)' / 'Đường (đến)'. Nếu Google ghim sai đường, kéo lại cho đúng.",
    "- Cột 'Mô hình ...' là kết quả hiện tại của mô hình (tốc độ giả định), chỉ để tham khảo, không cần sửa.",
    "- Các dòng nhóm 'test' giữ riêng để đánh giá sai số sau khi hiệu chỉnh; vẫn điền bình thường.",
    "- Mất khoảng 1-2 phút mỗi dòng. Không dùng công cụ tự động lấy dữ liệu Google (vi phạm điều khoản).",
    "",
    "Tuyến của mô hình: data/validation/model_routes.geojson (mở bằng QGIS, lọc theo id) để so hình dạng tuyến với Google.",
]


def write_excel(rows, cfg):
    wb = Workbook()
    ws = wb.active
    ws.title = "Huong dan"
    for line in HELP:
        ws.append([line.format(offpeak=cfg["slots"]["offpeak"]["depart"], peak=cfg["slots"]["peak"]["depart"])])
    ws["A1"].font = Font(bold=True, size=13)
    ws.column_dimensions["A"].width = 130

    ws = wb.create_sheet("Kiem tra")
    off, peak = cfg["slots"]["offpeak"]["depart"], cfg["slots"]["peak"]["depart"]
    header = ["id", "Nhóm", "Vùng", "Đường (đi)", "Đường (đến)", "Google Maps",
              f"Mô hình {off} (phút)", f"Mô hình {off} (km)", f"Mô hình {peak} (phút)", f"Mô hình {peak} (km)",
              f"Google {off} min (phút)", f"Google {off} max (phút)", f"Google {off} (km)",
              f"Google {peak} min (phút)", f"Google {peak} max (phút)", f"Google {peak} (km)",
              "Ghi chú", "Điểm đi (lat, lon)", "Điểm đến (lat, lon)"]
    ws.append(header)
    yellow = PatternFill("solid", fgColor="FFF2CC")
    for r in rows:
        url = (f"https://www.google.com/maps/dir/?api=1&origin={r['o_lat']:.6f},{r['o_lon']:.6f}"
               f"&destination={r['d_lat']:.6f},{r['d_lon']:.6f}&travelmode=driving")
        ws.append([r["id"], r["set"], r["zones"], r["o_name"], r["d_name"], "Mở chỉ đường",
                   round(r["offpeak_min"], 1), round(r["offpeak_km"], 2), round(r["peak_min"], 1), round(r["peak_km"], 2),
                   None, None, None, None, None, None, None,
                   f"{r['o_lat']:.6f}, {r['o_lon']:.6f}", f"{r['d_lat']:.6f}, {r['d_lon']:.6f}"])
        link = ws.cell(row=ws.max_row, column=6)
        link.hyperlink, link.style = url, "Hyperlink"
        for col in range(11, 18):
            ws.cell(row=ws.max_row, column=col).fill = yellow
    for col in range(11, 18):
        ws.cell(row=1, column=col).fill = yellow
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    widths = [5, 7, 10, 26, 26, 14, 11, 11, 11, 11, 11, 11, 10, 11, 11, 10, 24, 22, 22]
    for i, wdt in enumerate(widths, start=1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = wdt
    ws.row_dimensions[1].height = 45
    ws.freeze_panes = "D2"
    wb.active = 1
    wb.save(OUT / "google_check.xlsx")


if __name__ == "__main__":
    main()
