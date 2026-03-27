"""Tests for room creation, joining, and info endpoints."""


def test_create_room(client):
    res = client.post("/rooms", json={"event_name": "Taylor Swift - Eras Tour"})
    assert res.status_code == 201
    data = res.json()
    assert len(data["code"]) == 6
    assert data["code"].isupper()
    assert data["event_name"] == "Taylor Swift - Eras Tour"
    assert data["member_count"] == 0


def test_create_room_missing_name(client):
    res = client.post("/rooms", json={})
    assert res.status_code == 422


def test_create_room_empty_name(client):
    res = client.post("/rooms", json={"event_name": ""})
    assert res.status_code == 422


def test_join_room(client):
    # Create then join
    code = client.post("/rooms", json={"event_name": "Rock Concert"}).json()["code"]
    res = client.post(f"/rooms/{code}/join")
    assert res.status_code == 201
    data = res.json()
    assert data["code"] == code
    assert "member_token" in data
    assert len(data["member_token"]) == 36  # UUID format


def test_join_room_increments_member_count(client):
    code = client.post("/rooms", json={"event_name": "Jazz Night"}).json()["code"]
    client.post(f"/rooms/{code}/join")
    client.post(f"/rooms/{code}/join")
    res = client.get(f"/rooms/{code}")
    assert res.json()["member_count"] == 2


def test_join_nonexistent_room(client):
    res = client.post("/rooms/ZZZZZZ/join")
    assert res.status_code == 404


def test_get_room(client):
    code = client.post("/rooms", json={"event_name": "Comedy Show"}).json()["code"]
    res = client.get(f"/rooms/{code}")
    assert res.status_code == 200
    assert res.json()["event_name"] == "Comedy Show"


def test_get_nonexistent_room(client):
    res = client.get("/rooms/ZZZZZZ")
    assert res.status_code == 404


def test_room_code_is_case_insensitive(client):
    code = client.post("/rooms", json={"event_name": "Opera"}).json()["code"]
    res = client.get(f"/rooms/{code.lower()}")
    assert res.status_code == 200
