---
name: test-runner
description: Run the test suite and fix any failures
allowed-tools: Bash(pytest *), Read, Edit
---

Run the ExitVote test suite:

1. Activate venv if needed: `source venv/bin/activate`
2. Run: `pytest tests/ -v`
3. If tests fail:
   - Read the failing test to understand what's expected
   - Read the implementation to find the bug
   - Fix the implementation (never the test unless the test is clearly wrong)
   - Re-run until all pass
4. Show final results
