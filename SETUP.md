# Setup (fresh laptop)

1. Install uv:
   ```
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   Open a new terminal, then check it with `uv --version`.
2. Log in to GitHub (choose HTTPS when it asks):
   ```
   gh auth login
   ```
3. Clone the repo:
   ```
   gh repo clone aatish1321/Viva
   cd Viva
   ```
4. Install the dependencies:
   ```
   uv sync
   ```
5. Create your `.env` and fill in the three values (ask the team for them, and never commit this file):
   ```
   cp .env.example .env
   ```
6. Create `CLAUDE.local.md` with your role line, for example:
   ```
   echo "I am Person B (Voice). My folder is voice/." > CLAUDE.local.md
   ```
7. Check that everything works. All four checks should show ✅:
   ```
   uv run python scripts/check_setup.py
   ```

## Daily commands

| When | Command |
|---|---|
| After every `git pull` | `uv sync` |
| Start the app | `uv run streamlit run app.py` |
| Add a package (tell the team first) | `uv add <package>` |
