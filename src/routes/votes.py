"""
Vote routes: cast a vote, get results.

Key design decisions:
- member_token in the request body (not a header) keeps the API simple to test
- A member can change their vote anytime (UPSERT)
- Results are always visible — no "reveal after all vote" mechanic for simplicity
"""

import sqlite3
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from src.database import get_connection
from src.schemas import CastVoteRequest, ResultsResponse, VoteResponse
from src.routes.rooms import _get_room_or_404

router = APIRouter(prefix="/rooms", tags=["votes"])


def _get_member_or_401(token: str, room_id: int, conn: sqlite3.Connection) -> sqlite3.Row:
    member = conn.execute(
        "SELECT * FROM members WHERE token = ? AND room_id = ?", (token, room_id)
    ).fetchone()
    if not member:
        raise HTTPException(status_code=401, detail="Invalid member_token for this room")
    return member


def _compute_verdict(stay: int, leave: int) -> str:
    total = stay + leave
    if total == 0:
        return "No votes yet"
    if leave > stay:
        return "Most want to LEAVE"
    if stay > leave:
        return "Most want to STAY"
    return "It's a tie"


@router.post("/{code}/vote", response_model=VoteResponse)
def cast_vote(
    code: str,
    body: CastVoteRequest,
    conn: sqlite3.Connection = Depends(get_connection),
) -> VoteResponse:
    """Cast or change your vote. Use the member_token you received when joining."""
    room = _get_room_or_404(code, conn)
    member = _get_member_or_401(body.member_token, room["id"], conn)

    with conn:
        # UPSERT: insert vote or update if member already voted
        conn.execute(
            """
            INSERT INTO votes (member_id, choice, voted_at)
            VALUES (?, ?, ?)
            ON CONFLICT(member_id) DO UPDATE SET choice = excluded.choice, voted_at = excluded.voted_at
            """,
            (member["id"], body.choice, datetime.utcnow().isoformat()),
        )

    action = "Vote recorded" if body.choice == "leave" else "Vote recorded"
    return VoteResponse(
        member_token=body.member_token,
        choice=body.choice,
        message=f"{action}: {body.choice.upper()}",
    )


@router.get("/{code}/results", response_model=ResultsResponse)
def get_results(
    code: str,
    conn: sqlite3.Connection = Depends(get_connection),
) -> ResultsResponse:
    """Get the live vote tally for a room."""
    room = _get_room_or_404(code, conn)

    rows = conn.execute(
        """
        SELECT v.choice, COUNT(*) as count
        FROM votes v
        JOIN members m ON m.id = v.member_id
        WHERE m.room_id = ?
        GROUP BY v.choice
        """,
        (room["id"],),
    ).fetchall()

    counts = {row["choice"]: row["count"] for row in rows}
    stay = counts.get("stay", 0)
    leave = counts.get("leave", 0)
    total = stay + leave
    leave_percent = round((leave / total) * 100, 1) if total > 0 else 0.0

    return ResultsResponse(
        code=room["code"],
        event_name=room["event_name"],
        total_votes=total,
        stay_count=stay,
        leave_count=leave,
        leave_percent=leave_percent,
        verdict=_compute_verdict(stay, leave),
    )
