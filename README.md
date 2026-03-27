# ExitVote

Anonymous event exit voting. People at the same show, concert, or event join a room and vote **Stay** or **Leave** — no accounts, no names.

## How it works

1. Someone creates a room → gets a 6-letter code (e.g. `ROCKAZ`)
2. Everyone in the group opens the app and joins with the code
3. Each person votes anonymously: **Stay** or **Leave**
4. Anyone can see live results at any time

## Run locally

```bash
# 1. Clone and enter the project
git clone https://github.com/YOUR_USERNAME/exitvote.git
cd exitvote

# 2. Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Start the server
uvicorn src.main:app --reload

# 4. Open the interactive API docs
open http://127.0.0.1:8000/docs
```

## API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/rooms` | Create a room for an event |
| `POST` | `/rooms/{code}/join` | Join a room, receive anonymous token |
| `GET`  | `/rooms/{code}` | Get room info and member count |
| `POST` | `/rooms/{code}/vote` | Cast or change your vote (stay/leave) |
| `GET`  | `/rooms/{code}/results` | Live vote tally and verdict |

### Quick example

```bash
# Create a room
curl -X POST http://localhost:8000/rooms \
  -H "Content-Type: application/json" \
  -d '{"event_name": "Taylor Swift - Eras Tour"}'
# → {"code": "ROCKAZ", ...}

# Join the room
curl -X POST http://localhost:8000/rooms/ROCKAZ/join
# → {"member_token": "uuid-here", ...}

# Vote
curl -X POST http://localhost:8000/rooms/ROCKAZ/vote \
  -H "Content-Type: application/json" \
  -d '{"member_token": "uuid-here", "choice": "leave"}'

# See results
curl http://localhost:8000/rooms/ROCKAZ/results
# → {"verdict": "Most want to LEAVE", "leave_percent": 66.7, ...}
```

## Run tests

```bash
pytest tests/ -v
```

## Stack

- **Python 3.9+**
- **FastAPI** — API framework
- **SQLite** — database (no setup required)
- **Pytest + httpx** — testing

## Deploy to Railway

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com)

1. Push this repo to GitHub
2. Go to [railway.com](https://railway.com) → New Project → Deploy from GitHub
3. Select this repo → Railway auto-detects the config and deploys
