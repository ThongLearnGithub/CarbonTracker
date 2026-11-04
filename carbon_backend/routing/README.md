# Routing Engine – study area (LEZ)

Low-carbon route recommendation for GreenMove, as a module of `carbon_backend`. The API runs inside the
backend (`../routing_routes.py`, prefix `/routing`); `pipeline/` builds the data offline from the Vietnam
OpenStreetMap extract.

```text
carbon_backend/
├── main.py                 # include_router(routing_router); loads the graph at start-up
├── routing_routes.py       # HTTP endpoints /routing/...
└── routing/
    ├── model.py            # weight model (speed -> time, speed -> CO2)
    ├── algorithms.py       # Dijkstra/A*, Yen, LARAC, BOA*
    ├── service.py          # RoutingEngine: snapping + route queries
    ├── static/index.html   # test map (/routing/map)
    ├── config/weights_model.json
    ├── data/               # pipeline outputs; the API reads graph/, lez/ and the config
    └── pipeline/           # offline steps 00-05 + extra requirements
```

## Study area

LEZ = old District 1 + old District 3 + the Thu Thiem peninsula, with a 1 km buffer for the road graph.

| Zone | Source | Area |
|---|---|---|
| Quận 1 (cũ) | OSM relation 2587287 (`boundary=historic`, `end_date=2025-06-30`) | 7.70 km² |
| Quận 3 (cũ) | OSM relation 3819816 (`boundary=historic`, `end_date=2025-06-30`) | 4.93 km² |
| Thủ Thiêm (bán đảo) | Phường An Khánh (new ward, OSM relation 7351897) cut at Trần Não + rạch Cá Trê Lớn | 7.65 km² |
| **LEZ** | union of the three | **20.28 km²** |
| LEZ + 1 km | road-graph extent | 48.83 km² |

- Origin/destination points for experiments are sampled **inside the LEZ only** (`lez_union.geojson`);
  the 1 km buffer only exists so routes near the edge are not forced into detours.
- Assumption to verify: the Thu Thiem polygon is the land west of Trần Não and south of Cầu Sài Gòn,
  closed to the river along rạch Cá Trê Lớn. Ward boundaries run along the river centre line, so the
  polygon includes half the river width (larger than the ~6.5 km² Thu Thiem New Urban Area).
- Quận 2 and the old Phường Thủ Thiêm no longer exist as boundaries in OSM (merged in 2021 / 2025).

## Data

- `vietnam-261012.osm.pbf` (Geofabrik, 2026-10-12), © OpenStreetMap contributors, ODbL. Kept outside the
  repo (330 MB); point `OSM_PBF` at it.

## Pipeline

Only needed to rebuild the data (new OSM extract, changed access rules or speed assumptions). Uses the
backend venv plus the pipeline packages. Run from `carbon_backend`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r routing\pipeline\requirements.txt
$env:OSM_PBF = "D:\Thesis\vietnam-261012.osm.pbf"

routing\pipeline\00_export_sources.cmd                               # needs QGIS (GDAL ogr2ogr); set QGIS_BIN if not 4.2.3
.\.venv\Scripts\python.exe routing\pipeline\01_build_lez_polygon.py   # -> data/lez/*.geojson + lez_preview.png
.\.venv\Scripts\python.exe routing\pipeline\02_extract_osm.py         # -> data/osm/lez_buffer_1km.osm(.pbf), ~4 min
.\.venv\Scripts\python.exe routing\pipeline\03_build_graph.py         # -> data/graph/*, ~1 min
.\.venv\Scripts\python.exe routing\pipeline\04_edge_weights.py        # -> data/weights/*, seconds
.\.venv\Scripts\python.exe routing\pipeline\05_validation_sample.py   # -> data/validation/google_check.xlsx
```

`data/osm/`, `data/graph/edges.geojson` and `data/weights/edge_weights.csv` are not in Git (large, rebuilt by
steps 02-04, not read by the API). Changing `config/weights_model.json` needs no pipeline run: the API
computes the weights at start-up, so restarting the backend is enough.

`02_extract_osm.py` keeps every way that touches the buffer **with all its nodes** (like
`osmium extract --strategy complete_ways`), so no road edge is clipped at the boundary.

## Outputs

| File | Use |
|---|---|
| `data/lez/lez_zones.geojson` | the three zones (open in QGIS to check) |
| `data/lez/lez_union.geojson` | LEZ polygon – sample O/D points here |
| `data/lez/lez_buffer_1km.geojson` | road-graph extent |
| `data/osm/lez_buffer_1km.osm.pbf` | OSM extract (2.4 MB) – QGIS / pyosmium |
| `data/osm/lez_buffer_1km.osm` | same, XML (37 MB) – OSMnx `graph_from_xml` |

Extract contents (2026-10-12 data): 177,334 nodes, 36,245 ways (17,551 `highway=*`), 1,387 relations.

## Road graph (`03_build_graph.py`)

Directed graph: a **node** is a road end or a junction of road ways; an **edge** is the road piece between
two nodes, one record per travel direction. Each edge has a 0/1 flag per mode saying whether that mode may
travel `u -> v`. Length is the geodesic length of the full OSM geometry. Speed, time and CO₂ are added in
the next step (speed model); `highway`, `maxspeed`, `lanes` and `n_signals` are kept for it.

**Access rules** (documented assumptions):

| Highway | Default modes |
|---|---|
| trunk, primary, secondary, tertiary (+ links), unclassified, residential, living_street, service, road, track | motorcycle, car, bicycle, foot |
| motorway (+ link) | car only (Vietnamese law: no motorcycles / bicycles / pedestrians on expressways) |
| pedestrian, footway, steps, bridleway | foot |
| path | foot, bicycle |
| cycleway | bicycle, foot |
| busway | none (bus only) |
| construction, proposed, platform, corridor, `area=yes` | dropped |

- Access tags override defaults, most specific key first: motorcycle → `motorcycle`, `motor_vehicle`,
  `vehicle`, `access`; car → `motorcar`, `motor_vehicle`, `vehicle`, `access`; bicycle → `bicycle`,
  `vehicle`, `access`; foot → `foot`, `access`. `private`, `no`, … deny; `yes`, `designated`,
  `destination`, … allow. `motorroad=yes` excludes bicycles and pedestrians.
- One-way: `oneway:<mode>` overrides `oneway`; roundabouts and motorways are one-way by default;
  pedestrians ignore one-way streets; `cycleway=opposite*` allows contra-flow cycling.
- Not modelled yet: turn restrictions (`type=restriction` relations are kept in the extract), time-of-day
  (`:conditional`) restrictions.

**Result** (2026-10-12 data): 26,758 nodes (9,668 inside the LEZ), 69,784 directed edges, 870 traffic-signal nodes.

| Mode | Directed edges | In largest SCC | LEZ nodes in largest SCC | km (directed) |
|---|---|---|---|---|
| motorcycle | 53,767 | 53,222 (99.0 %) | 7,758 | 2,261 |
| car | 46,676 | 45,048 (96.5 %) | 7,315 | 1,978 |
| bicycle | 54,211 | 53,587 (98.8 %) | 7,856 | 2,276 |
| foot | 69,532 | 69,110 (99.4 %) | 9,504 | 2,913 |

- Routing must use the **largest strongly connected component** of each mode (`lcc_<mode>` columns),
  otherwise some origin/destination pairs have no route. Cut-off pieces are mostly one-way roads leaving
  the extract and a few alley clusters.
- Cars have ~7,000 fewer edges than motorcycles: 2,111 ways (mostly alleys tagged `service`/`residential`)
  are `motor_vehicle=no` or `motorcar=no` with `motorcycle=yes` — motorcycle-only alleys.
- The Saigon River tunnel (Hầm Thủ Thiêm) is mapped as separate car tubes and motorcycle lanes; the
  graph keeps that separation.

| File | Content |
|---|---|
| `data/graph/nodes.csv` | `node_id, lon, lat, in_lez, traffic_signals, lcc_<mode>` |
| `data/graph/edges.csv` | `edge_id, u, v, way_id, highway, name, length_m, maxspeed, lanes, oneway, junction, bridge, tunnel, n_signals, <mode>, lcc_<mode>, geometry_wkt` |
| `data/graph/edges.geojson` | same edges for QGIS (filter e.g. `"lcc_motorcycle" = 1`) |
| `data/graph/summary.json`, `graph_preview.png` | statistics and per-mode connectivity map |

## Edge weights (`04_edge_weights.py`)

Every edge gets a travel time `t` (s) and CO₂ `c` (g) per **vehicle profile × time slot**. All parameters are
in `config/weights_model.json`; speeds, peak factors and signal delays are **assumptions until calibrated**.

| Profile | Graph mode | CO₂ model |
|---|---|---|
| `motorcycle_petrol` | motorcycle | COPERT energy curve, L-category 4-stroke <250 cm³, Euro 2 (VN level 2) |
| `car_petrol` | car | COPERT energy curve, passenger car petrol Small, Euro 5 PFI (VN level 5) |
| `motorcycle_electric` | motorcycle | 25 Wh/km (assumption) × grid 0.6592 kg CO₂/kWh (VN 2023) |
| `bicycle`, `foot` | bicycle, foot | 0 (time only) |

Time slots: `offpeak` (10:00–15:00) and `peak` (17:00–19:00).

- Speed: off-peak running speed per highway class (e.g. motorcycle primary 30, residential 20, service/alley
  15 km/h), capped by OSM `maxspeed` where tagged, × peak factor at peak (motorcycle 0.65 major / 0.80 minor roads).
- `t = length / v + n_signals × signal delay` (motorcycle 15 s off-peak, 30 s peak).
- `c = length × CO₂/km(v_avg)` with `v_avg = length / t`, so waiting at signals raises CO₂ per km.
  COPERT: `EC = (αv² + βv + γ + δ/v) / (εv² + ζv + η) × (1 − RF)` in MJ/km, coefficients from the
  EMEP/EEA Guidebook 2023 (v2026) chapter 1.A.3.b.i-iv Appendix 4 (`HOT_EMISSIONS_PARAMETERS`, pollutant `EC`);
  CO₂ = EC × 69.3 g/MJ (IPCC 2006 motor gasoline). Speed is clamped to the curve's validity range
  (motorcycle 10–100 km/h, car 5–130 km/h).
- Caveat: COPERT curves are fitted on trip-average speeds; applying them per edge is the usual eco-routing
  approximation. Cold starts are not modelled.

| File | Content |
|---|---|
| `data/weights/edge_weights.csv` | `edge_id, t_<profile>_<slot>, co2_<profile>_<slot>`; empty where the mode may not use the edge |
| `data/weights/summary.json` | length-weighted network mean speed and CO₂/km per profile and slot |
| `data/weights/co2_curves.png` | CO₂ per km against speed for the three motor profiles |

## Google Maps check (`05_validation_sample.py`)

40 origin/destination pairs inside the LEZ (stratified: Q1–Q3, Q1–Thủ Thiêm, Q3–Thủ Thiêm, and within each
zone; 1–6 km apart; seed 2026), routed by the model's fastest path for `motorcycle_petrol` in both slots.
`google_check.xlsx` has one row per pair with a Google Maps link and yellow columns for the times and
distances read **by hand** from Google Maps (motorbike mode, "Depart at" a Tuesday 10:30 and 17:30).
Every 4th pair (10 pairs, `test`) is held out: it is not used to fit the speeds, only to report the error.

| File | Content |
|---|---|
| `data/validation/google_check.xlsx` | sheet `Huong dan` (instructions), sheet `Kiem tra` (fill in) |
| `data/validation/od_pairs.csv` | pairs with model minutes, km and CO₂ per slot |
| `data/validation/model_routes.geojson` | model routes (QGIS; filter by `id`, `slot`) |

## Routing API (`../routing_routes.py`)

Part of the backend; start it as usual from `carbon_backend`:

```powershell
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

- http://127.0.0.1:8000/routing/map – test map: click origin and destination, pick vehicle / time slot / algorithm,
  compare the routes; the "Google Maps" button opens the same two points in Google Maps. A query can be linked
  directly: `/routing/map?o=10.779,106.687&d=10.770,106.720&algorithm=pareto&k=3`.
- http://127.0.0.1:8000/docs – Swagger UI (tag `routing`).
- `GET /routing/meta` (vehicles, slots, algorithms), `GET /routing/lez` (zones), `GET /routing/health`.
- The graph and all weights are built in memory at start-up (~2 s) from `data/graph/` and
  `config/weights_model.json`; restart the server after changing the config. With `--reload` that happens on
  every code change, and each uvicorn worker holds its own copy of the graph.

`POST /routing/routes`

```json
{ "origin": {"lat": 10.7725, "lon": 106.6980}, "destination": {"lat": 10.7700, "lon": 106.7200},
  "vehicle": "motorcycle_petrol", "depart_at": "17:30", "algorithm": "pareto", "k": 3, "max_extra_time": 0.2 }
```

| Field | Values |
|---|---|
| `vehicle` | `motorcycle_petrol`, `car_petrol`, `motorcycle_electric`, `bicycle`, `foot` |
| `depart_at` / `slot` | `HH:MM` → `peak` inside 07:00–09:00 or 16:30–19:00, else `offpeak`; or give `slot` directly |
| `algorithm` | `pareto` (default), `fastest`, `greenest`, `shortest`, `yen`, `csp` |
| `k` | routes returned by `pareto` / `yen` (1–10) |
| `max_extra_time` | `csp`: allowed extra time as a fraction of the fastest route (0.2 = +20 %) |

Response: snapped origin/destination (`snap_m` = distance to the graph node), `google_maps_url`, `info`
(compute time, Pareto front size, …) and `routes[]` with `time_min`, `co2_g`, `distance_km`,
`extra_time_min` and `co2_saving_pct` (both relative to the fastest route), `shared_with_fastest_pct`
(share of the route's length also on the fastest route), `via` (main street names) and a GeoJSON `geometry`.
Points more than 300 m from a usable road return HTTP 400.

| Algorithm | Method | Notes |
|---|---|---|
| `fastest`, `greenest`, `shortest` | Dijkstra on t, c or length | `greenest`/`shortest` also return the fastest route for comparison |
| `yen` | Yen's K loopless shortest paths on t; spur searches are A* with exact reverse-Dijkstra bounds | alternatives are usually near-copies of the fastest route |
| `csp` | LARAC Lagrangian relaxation: min CO₂ s.t. t ≤ (1 + ε) × fastest | `larac_status` = `optimal` when the greenest route already fits, `lagrangian` otherwise (may miss the exact optimum) |
| `pareto` | BOA* bi-objective A* on (t, c) with exact single-objective bounds | exact Pareto front; `k` routes are picked spread along it (always fastest and greenest) |

Graph O/D points snap to the nearest graph node (junction), not to the nearest point on a road.
All queries in the LEZ take well under 0.2 s.
