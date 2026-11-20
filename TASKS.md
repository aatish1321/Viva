# TASKS.md: Implementation tasks for AI coding assistants

## Instructions for the AI
- Read `AGENTS.md` first. It defines the project, the stack, the folder ownership, the data contracts and the agent rules.
- The user will tell you their role (A, B or C). **Only do the tasks for that role**, in order.
- Do **one task at a time**. After each task, stop and tell the user how to run or test it, then wait.
- A task is finished only when its **Done when** check passes.
- If a task depends on another person's function that isn't finished yet, use the fake from `shared/fakes.py`.
- Never change `shared/contracts.py` without the user confirming the whole team agreed.
- Keep everything as simple as possible. This is a hackathon demo.

---

## Environment setup (the night before, done once by one person)

The user creates the API keys and puts them in `.env` themselves. Do everything else.
**Never print, log or commit the values in `.env`.**

**S0.1: Python environment with uv**
- Check that uv is installed (`uv --version`). If it isn't, tell the user to install it (`curl -LsSf https://astral.sh/uv/install.sh | sh`) and wait.
- Run `uv init --name viva` in the repo root, then delete the hello-world `main.py` it creates (keep `pyproject.toml` and `.python-version`).
- Run `uv add streamlit google-genai elevenlabs python-dotenv`. This creates `.venv` and `uv.lock`.
- Follow the uv rules in `AGENTS.md`: no pip, no `requirements.txt`.
- Done when: `uv run python -c "import streamlit, google.genai, elevenlabs, dotenv"` runs without errors.

**S0.2: Git hygiene files**
- `.gitignore` must contain `.env`, `CLAUDE.local.md`, `__pycache__/`, `.venv/` and `scripts/test.mp3` (add any that are missing, keep the rest).
- Create `.env.example` with the empty keys `GEMINI_API_KEY=`, `ELEVENLABS_API_KEY=` and `ELEVENLABS_VOICE_ID=`.
- Check that `.env` exists and that all three keys have values, **without printing them**. If any are missing, tell the user which ones.
- Done when: `git status` doesn't show `.env`, and `.env.example` exists.

**S0.3: Verify current model IDs**
- Look up the current model IDs in the official docs (APIs change often, so don't trust memory):
  - Gemini: the newest **stable Flash** model on https://ai.google.dev/gemini-api/docs/models
  - ElevenLabs: a **low-latency** Text to Speech model, and the current **Scribe** Speech to Text model, from https://elevenlabs.io/docs
- Add a section `## Verified model IDs` at the end of `AGENTS.md` listing the three IDs, the date checked and the source URLs.
- Done when: the user has seen the three IDs and confirmed them.

**S0.4: Setup check script** (`scripts/check_setup.py`)
- Loads `.env` and runs four checks, printing ✅ or ❌ with a one-line fix for each failure:
  1. All three keys are present (show only "present" or "missing", never the values)
  2. Gemini replies to "Say hi in 3 words", using the verified Gemini model
  3. ElevenLabs Text to Speech saves "Welcome to your oral exam." to `scripts/test.mp3`, using `ELEVENLABS_VOICE_ID`
  4. ElevenLabs Speech to Text transcribes `scripts/test.mp3` back to text
- Print how long each API call took.
- Done when: all four checks pass and the user hears the voice in `scripts/test.mp3`.

**S0.5: Teammate guide** (`SETUP.md`)
- Short, numbered steps for a teammate on a fresh laptop: install uv, clone the repo, run `gh auth login`, run `uv sync`, copy `.env.example` to `.env` and fill it in, create `CLAUDE.local.md` with their role line (for example `I am Person B (Voice). My folder is voice/.`), then run `uv run python scripts/check_setup.py`.
- Add a short "Daily commands" box: `uv sync` after every pull, `uv run streamlit run app.py` to start the app, and `uv add <package>` only after telling the team.
- Done when: the file exists and every command in it has been run successfully at least once on this machine.

**S0.6: Commit and push**
- Commit `pyproject.toml`, `uv.lock`, `.python-version`, `.gitignore`, `.env.example`, `scripts/check_setup.py`, `SETUP.md` and the `AGENTS.md` update, with the message `S0: environment setup`.
- First confirm that `.env`, `.venv/`, `CLAUDE.local.md` and `scripts/test.mp3` are **not** staged.
- Run `git pull --rebase`, then `git push`.
- Done when: the push succeeds and GitHub shows no `.env`.

---

## Shared setup (at the start of the hackathon, done once)

**S1: Project skeleton**
- Create the folder structure from `AGENTS.md`, with empty modules (`pyproject.toml`, `.gitignore` and `.env.example` already exist from S0).
- Done when: `uv run streamlit run app.py` opens an empty page.

**S2: `shared/contracts.py`**
- Copy the TypedDicts from `AGENTS.md` section 4 exactly.
- Done when: `uv run python -c "import shared.contracts"` runs without errors.

**S3: `shared/fakes.py`**
- A fake version of every function in `AGENTS.md` section 4, returning realistic hard-coded data in the exact contract shapes:
  `extract_topics`, `grade_answer`, `update_mastery`, `next_turn`, `coach`, `speak` (returns empty bytes), `transcribe` (returns a fixed sentence).
- Make `fake_next_turn` return `end` after 4 calls, so a fake exam finishes.
- Done when: each fake can be imported and returns data matching its contract.

---

## Role A: Brain (`agent/`)

**A1: Gemini helper** (`agent/gemini.py`)
- `ask_json(prompt: str, schema, parts: list | None = None) -> dict`
- Uses the `google-genai` SDK with JSON output and two constants at the top of the file: `GEMINI_MODEL = "gemini-3.8-flash"` and `GEMINI_FALLBACK_MODEL = "gemini-3.6-flash"`.
- Retries once on invalid JSON, then raises a clear error.
- On 503 / overloaded errors: retry 2 times with a short wait (about 1-2 seconds), then try `GEMINI_FALLBACK_MODEL`. (The setup check hit 503 "high demand" errors and an 18.5s reply on `gemini-3.8-flash`.)
- Done when: a test call with a tiny schema returns a parsed dict.

**A2: Topic extraction** (`agent/topics.py`)
- `extract_topics(pdf_bytes) -> list[Topic]` sends the PDF to Gemini and returns 4–6 topics with ids `t1`…`t6`, key points and that topic's notes text.
- Prompt goes in `agent/prompts.py`.
- Done when: running it on `demo/demo_notes.pdf` prints 4–6 sensible topics.

**A3: Grading** (`agent/examiner.py`)
- `grade_answer(topic, question, answer) -> Grade`
- `lookup_notes(topic)` returns `topic["notes"]`, and those notes go into the grade prompt (`AGENTS.md` section 5) as the only truth.
- Done when: a good answer scores above 70, a wrong one below 40, and `evidence` quotes the notes.

**A4: Mastery update** (`agent/examiner.py`)
- `update_mastery(mastery, grade) -> mastery` in plain Python (no LLM), following the score, confidence and colour rules in `AGENTS.md` section 5.
- Also `init_mastery(topics)`, which returns every topic as grey with confidence none.
- Done when: a short unit test covering 0, 1, 2 and 3 answers produces the right confidence and colour.

**A5: Decision** (`agent/examiner.py`)
- `next_turn(state) -> ExamTurn` uses the decide prompt from `AGENTS.md` section 5 and sends the topics, mastery map and transcript.
- Enforce the safety limits **in code** before calling Gemini: 8 questions in total, 2 follow-ups per topic, 4 minutes. If a limit is hit, return `end` with reason "Time is up."
- Fallback if Gemini fails: ask a simple question on the next untested topic.
- Done when: the first call on an all-grey map returns a question with a reason.

**A6: Terminal exam runner** (`agent/run_cli.py`)
- A loop: `extract_topics` → `next_turn` → `input()` answer → `grade_answer` → `update_mastery` → repeat until `end`.
- Print the mastery map and the agent's reason after every turn.
- Done when: a full typed exam runs end to end and the agent ends it on its own. **Checkpoint 1 for the team.**

**A7: Coach** (`agent/coach.py`)
- `coach(state) -> Results`: weak topics are those scoring below 60. Write 3 flashcards per weak topic and a 3-step study plan.
- Done when: running it after a CLI exam prints flashcards only for the weak topics.

**A8: Prompt tuning**
- Run the CLI exam on the demo PDF 5 times. Adjust the prompts so that:
  - a vague answer always triggers `follow_up`
  - questions stay under 25 words and sound spoken
  - the exam ends within 8 questions
- Done when: 5 runs in a row behave correctly.

**A9 (optional): Grader agent** (`agent/examiner.py`)
- After `grade_answer`, a second Gemini call reviews the grade against the notes and may change the score, filling in `grader_note`.
- Done when: `grader_note` appears for at least one overly generous grade.

---

## Role B: Voice (`voice/`)

**B1: Text to speech** (`voice/voice.py`)
- `speak(text) -> bytes` uses the ElevenLabs SDK, reads `ELEVENLABS_VOICE_ID` from `.env` and returns MP3 bytes.
- Use a low-latency TTS model, with the model ID in a constant.
- Note: the free ElevenLabs plan only allows **premade** voices via the API (Voice Library voices fail with `paid_plan_required`) and has a monthly character limit. So do **B5 (caching) right after B2**, not at the end.
- Done when: a test script saves `test.mp3` and it plays a question in the chosen voice.

**B2: Speech to text** (`voice/voice.py`)
- `transcribe(audio: bytes) -> str` uses ElevenLabs Speech to Text (Scribe) and returns plain text.
- Done when: a recorded WAV or MP3 sentence comes back as correct text.

**B3: Speed test** (`voice/test_voice.py`)
- Time both functions over 3 runs and print the average.
- If either takes over 3 seconds, try a faster model or a shorter output format.
- Done when: both average under 3 seconds, or the slow one is reported to the team.

**B4: Voice in the exam screen** (in `app.py`, together with C)
- The question audio from `speak()` plays automatically (`st.audio(..., autoplay=True)`).
- The answer from `st.audio_input` goes through `transcribe()`.
- The transcribed text appears in an **editable text box** with a "Submit answer" button, so misheard words can be fixed.
- Done when: a full exam can be done by voice in the app.

**B5: Caching**
- Cache `speak()` results by text (a dict in `st.session_state`), so a replayed question isn't generated twice.
- Done when: replaying a question makes no new API call.

**B6 (optional): Examiner personas**
- A `PERSONAS` dict with "Strict professor" and "Friendly tutor". Each has a voice ID and a one-line style instruction that A adds to the decide prompt.
- Done when: switching the persona changes both the voice and the tone of the questions.

---

## Role C: Screen (`app.py`, `ui/`)

**C1: App skeleton** (`app.py`)
- Three phases in `st.session_state.phase`: `upload` → `exam` → `results`. Initialise every session key from `AGENTS.md` section 4.
- Use the fakes for every function at first.
- Done when: clicking through all three phases works with fake data.

**C2: Upload screen**
- A PDF uploader and a "Start exam" button. On start: `extract_topics` → `init_mastery` → first `next_turn`, then switch to `exam`.
- Done when: uploading a PDF opens the exam screen with the first question.

**C3: Mastery map** (`ui/mastery_map.py`)
- `render_mastery_map(topics, mastery)`: one card per topic with the name, score and a background colour (grey / red / amber / green).
- Big fonts so it's readable on a projector.
- Done when: the cards change colour when the mastery data changes.

**C4: Exam screen**
- Layout: the question large at the top, the **"why I'm asking" reason** in italics under it, the mastery map at the side, and the transcript below.
- A text box plus a "Submit answer" button (voice is added in B4).
- On submit: `grade_answer` → `update_mastery` → `next_turn`, then append to the transcript and rerun.
- Show a question counter and the elapsed time.
- Done when: a full exam on fakes runs from the exam screen to results.

**C5: Results screen** (`ui/results.py`)
- The final mastery map, the weak topics highlighted, flashcards as flip-style cards (an expander for each card is fine) and the study plan.
- A "Start again" button that resets the session.
- Done when: the results show the coach output.

**C6: Connect the real functions**
- Swap each fake for the real import one at a time (`agent/` first, then `voice/`), testing after each swap.
- Done when: a full real exam runs in the app. **Checkpoint 2 for the team.**

**C7: Demo polish**
- A clean title and logo text ("Viva: your AI oral examiner"), hide the Streamlit menu, use a wide layout.
- Show a spinner with the agent's action while waiting ("Examiner is grading your answer…", "Examiner is choosing the next question…").
- Done when: the app looks clean on a projector at 1080p.

**C8: Pitch script draft** (`demo/pitch.md`)
- A 3-minute script: problem story → one-line description → live demo steps → why it is agentic (goal, decisions, tools, stopping on its own) → tech (Gemini, ElevenLabs) → close.
- Include the deliberately vague answer the presenter gives to trigger a follow-up.
- Done when: the script reads aloud in under 3 minutes.

---

## Priority if time runs short
Cut in this order: A9 → B6 → B5 → B4 (typed answers still work).
**Never cut:** C3 (mastery map), the reason line in C4, A5, A6.
