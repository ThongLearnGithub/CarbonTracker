def test_meta_lists_vehicles_and_algorithms(client):
    response = client.get("/routing/meta")

    assert response.status_code == 200
    assert "motorcycle_petrol" in response.json()["vehicles"]
    assert "pareto" in response.json()["algorithms"]


def test_route_between_two_points_in_the_lez(client):
    body = {"origin": {"lat": 10.772, "lon": 106.698}, "destination": {"lat": 10.7797, "lon": 106.6990}, "algorithm": "fastest"}
    response = client.post("/routing/routes", json=body)

    assert response.status_code == 200
    assert response.json()["routes"][0]["distance_km"] > 0


def test_point_outside_the_graph_is_a_400(client):
    body = {"origin": {"lat": 21.03, "lon": 105.85}, "destination": {"lat": 10.7797, "lon": 106.6990}}
    response = client.post("/routing/routes", json=body)

    assert response.status_code == 400
    assert "nearest road" in response.json()["detail"]


def test_health_endpoints(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/routing/health").json()["status"] == "ok"
