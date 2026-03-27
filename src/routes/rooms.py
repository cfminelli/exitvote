"""
Room routes: create a room, join a room, get room info.

How it works:
- Anyone can create a room for an event and get a short code
- Anyone with the code can join and receive an anonymous member_token
- The member_token is the only identity — no accounts, no names
"""

import random
import sqlite3
import string
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException

from src.database import get_connection
from src.schemas import CreateRoomRequest, JoinRoomResponse, RoomResponse

router = APIRouter(prefix="/rooms", tags=["rooms"])

ROOM_TTL_HOURS = 8


def _make_room_code(conn: sqlite3.Connection) -> str:
    """Generate a unique 6-letter uppercase code, e.g. ROCKAZ."""
    for _ in range(10):
        code = "".join(random.choices(string.ascii_uppercase, k=6))
        exists = conn.execute("SELECT 1 FROM rooms WHERE code = ?", (code,)).fetchone()
        if not exists:
            return code
    raise RuntimeError("Could not generate a unique room code")


def _get_room_or_404(code: str, conn: sqlite3.Connection) -> sqlite3.Row:
    room = conn.execute("SELECT * FROM rooms WHERE code = ?", (code.upper(),)).fetchone()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room["expires_at"] < datetime.utcnow().isoformat():
        raise HTTPException(status_code=410, detail="Room has expired")
    return room


@router.post("", response_model=RoomResponse, status_code=201)
def create_room(
    body: CreateRoomRequest,
    conn: sqlite3.Connection = Depends(get_connection),
) -> RoomResponse:
    """Create a new room for an event. Returns a room code to share with your group."""
    now = datetime.utcnow()
    expires_at = now + timedelta(hours=ROOM_TTL_HOURS)

    code = _make_room_code(conn)
    with conn:
        conn.execute(
            "INSERT INTO rooms (code, event_name, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (code, body.event_name, now.isoformat(), expires_at.isoformat()),
        )

    return RoomResponse(
        code=code,
        event_name=body.event_name,
        created_at=now.isoformat(),
        expires_at=expires_at.isoformat(),
        member_count=0,
    )


@router.post("/{code}/join", response_model=JoinRoomResponse, status_code=201)
def join_room(
    code: str,
    conn: sqlite3.Connection = Depends(get_connection),
) -> JoinRoomResponse:
    """Join a room using its code. Returns an anonymous member_token — save it to vote."""
    room = _get_room_or_404(code, conn)
    token = str(uuid.uuid4())

    with conn:
        conn.execute(
            "INSERT INTO members (room_id, token, joined_at) VALUES (?, ?, ?)",
            (room["id"], token, datetime.utcnow().isoformat()),
        )

    return JoinRoomResponse(
        code=room["code"],
        event_name=room["event_name"],
        member_token=token,
    )


@router.get("/{code}", response_model=RoomResponse)
def get_room(
    code: str,
    conn: sqlite3.Connection = Depends(get_connection),
) -> RoomResponse:
    """Get room info and current member count."""
    room = _get_room_or_404(code, conn)
    member_count = conn.execute(
        "SELECT COUNT(*) FROM members WHERE room_id = ?", (room["id"],)
    ).fetchone()[0]

    return RoomResponse(
        code=room["code"],
        event_name=room["event_name"],
        created_at=room["created_at"],
        expires_at=room["expires_at"],
        member_count=member_count,
    )
