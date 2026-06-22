"""
Meeting recording post-processing pipeline.

1. Transcribe via the specialists FastAPI (whisper.cpp wrapper)
2. Synthesize a structured summary via Granite 4 tiny-h
3. Save the markdown note into the Obsidian vault
4. Index it in Qdrant for future RAG search

Usage:
    python process.py <audio_file.wav> [project] [topic]

Anti-hallucination guards:
- is_transcript_meaningful() filters out silence and noise-tag-only transcripts
  before they reach Granite (prevents fabricated summaries from silence).
- A 'no speech' note is saved instead of running synthesis on empty audio.
- The SYNTHESIS_PROMPT contains hard rules forbidding the model from
  inventing decisions, actions, or topics not present in the transcript.
"""
import sys
import json
import re
from datetime import datetime
from pathlib import Path

import httpx


# ===== Configuration =====
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VAULT_DIR = PROJECT_ROOT / "vault"
MEETINGS_DIR = VAULT_DIR / "meetings"

SPECIALISTS_URL = "http://localhost:8001"
LITELLM_URL = "http://localhost:4000"
LITELLM_KEY = "sk-cos-local-dev"
QDRANT_URL = "http://localhost:6333"
COLLECTION = "documents"

LLM_MODEL = "granite-tiny"
EMBED_MODEL = "granite-embed"


# ===== Step 1: Transcription =====
def transcribe(audio_path: Path) -> dict:
    """Call the FastAPI /transcribe wrapper (whisper.cpp)."""
    print(f"🎙️  Transcription via whisper.cpp...")
    with open(audio_path, "rb") as f:
        with httpx.Client(timeout=600) as client:
            r = client.post(
                f"{SPECIALISTS_URL}/transcribe",
                files={"file": (audio_path.name, f, "audio/wav")},
                data={"language": "fr"},
            )
            r.raise_for_status()
            data = r.json()
            print(f"   → {len(data['text'])} characters in {data['duration_ms']/1000:.1f}s")
            return data


# ===== Anti-hallucination guard =====
def is_transcript_meaningful(transcript: str) -> bool:
    """
    Decide whether a transcript actually contains speech worth summarizing.

    Returns False when Whisper output is just silence markers, hum tags,
    or extremely short noise — to avoid Granite hallucinating a summary
    from nothing.

    Why this matters: Whisper on silent audio emits things like
    "[Bourdonnement]\n[Bourdonnement]\n..." which is long enough to pass
    a naive `len(text) > 20` check, but contains zero real content.
    Without this guard, Granite confidently fabricates a meeting summary
    from its `USER_PROFILE` and `PROJECT_CONTEXT` instead.
    """
    text = transcript.strip()

    # Too short overall
    if len(text) < 50:
        return False

    # Strip Whisper noise tags: [Bourdonnement], [Music], [silence], [hum]...
    cleaned = re.sub(r"\[[^\]]*\]", "", text).strip()

    # If after removing tags there's almost no real text left, it's noise only
    if len(cleaned) < 50:
        return False

    # Count "real" words (3+ letters) to avoid considering "uh ah ok" as content
    real_words = re.findall(r"\b[a-zA-ZÀ-ÿ]{3,}\b", cleaned)
    if len(real_words) < 10:
        return False

    return True


# ===== Step 2: Structured synthesis =====
SYNTHESIS_PROMPT = """You are a meeting note assistant. Your ONLY job is to summarize ACTUAL CONTENT from the transcript below.

═══════════════════════════════════════════════
🔒 ABSOLUTE RULES — READ FIRST
═══════════════════════════════════════════════

1. Base your summary STRICTLY on what is in the transcript.
2. NEVER invent decisions, actions, names, dates, or topics.
3. NEVER use information from outside the transcript (no general knowledge,
   no assumptions about projects, organizations, teams, or anything else).
4. If the transcript is unclear, fragmented, or contains mostly silence/noise
   markers like [Bourdonnement], [silence], [Music], etc.:
   → write "Aucun contenu exploitable dans cette réunion." in every section.
   → DO NOT fabricate plausible-sounding meeting content.

═══════════════════════════════════════════════

Generate the meeting note in French in this exact structure:

# Résumé
[3-4 sentences MAX, factual, ONLY based on what was actually said. If nothing
substantive was said, write: "Aucun contenu exploitable dans cette réunion."]

# Décisions
- [decision 1, only if explicitly stated in the transcript]
[If no decisions were made: write "Aucune"]

# Actions
- [ ] @who : what (deadline if mentioned)
[Only list actions explicitly stated. If none: write "Aucune"]

# Questions ouvertes
- [question raised but not answered]
[If none: write "Aucune"]

# Sujets abordés
- [topic 1 actually discussed]
[If transcript has no real content: write "Aucun"]

═══════════════════════════════════════════════

TRANSCRIPT TO SUMMARIZE:
{transcript}
"""


def synthesize(transcript: str) -> str:
    """Generate a structured summary via Granite 4 tiny-h."""
    print(f"🧠 Synthesis via {LLM_MODEL}...")
    with httpx.Client(timeout=300) as client:
        r = client.post(
            f"{LITELLM_URL}/v1/chat/completions",
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "user", "content": SYNTHESIS_PROMPT.format(transcript=transcript)},
                ],
                "temperature": 0.3,
                "max_tokens": 2000,
            },
        )
        r.raise_for_status()
        synthesis = r.json()["choices"][0]["message"]["content"].strip()
        print(f"   → {len(synthesis)} characters of synthesis")
        return synthesis


# ===== Step 3: Save to vault =====
def slugify(text: str, max_len: int = 50) -> str:
    """Turn a text into a safe filename."""
    s = re.sub(r"[^\w\s-]", "", text.lower())
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    return s[:max_len] or "meeting"


def save_to_vault(
    audio_path: Path,
    transcript: str,
    synthesis: str,
    project: str,
    topic: str | None,
    duration_s: float,
) -> Path:
    """Save the meeting note as Markdown in the Obsidian vault."""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    year_month = now.strftime("%Y/%m")

    out_dir = MEETINGS_DIR / year_month
    out_dir.mkdir(parents=True, exist_ok=True)

    topic_slug = slugify(topic) if topic else slugify(audio_path.stem)
    filename = f"{date_str}_{topic_slug}.md"
    out_path = out_dir / filename

    front_matter = f"""---
date: {date_str}
time: {now.strftime("%H:%M")}
project: {project}
topic: {topic or "(non spécifié)"}
duration_seconds: {duration_s:.0f}
audio_file: {audio_path.name}
type: meeting
tags: [meeting, {project}]
---

"""

    body = f"""{synthesis}

---

## Raw transcript

> Source: `{audio_path.name}` ({duration_s:.0f}s)

{transcript}
"""

    out_path.write_text(front_matter + body, encoding="utf-8")
    print(f"📝 Saved: {out_path}")
    return out_path


def save_silent_meeting_note(
    audio_path: Path,
    transcript: str,
    project: str,
    topic: str | None,
    duration_s: float,
) -> Path:
    """
    Save an honest 'no usable content' meeting note when the audio
    had no real speech. Better than silently dropping the recording.
    """
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    year_month = now.strftime("%Y/%m")

    out_dir = MEETINGS_DIR / year_month
    out_dir.mkdir(parents=True, exist_ok=True)

    topic_slug = slugify(topic) if topic else slugify(audio_path.stem)
    filename = f"{date_str}_{topic_slug}_NO_SPEECH.md"
    out_path = out_dir / filename

    content = f"""---
date: {date_str}
time: {now.strftime("%H:%M")}
project: {project}
topic: {topic or "(non spécifié)"}
duration_seconds: {duration_s:.0f}
audio_file: {audio_path.name}
type: meeting_no_speech
tags: [meeting, no_speech, {project}]
---

# ⚠️ No meaningful speech detected

The recording was processed but Whisper did not detect actual speech content.

Common causes:
- The system output was not routed to the Multi-Output Device (BlackHole + speakers)
- The microphone level was too low
- Only ambient noise was captured ([Bourdonnement], [silence], etc.)

**No summary was generated** to avoid hallucination.

## Raw transcript (for inspection)

```
{transcript}
```

## Audio file

`{audio_path}` ({duration_s:.0f}s)
"""

    out_path.write_text(content, encoding="utf-8")
    print(f"📝 Saved 'no speech' note: {out_path}")
    return out_path


# ===== Step 4: Index in Qdrant =====
def index_in_qdrant(md_path: Path, project: str):
    """Index the meeting note in Qdrant for future RAG search."""
    print(f"💾 Indexing in Qdrant...")
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct
    import uuid

    text = md_path.read_text(encoding="utf-8")

    with httpx.Client(timeout=120) as client:
        r = client.post(
            f"{LITELLM_URL}/v1/embeddings",
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            json={"model": EMBED_MODEL, "input": text[:8000]},
        )
        r.raise_for_status()
        vector = r.json()["data"][0]["embedding"]

    client = QdrantClient(url=QDRANT_URL)
    point = PointStruct(
        id=str(uuid.uuid4()),
        vector=vector,
        payload={
            "source": md_path.name,
            "path": str(md_path),
            "project": project,
            "type": "meeting",
            "text": text[:2000],
        },
    )
    client.upsert(collection_name=COLLECTION, points=[point])
    print(f"   → indexed (id={point.id[:8]}...)")


# ===== Full pipeline =====
def process(audio_path: Path, project: str = "default", topic: str | None = None):
    """Run the full pipeline."""
    if not audio_path.exists():
        print(f"❌ File not found: {audio_path}")
        sys.exit(1)

    print(f"\n🎬 Processing {audio_path.name}\n")

    # 1. Transcription
    trans_data = transcribe(audio_path)
    transcript = trans_data["text"]
    duration_s = trans_data["duration_ms"] / 1000

    # 2. Guard: meaningful content check (prevents hallucination from silence)
    if not is_transcript_meaningful(transcript):
        print("⚠️  No meaningful speech detected — saving honest 'no speech' note.")
        save_silent_meeting_note(audio_path, transcript, project, topic, duration_s)
        return

    # 3. Synthesis
    synthesis = synthesize(transcript)

    # 4. Markdown vault
    md_path = save_to_vault(
        audio_path, transcript, synthesis, project, topic, duration_s
    )

    # 5. Qdrant indexing
    try:
        index_in_qdrant(md_path, project)
    except Exception as e:
        print(f"⚠️  Qdrant indexing failed: {e}")

    print(f"\n🎉 Pipeline complete for {audio_path.name}")
    print(f"   → Meeting note: {md_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process.py <audio.wav> [project] [topic]")
        sys.exit(1)

    audio = Path(sys.argv[1])
    proj = sys.argv[2] if len(sys.argv) > 2 else "default"
    top = sys.argv[3] if len(sys.argv) > 3 else None

    process(audio, proj, top)
