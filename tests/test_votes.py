"""Tests for voting and results endpoints."""

import pytest


@pytest.fixture
def room_and_token(client):
    """Helper: create a room and return (code, member_token)."""
    code = client.post("/rooms", json={"event_name": "Test Event"}).json()["code"]
    token = client.post(f"/rooms/{code}/join").json()["member_token"]
    return code, token


def test_cast_vote_leave(client, room_and_token):
    code, token = room_and_token
    res = client.post(f"/rooms/{code}/vote", json={"member_token": token, "choice": "leave"})
    assert res.status_code == 200
    assert res.json()["choice"] == "leave"


def test_cast_vote_stay(client, room_and_token):
    code, token = room_and_token
    res = client.post(f"/rooms/{code}/vote", json={"member_token": token, "choice": "stay"})
    assert res.status_code == 200
    assert res.json()["choice"] == "stay"


def test_change_vote(client, room_and_token):
    code, token = room_and_token
    client.post(f"/rooms/{code}/vote", json={"member_token": token, "choice": "stay"})
    res = client.post(f"/rooms/{code}/vote", json={"member_token": token, "choice": "leave"})
    assert res.status_code == 200
    assert res.json()["choice"] == "leave"


def test_invalid_vote_choice(client, room_and_token):
    code, token = room_and_token
    res = client.post(f"/rooms/{code}/vote", json={"member_token": token, "choice": "maybe"})
    assert res.status_code == 422


def test_vote_with_wrong_token(client, room_and_token):
    code, _ = room_and_token
    res = client.post(f"/rooms/{code}/vote", json={"member_token": "fake-token", "choice": "leave"})
    assert res.status_code == 401


def test_results_no_votes(client):
    code = client.post("/rooms", json={"event_name": "Empty Room"}).json()["code"]
    client.post(f"/rooms/{code}/join")
    res = client.get(f"/rooms/{code}/results")
    assert res.status_code == 200
    data = res.json()
    assert data["total_votes"] == 0
    assert data["verdict"] == "No votes yet"
    assert data["leave_percent"] == 0.0


def test_results_majority_leave(client):
    code = client.post("/rooms", json={"event_name": "Boring Show"}).json()["code"]
    tokens = [client.post(f"/rooms/{code}/join").json()["member_token"] for _ in range(3)]
    client.post(f"/rooms/{code}/vote", json={"member_token": tokens[0], "choice": "leave"})
    client.post(f"/rooms/{code}/vote", json={"member_token": tokens[1], "choice": "leave"})
    client.post(f"/rooms/{code}/vote", json={"member_token": tokens[2], "choice": "stay"})

    res = client.get(f"/rooms/{code}/results")
    data = res.json()
    assert data["leave_count"] == 2
    assert data["stay_count"] == 1
    assert data["leave_percent"] == pytest.approx(66.7)
    assert data["verdict"] == "Most want to LEAVE"


def test_results_majority_stay(client):
    code = client.post("/rooms", json={"event_name": "Great Concert"}).json()["code"]
    tokens = [client.post(f"/rooms/{code}/join").json()["member_token"] for _ in range(3)]
    client.post(f"/rooms/{code}/vote", json={"member_token": tokens[0], "choice": "stay"})
    client.post(f"/rooms/{code}/vote", json={"member_token": tokens[1], "choice": "stay"})
    client.post(f"/rooms/{code}/vote", json={"member_token": tokens[2], "choice": "leave"})

    data = client.get(f"/rooms/{code}/results").json()
    assert data["verdict"] == "Most want to STAY"


def test_results_tie(client):
    code = client.post("/rooms", json={"event_name": "Meh Show"}).json()["code"]
    tokens = [client.post(f"/rooms/{code}/join").json()["member_token"] for _ in range(2)]
    client.post(f"/rooms/{code}/vote", json={"member_token": tokens[0], "choice": "stay"})
    client.post(f"/rooms/{code}/vote", json={"member_token": tokens[1], "choice": "leave"})

    data = client.get(f"/rooms/{code}/results").json()
    assert data["verdict"] == "It's a tie"


def test_changing_vote_updates_results(client):
    code = client.post("/rooms", json={"event_name": "Mind Changer"}).json()["code"]
    token = client.post(f"/rooms/{code}/join").json()["member_token"]

    client.post(f"/rooms/{code}/vote", json={"member_token": token, "choice": "stay"})
    data_before = client.get(f"/rooms/{code}/results").json()
    assert data_before["stay_count"] == 1

    client.post(f"/rooms/{code}/vote", json={"member_token": token, "choice": "leave"})
    data_after = client.get(f"/rooms/{code}/results").json()
    assert data_after["stay_count"] == 0
    assert data_after["leave_count"] == 1
