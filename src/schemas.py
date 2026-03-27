"""
Pydantic schemas for request bodies and API responses.

These define the shape of data coming in and going out of every endpoint.
Pydantic validates inputs automatically — bad data gets a clear 422 error.
"""

from pydantic import BaseModel, Field


# --- Requests ---

class CreateRoomRequest(BaseModel):
    event_name: str = Field(..., min_length=1, max_length=100, examples=["Taylor Swift - Eras Tour"])


class JoinRoomRequest(BaseModel):
    pass  # No body needed — joining just requires the room code in the URL


class CastVoteRequest(BaseModel):
    member_token: str = Field(..., description="Your anonymous token received when joining")
    choice: str = Field(..., pattern="^(stay|leave)$", examples=["leave"])


# --- Responses ---

class RoomResponse(BaseModel):
    code: str
    event_name: str
    created_at: str
    expires_at: str
    member_count: int


class JoinRoomResponse(BaseModel):
    code: str
    event_name: str
    member_token: str  # the caller's anonymous identity — keep this secret


class VoteResponse(BaseModel):
    member_token: str
    choice: str
    message: str


class ResultsResponse(BaseModel):
    code: str
    event_name: str
    total_votes: int
    stay_count: int
    leave_count: int
    leave_percent: float  # 0.0 – 100.0
    verdict: str          # "Most want to STAY" / "Most want to LEAVE" / "It's a tie" / "No votes yet"
