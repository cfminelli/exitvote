"""
Pydantic schemas for request bodies and API responses.

These define the shape of data coming in and going out of every endpoint.
Pydantic validates inputs automatically — bad data gets a clear 422 error.
"""

from typing import Optional
from pydantic import BaseModel, Field


# --- Requests ---

class CreateRoomRequest(BaseModel):
    event_name: str = Field(..., min_length=1, max_length=100, examples=["Taylor Swift - Eras Tour"])
    leave_threshold: int = Field(51, ge=1, le=100, description="% of leave votes needed to reach a decision")
    vote_cooldown: int = Field(0, ge=0, le=60, description="Minutes a member must wait before changing their vote")


class CastVoteRequest(BaseModel):
    member_token: str = Field(..., description="Your anonymous token received when joining")
    choice: str = Field(..., pattern="^(stay|leave)$", examples=["leave"])
    reason: Optional[str] = Field(None, description="Why you want to leave (optional)")


# --- Responses ---

VALID_REASONS = ["too_loud", "not_my_vibe", "tired", "too_late", "other"]

class RoomResponse(BaseModel):
    code: str
    event_name: str
    created_at: str
    expires_at: str
    member_count: int
    leave_threshold: int
    vote_cooldown: int


class JoinRoomResponse(BaseModel):
    code: str
    event_name: str
    member_token: str
    leave_threshold: int
    vote_cooldown: int


class VoteResponse(BaseModel):
    member_token: str
    choice: str
    reason: Optional[str]
    message: str
    cooldown_until: Optional[str]  # ISO timestamp — when they can change vote again


class ReasonCount(BaseModel):
    reason: str
    count: int


class ResultsResponse(BaseModel):
    code: str
    event_name: str
    total_votes: int
    stay_count: int
    leave_count: int
    leave_percent: float
    leave_threshold: int
    verdict: str          # "Most want to STAY" / "Most want to LEAVE" / "It's a tie" / "No votes yet"
    decision_reached: bool
    reasons: list[ReasonCount]
