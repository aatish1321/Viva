@AGENTS.md
@TASKS.md

## Claude Code rules for this team

- My role (A, B or C) and my folder are in `CLAUDE.local.md`. Only edit files in my folder.
  If a change is needed anywhere else, tell me what and why instead of doing it.
- Do one task from TASKS.md at a time. When it's done, tell me how to test it, then stop and wait.
- Run the task's test yourself when you can (Python scripts, unit tests). For Streamlit screens, tell me what to click and what I should see.
- Never change `shared/contracts.py` unless I confirm the whole team agreed.
- Use uv for everything: `uv run ...` to run code, `uv add ...` for packages (ask me first). Never use pip or create `requirements.txt`.
- Git: commit only when I say the task works. Before pushing, run `git pull --rebase`.
  Commit only my folder's files. Never force-push. Never commit `.env` or `CLAUDE.local.md`.
- Commit messages start with the task ID, for example `A3: grading works`.
- If you fail at the same thing twice, stop and explain what's going wrong instead of trying a third time.
