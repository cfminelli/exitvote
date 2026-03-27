"""Tests for voting and results endpoints."""

import pytest


@pytest.fixture
def room_and_token(client):
    """Helper: create a room and return (code, member_token)."""
    code = client.post("/rooms", json={"event_name": "Test Event"}).json()["code"]
    token = client.post(f"/rooms/{code}/join").json()["member_token"]
    return code, token


@pytest.fixture
def unanimous_room(client):
    """Room that requires 100% leave votes to reach a decision."""
    code = client.post("/rooms", json={"event_name": "Strict Room", "leave_threshold": 100}).json()["code"]
    tokens = [client.post(f"/rooms/{code}/join").json()["member_token"] for _ in range(3)]
    return code, tokens


# ── Basic voting ────────────────────────────────────────────────

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


# ── Reasons ─────────────────────────────────────────────────────

def test_vote_leave_with_reason(client, room_and_token):
    code, token = room_and_token
    res = client.post(f"/rooms/{code}/vote", json={
        "member_token": token, "choice": "leave", "reason": "too_loud"
    })
    assert res.status_code == 200
    assert res.json()["reason"] == "too_loud"


def test_vote_stay_with_reason_rejected(client, room_and_token):
    code, token = room_and_token
    res = client.post(f"/rooms/{code}/vote", json={
        "member_token": token, "choice": "stay", "reason": "too_loud"
    })
    assert res.status_code == 422


def test_vote_invalid_reason(client, room_and_token):
    code, token = room_and_token
    res = client.post(f"/rooms/{code}/vote", json={
        "member_token": token, "choice": "leave", "reason": "madeup_reason"
    })
    assert res.status_code == 422


# ── Results ─────────────────────────────────────────────────────

def test_results_no_votes(client):
    code = client.post("/rooms", json={"event_name": "Empty Room"}).json()["code"]
    client.post(f"/rooms/{code}/join")
    res = client.get(f"/rooms/{code}/results")
    assert res.status_code == 200
    data = res.json()
    assert data["total_votes"] == 0
    assert data["verdict"] == "No votes yet"
    assert data["leave_percent"] == 0.0
    assert data["decision_reached"] is False


def test_results_majority_leave(client):
    code = client.post("/rooms", json={"event_name": "Boring Show"}).json()["code"]
    tokens = [client.post(f"/rooms/{code}/join").json()["member_token"] for _ in range(3)]
    client.post(f"/rooms/{code}/vote", json={"member_token": tokens[0], "choice": "leave"})
    client.post(f"/rooms/{code}/vote", json={"member_token": tokens[1], "choice": "leave"})
    client.post(f"/rooms/{code}/vote", json={"member_token": tokens[2], "choice": "stay"})

    data = client.get(f"/rooms/{code}/results").json()
    assert data["leave_count"] == 2
    assert data["stay_count"] == 1
    assert data["leave_percent"] == pytest.approx(66.7)
    assert data["verdict"] == "Most want to LEAVE"
    assert data["decision_reached"] is True  # 66.7% >= 51% threshold


def test_results_majority_stay(client):
    code = client.post("/rooms", json={"event_name": "Great Concert"}).json()["code"]
    tokens = [client.post(f"/rooms/{code}/join").json()["member_token"] for _ in range(3)]
    client.post(f"/rooms/{code}/vote", json={"member_token": tokens[0], "choice": "stay"})
    client.post(f"/rooms/{code}/vote", json={"member_token": tokens[1], "choice": "stay"})
    client.post(f"/rooms/{code}/vote", json={"member_token": tokens[2], "choice": "leave"})

    data = client.get(f"/rooms/{code}/results").json()
    assert data["verdict"] == "Most want to STAY"
    assert data["decision_reached"] is True


def test_results_tie(client):
    code = client.post("/rooms", json={"event_name": "Meh Show"}).json()["code"]
    tokens = [client.post(f"/rooms/{code}/join").json()["member_token"] for _ in range(2)]
    client.post(f"/rooms/{code}/vote", json={"member_token": tokens[0], "choice": "stay"})
    client.post(f"/rooms/{code}/vote", json={"member_token": tokens[1], "choice": "leave"})

    data = client.get(f"/rooms/{code}/results").json()
    assert data["verdict"] == "It's a tie"
    assert data["decision_reached"] is False


def test_unanimous_threshold_not_reached(client, unanimous_room):
    code, tokens = unanimous_room
    # Only 2 of 3 vote leave — doesn't reach 100%
    client.post(f"/rooms/{code}/vote", json={"member_token": tokens[0], "choice": "leave"})
    client.post(f"/rooms/{code}/vote", json={"member_token": tokens[1], "choice": "leave"})
    client.post(f"/rooms/{code}/vote", json={"member_token": tokens[2], "choice": "stay"})

    data = client.get(f"/rooms/{code}/results").json()
    assert data["verdict"] == "Most want to LEAVE"
    assert data["decision_reached"] is False  # 66.7% < 100% threshold


def test_unanimous_threshold_reached(client, unanimous_room):
    code, tokens = unanimous_room
    for token in tokens:
        client.post(f"/rooms/{code}/vote", json={"member_token": token, "choice": "leave"})

    data = client.get(f"/rooms/{code}/results").json()
    assert data["decision_reached"] is True  # 100% == 100% threshold


def test_results_include_reasons(client):
    code = client.post("/rooms", json={"event_name": "Reason Test"}).json()["code"]
    tokens = [client.post(f"/rooms/{code}/join").json()["member_token"] for _ in range(3)]
    client.post(f"/rooms/{code}/vote", json={"member_token": tokens[0], "choice": "leave", "reason": "too_loud"})
    client.post(f"/rooms/{code}/vote", json={"member_token": tokens[1], "choice": "leave", "reason": "too_loud"})
    client.post(f"/rooms/{code}/vote", json={"member_token": tokens[2], "choice": "leave", "reason": "tired"})

    data = client.get(f"/rooms/{code}/results").json()
    reasons = {r["reason"]: r["count"] for r in data["reasons"]}
    assert reasons["too_loud"] == 2
    assert reasons["tired"] == 1


def test_changing_vote_updates_results(client):
    code = client.post("/rooms", json={"event_name": "Mind Changer"}).json()["code"]
    token = client.post(f"/rooms/{code}/join").json()["member_token"]

    client.post(f"/rooms/{code}/vote", json={"member_token": token, "choice": "stay"})
    assert client.get(f"/rooms/{code}/results").json()["stay_count"] == 1

    client.post(f"/rooms/{code}/vote", json={"member_token": token, "choice": "leave"})
    data = client.get(f"/rooms/{code}/results").json()
    assert data["stay_count"] == 0
    assert data["leave_count"] == 1


# ── Cooldown ─────────────────────────────────────────────────────

def test_cooldown_blocks_immediate_change(client):
    code = client.post("/rooms", json={"event_name": "Cooldown Test", "vote_cooldown": 30}).json()["code"]
    token = client.post(f"/rooms/{code}/join").json()["member_token"]

    # First vote: allowed
    client.post(f"/rooms/{code}/vote", json={"member_token": token, "choice": "stay"})

    # Immediate change: blocked
    res = client.post(f"/rooms/{code}/vote", json={"member_token": token, "choice": "leave"})
    assert res.status_code == 429


def test_no_cooldown_allows_immediate_change(client):
    code = client.post("/rooms", json={"event_name": "No Cooldown", "vote_cooldown": 0}).json()["code"]
    token = client.post(f"/rooms/{code}/join").json()["member_token"]

    client.post(f"/rooms/{code}/vote", json={"member_token": token, "choice": "stay"})
    res = client.post(f"/rooms/{code}/vote", json={"member_token": token, "choice": "leave"})
    assert res.status_code == 200


def test_first_vote_always_allowed_with_cooldown(client):
    code = client.post("/rooms", json={"event_name": "First Vote", "vote_cooldown": 60}).json()["code"]
    token = client.post(f"/rooms/{code}/join").json()["member_token"]
    res = client.post(f"/rooms/{code}/vote", json={"member_token": token, "choice": "leave"})
    assert res.status_code == 200
