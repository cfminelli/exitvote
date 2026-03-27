# ExitVote API

Anonymous event exit voting via room codes.
People at the same event join a room and vote Stay/Leave — no accounts needed.

## Setup
```bash
source venv/bin/activate
pip install -r requirements.txt
```

## Run & Test
- Dev server: `uvicorn src.main:app --reload`
- API docs:   http://127.0.0.1:8000/docs
- Tests:      `pytest tests/ -v`
- Coverage:   `pytest --cov=src tests/`
- Lint:       `ruff check src/ tests/`
- Format:     `black src/ tests/`
- Type check: `mypy src/`

## Project Structure
```
src/
├── main.py        # FastAPI app entry point
├── database.py    # SQLite connection + table creation
├── models.py      # DB row dataclasses
├── schemas.py     # Pydantic request/response models
└── routes/
    ├── rooms.py   # POST /rooms, POST /rooms/{code}/join, GET /rooms/{code}
    └── votes.py   # POST /rooms/{code}/vote, GET /rooms/{code}/results
tests/
├── conftest.py    # Shared fixtures (test client, DB)
├── test_rooms.py  # Room creation and joining tests
└── test_votes.py  # Voting and results tests
```

## Core Concepts
- **Room**: created with a short code (e.g. `ROCK-42`), expires after 8 hours
- **Member**: joins via room code, gets an anonymous `member_token` (UUID)
- **Vote**: Stay or Leave — one per member, changeable anytime
- **Results**: percentage of Leave votes, visible to all room members

## Code Style
- Type hints on all functions
- Pydantic models for all request/response bodies
- No ORM — plain SQL with sqlite3
- snake_case functions and variables, PascalCase classes
- Max 100 char lines

## API Summary
| Method | Path | Description |
|--------|------|-------------|
| POST | /rooms | Create a room |
| POST | /rooms/{code}/join | Join a room, get member_token |
| GET  | /rooms/{code} | Get room info |
| POST | /rooms/{code}/vote | Cast or change vote |
| GET  | /rooms/{code}/results | Get live vote tally |
