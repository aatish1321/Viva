"""Check that the API keys in .env work. Run: uv run python scripts/check_setup.py"""
import io
import os
import time
from pathlib import Path

from dotenv import load_dotenv

GEMINI_MODEL = "gemini-3.8-flash"
TTS_MODEL = "eleven_v4_turbo"
STT_MODEL = "scribe_v3"
KEYS = ["GEMINI_API_KEY", "ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID"]
MP3 = Path(__file__).parent / "test.mp3"

load_dotenv()


def check(name, fix, fn):
    start = time.time()
    try:
        result = fn()
        print(f"✅ {name} ({time.time() - start:.1f}s) {result or ''}")
        return True
    except Exception as e:
        detail = getattr(e, "body", None) or str(e)  # ElevenLabs ApiError's str() is mostly headers
        print(f"❌ {name} ({time.time() - start:.1f}s): {type(e).__name__}: {str(detail)[:300]}\n   Fix: {fix}")
        return False


def present(k):
    return os.getenv(k, "") not in ("", "paste_here")


def keys():
    for k in KEYS:
        print(f"   {k}: {'present' if present(k) else 'missing'}")
    missing = [k for k in KEYS if not present(k)]
    if missing:
        raise RuntimeError(f"missing {', '.join(missing)}")


def gemini():
    from google import genai
    client = genai.Client()  # keep a reference: a garbage-collected client closes mid-request
    resp = client.models.generate_content(model=GEMINI_MODEL, contents="Say hi in 3 words")
    return f"-> {resp.text.strip()!r}"


def tts():
    from elevenlabs.client import ElevenLabs
    audio = b"".join(ElevenLabs().text_to_speech.convert(
        voice_id=os.environ["ELEVENLABS_VOICE_ID"], text="Welcome to your oral exam.",
        model_id=TTS_MODEL, output_format="mp3_44100_128"))
    MP3.write_bytes(audio)
    return f"-> saved {MP3} ({len(audio)} bytes)"


def stt():
    from elevenlabs.client import ElevenLabs
    text = ElevenLabs().speech_to_text.convert(file=io.BytesIO(MP3.read_bytes()), model_id=STT_MODEL).text
    return f"-> {text!r}"


ok = check("Keys", "Copy .env.example to .env and fill in every value.", keys)
ok &= check("Gemini", f"Check GEMINI_API_KEY at https://aistudio.google.com/apikey and that {GEMINI_MODEL} exists.", gemini)
tts_ok = check("ElevenLabs TTS", "Check ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID in your ElevenLabs dashboard.", tts)
ok &= tts_ok
if tts_ok:
    ok &= check("ElevenLabs STT", "Check ELEVENLABS_API_KEY has Speech to Text access.", stt)
else:
    print("❌ ElevenLabs STT skipped: needs test.mp3 from the TTS check.")
    ok = False
print("\nAll checks passed." if ok else "\nSome checks failed.")
