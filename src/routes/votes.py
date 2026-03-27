"""
Vote routes: cast a vote, get results.

Key design decisions:
- member_token in the request body keeps the API simple to test
- Cooldown is enforced: if vote_cooldown > 0, a member must wait N minutes before changing
- Reasons are optional and only meaningful for "leave" votes
- Results verdict is driven by the room's leave_threshold
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from src.database import get_connection
from src.schemas import CastVoteRequest, ReasonCount, ResultsResponse, VoteResponse, VALID_REASONS
from src.routes.rooms import _get_room_or_404

router = APIRouter(prefix="/rooms", tags=["votes"])


def _get_member_or_401(token: str, room_id: int, conn: sqlite3.Connection) -> sqlite3.Row:
    member = conn.execute(
        "SELECT * FROM members WHERE token = ? AND room_id = ?", (token, room_id)
    ).fetchone()
    if not member:
        raise HTTPException(status_code=401, detail="Invalid member_token for this room")
    return member


def _compute_verdict(stay: int, leave: int, threshold: int) -> tuple[str, bool]:
    """Return (verdict_text, decision_reached)."""
    total = stay + leave
    if total == 0:
        return "No votes yet", False
    leave_pct = (leave / total) * 100
    if leave_pct >= threshold:
        return "Most want to LEAVE", True
    stay_pct = (stay / total) * 100
    if stay_pct >= threshold:
        return "Most want to STAY", True
    if leave > stay:
        return "Most want to LEAVE", False
    if stay > leave:
        return "Most want to STAY", False
    return "It's a tie", False


@router.post("/{code}/vote", response_model=VoteResponse)
def cast_vote(
    code: str,
    body: CastVoteRequest,
    conn: sqlite3.Connection = Depends(get_connection),
) -> VoteResponse:
    """Cast or change your vote. Cooldown is enforced if the room has one configured."""
    room = _get_room_or_404(code, conn)
    member = _get_member_or_401(body.member_token, room["id"], conn)

    # Validate reason
    reason: Optional[str] = None
    if body.reason:
        if body.choice != "leave":
            raise HTTPException(status_code=422, detail="Reasons only apply to 'leave' votes")
        if body.reason not in VALID_REASONS:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid reason. Valid options: {VALID_REASONS}"
            )
        reason = body.reason

    # Check cooldown
    cooldown_minutes = room["vote_cooldown"]
    existing_vote = conn.execute(
        "SELECT * FROM votes WHERE member_id = ?", (member["id"],)
    ).fetchone()

    cooldown_until: Optional[str] = None
    if existing_vote and cooldown_minutes > 0:
        voted_at = datetime.fromisoformat(existing_vote["voted_at"])
        can_vote_at = voted_at + timedelta(minutes=cooldown_minutes)
        if datetime.utcnow() < can_vote_at:
            raise HTTPException(
                status_code=429,
                detail=f"Cooldown active. You can change your vote after {can_vote_at.isoformat()}"
            )

    now = datetime.utcnow()
    if cooldown_minutes > 0:
        cooldown_until = (now + timedelta(minutes=cooldown_minutes)).isoformat()

    with conn:
        conn.execute(
            """
            INSERT INTO votes (member_id, choice, reason, voted_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(member_id) DO UPDATE SET
                choice = excluded.choice,
                reason = excluded.reason,
                voted_at = excluded.voted_at
            """,
            (member["id"], body.choice, reason, now.isoformat()),
        )

    return VoteResponse(
        member_token=body.member_token,
        choice=body.choice,
        reason=reason,
        message=f"Vote recorded: {body.choice.upper()}",
        cooldown_until=cooldown_until,
    )


@router.get("/{code}/results", response_model=ResultsResponse)
def get_results(
    code: str,
    conn: sqlite3.Connection = Depends(get_connection),
) -> ResultsResponse:
    """Get the live vote tally, verdict, and reason breakdown for a room."""
    room = _get_room_or_404(code, conn)

    # Vote counts
    rows = conn.execute(
        """
        SELECT v.choice, COUNT(*) as count
        FROM votes v JOIN members m ON m.id = v.member_id
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

    # Reason breakdown (leave votes only)
    reason_rows = conn.execute(
        """
        SELECT v.reason, COUNT(*) as count
        FROM votes v JOIN members m ON m.id = v.member_id
        WHERE m.room_id = ? AND v.choice = 'leave' AND v.reason IS NOT NULL
        GROUP BY v.reason ORDER BY count DESC
        """,
        (room["id"],),
    ).fetchall()
    reasons = [ReasonCount(reason=r["reason"], count=r["count"]) for r in reason_rows]

    verdict, decision_reached = _compute_verdict(stay, leave, room["leave_threshold"])

    return ResultsResponse(
        code=room["code"],
        event_name=room["event_name"],
        total_votes=total,
        stay_count=stay,
        leave_count=leave,
        leave_percent=leave_percent,
        leave_threshold=room["leave_threshold"],
        verdict=verdict,
        decision_reached=decision_reached,
        reasons=reasons,
    )
