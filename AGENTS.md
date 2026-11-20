# AGENTS.md: Project context for AI coding tools

> Put this file in the repo root. Cursor, Codex, Copilot and most other AI coding tools read `AGENTS.md` automatically.
> If you use Claude Code, also save a copy as `CLAUDE.md`.
> If your tool doesn't read it automatically, paste it at the start of every new AI chat.

---

## 1. What we are building

**Viva** is an AI oral exam examiner, built at the GDG on Campus University of Debrecen Agentic AI Hackathon
(Saturday 21 November 2026, hacking 11:00–17:00, 3 people, every teammate codes with AI).

- The student uploads lecture notes as a PDF.
- A Gemini agent splits the notes into 4–6 topics.
- The agent runs a **spoken** oral exam. Its single goal is to **find out what the student does NOT know in about 3 minutes.**
- On every turn the agent grades the answer against the notes, updates a **mastery map**, and **decides on its own** what to do next:
  follow up, move to a new topic, or end the exam. It also shows a one-line reason on screen.
- After the exam, a coach agent writes flashcards and a short study plan for the weak topics.

**Why this is agentic (the judges must see this):** the model has a goal, keeps state (the mastery map), picks its own next action,
uses a tool (`lookup_notes`) to check answers, decides when to stop, and acts afterwards (flashcards).
The live mastery map and the "why I'm asking this" line make those decisions visible. **Never cut them.**

---

## 2. Stack (do not add anything else)

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| UI | Streamlit, a single app. `st.session_state` for state, `st.audio_input` for the mic, `st.audio(..., autoplay=True)` for playback |
| LLM | Gemini via the `google-genai` SDK, always with JSON (structured) output |
| Model | The newest stable **Flash** model on https://ai.google.dev/gemini-api/docs/models. Store the ID in one constant `GEMINI_MODEL` |
| Voice out | ElevenLabs Text to Speech (`elevenlabs` SDK) |
| Voice in | ElevenLabs Speech to Text, Scribe model (`elevenlabs` SDK) |
| Config | `python-dotenv`, with keys in `.env` |

**Do NOT use:** LangChain, LlamaIndex, any database, a separate frontend (React etc.), Docker, or vector stores.
The notes are small, so `lookup_notes` just returns that topic's text.

`requirements.txt`:
```
streamlit
google-genai
elevenlabs
python-dotenv
```

`.env` (never commit it):
```
GEMINI_API_KEY=...
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...
```

Run: `streamlit run app.py`

---

## 3. Folder structure and ownership

**Only edit files you own.** Change files in `shared/` only after telling the team.

```
viva/
├── app.py                 # C: Streamlit app, phases: upload -> exam -> results
├── ui/
│   ├── mastery_map.py     # C: coloured topic map component
│   └── results.py         # C: scores, weak topics, flashcards, study plan
├── agent/
│   ├── gemini.py          # A: ask_json(prompt, schema, parts=None) helper, retry once on bad JSON
│   ├── topics.py          # A: extract_topics
│   ├── examiner.py        # A: grade_answer, next_turn, update_mastery
│   ├── coach.py           # A: coach
│   └── prompts.py         # A: every prompt lives here
├── voice/
│   └── voice.py           # B: speak, transcribe
├── shared/
│   ├── contracts.py       # ALL: TypedDicts below
│   └── fakes.py           # ALL: fake versions of every function (hard-coded examples)
├── demo/
│   └── demo_notes.pdf     # B: lecture used on stage
├── .env
├── .gitignore             # .env, __pycache__, .venv
└── requirements.txt
```

---

## 4. Data contracts (`shared/contracts.py`)

**Never change these shapes without telling the whole team.**

```python
from typing import TypedDict, Literal, Optional

class Topic(TypedDict):
    id: str                 # "t1", "t2", ...
    name: str               # "Cardiac cycle"
    key_points: list[str]
    notes: str              # this topic's slice of the lecture notes

class MasteryEntry(TypedDict):
    topic_id: str
    score: int              # 0-100, average of answer scores for this topic
    confidence: Literal["none", "low", "medium", "high"]
    answers: int
    colour: Literal["grey", "red", "amber", "green"]

class ExamTurn(TypedDict):
    action: Literal["follow_up", "new_topic", "end"]
    topic_id: Optional[str]  # None when action == "end"
    question: str            # empty when action == "end"
    reason: str              # one plain sentence shown on screen

class Grade(TypedDict):
    topic_id: str
    score: int               # 0-100
    evidence: str            # short quote from the notes
    missing: list[str]       # what the answer left out
    grader_note: Optional[str]

class TranscriptEntry(TypedDict):
    role: Literal["examiner", "student"]
    text: str
    topic_id: Optional[str]

class Flashcard(TypedDict):
    topic_id: str
    front: str
    back: str

class Results(TypedDict):
    weak_topics: list[str]   # topic ids with score < 60
    flashcards: list[Flashcard]
    study_plan: list[str]
```

### Function interfaces

```python
# agent/  (Person A)
def extract_topics(pdf_bytes: bytes) -> list[Topic]: ...
def grade_answer(topic: Topic, question: str, answer: str) -> Grade: ...
def update_mastery(mastery: dict[str, MasteryEntry], grade: Grade) -> dict[str, MasteryEntry]: ...  # pure code, no LLM
def next_turn(state: dict) -> ExamTurn: ...   # the agent's decision
def coach(state: dict) -> Results: ...

# voice/  (Person B)
def speak(text: str) -> bytes: ...            # mp3 bytes
def transcribe(audio: bytes) -> str: ...
```

### `st.session_state` keys (owned by C, read by everyone)

| Key | Type |
|---|---|
| `phase` | `"upload"` / `"exam"` / `"results"` |
| `topics` | `list[Topic]` |
| `mastery` | `dict[str, MasteryEntry]`, keyed by topic id |
| `transcript` | `list[TranscriptEntry]` |
| `current_turn` | `ExamTurn` |
| `started_at` | `float` (time.time()) |
| `question_count` | `int` |
| `results` | `Results` |

`state` passed to `next_turn` and `coach` = `{"topics", "mastery", "transcript", "question_count", "started_at"}`.

---

## 5. Agent behaviour

### One exam turn
1. The student answers (mic → `transcribe`, or typed).
2. `grade_answer`: gets the topic's notes (`lookup_notes`) and asks Gemini for a `Grade` with evidence from the notes.
3. `update_mastery` (plain code) updates the score, confidence and colour.
4. `next_turn`: Gemini sees the whole mastery map and the transcript, then returns an `ExamTurn`.
5. If the action is not `end`: `speak(question)`, show the question and the reason, and wait for the next answer.
6. If the action is `end`: run `coach`, then switch to the results phase.

The first question comes from `next_turn` with an all-grey map.

### Mastery rules (in code)
- score = average of that topic's answer scores
- confidence: 0 answers = none, 1 = low, 2 = medium, 3+ = high; 2 answers within 15 points of each other = high
- colour: no answers = grey, score < 40 = red, 40–70 = amber, > 70 = green

### Decision rules (in the prompt)
- Ask about the topic with the **lowest confidence**; break ties with the lowest score.
- Last answer scored 30–70 or was vague → `follow_up` on the same topic with a more specific question.
- Last answer scored above 80 → ask a harder question or move on.
- Every topic at medium or high confidence → `end`.

### Safety limits (in CODE, never trust the model for these)
- At most **8 questions** in total and at most **2 follow-ups** per topic. The exam stops after **4 minutes**.
- If the code limit is hit, force `{"action": "end", "reason": "Time is up."}`.
- If Gemini returns broken JSON: retry once. If it fails again, ask a generic question on the next untested topic.

### Examiner decide prompt (starting point, lives in `agent/prompts.py`)
```
You are a strict but fair university oral examiner.
Goal: find out what this student does NOT know, in as few questions as possible.
You get: the topic list, the mastery map (score + confidence per topic) and the conversation so far.
Rules: pick the topic with the lowest confidence; follow up if the last answer was vague or scored 30-70;
ask something harder if it scored above 80; end when every topic has at least medium confidence.
Ask ONE short question at a time, like a real professor speaking out loud (max 25 words).
Never repeat a question. Never give the answer away.
Return JSON only: {"action", "topic_id", "question", "reason"}.
The reason is one plain sentence a student would understand, e.g.
"Your answer on valves was vague, so I'm checking the detail."
```

### Grade prompt (starting point)
```
You are grading one oral exam answer. Use ONLY the notes below as the truth.
Return JSON: {"topic_id", "score" (0-100), "evidence" (a short quote from the notes),
"missing" (key points the student left out), "grader_note": null}.
Be fair: give partial credit for correct ideas in different words.
```

---

## 6. SDK hints (check them against the current docs, because APIs change)

```python
# Gemini, JSON output
from google import genai
from google.genai import types
client = genai.Client()  # reads GEMINI_API_KEY
resp = client.models.generate_content(
    model=GEMINI_MODEL,
    contents=[prompt],  # for a PDF add: types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
    config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=Schema),
)
data = resp.parsed or json.loads(resp.text)

# ElevenLabs
from elevenlabs.client import ElevenLabs
el = ElevenLabs()  # reads ELEVENLABS_API_KEY
audio = b"".join(el.text_to_speech.convert(text=text, voice_id=VOICE_ID, model_id=TTS_MODEL, output_format="mp3_44100_128"))
text = el.speech_to_text.convert(file=io.BytesIO(audio_bytes), model_id="scribe_v2").text
```
If you're not sure about an SDK call, **say so and ask me to paste the docs**. Don't guess.
ElevenLabs also publishes skills for AI coding assistants: `npx skills add elevenlabs/skills`.

---

## 7. How to work with me (rules for the AI)

- Build the **simplest version that works**. No extra features, no abstractions "for later", no classes where a function will do.
- Work in **small steps**. After each step, tell me how to run or test it.
- Only touch the files my role owns (see section 3). If you need a shared change, tell me instead of making it.
- Use `shared/fakes.py` for any function a teammate hasn't finished yet.
- Keys come from `.env`. Never hard-code them, and never print them.
- Keep the UI clean and big enough for a projector: large fonts and clear colours.
- Prefer working code over clever code. This is a 5-hour hackathon demo.

---

## 8. My role (edit this line in your own copy)

`I am Person __ (A = agent/brain, B = voice, C = screen + pitch). Current task: ______`
