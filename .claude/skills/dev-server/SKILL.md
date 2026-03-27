---
name: dev-server
description: Start the development server
allowed-tools: Bash(uvicorn *)
---

Start the ExitVote dev server:

```bash
source venv/bin/activate
uvicorn src.main:app --reload
```

Then open http://127.0.0.1:8000/docs to explore the API interactively.
