"""
Chief of Staff — Spécialistes API
Wrappers FastAPI exposant les capacités locales : transcribe, embed, safety.
"""
import subprocess
import tempfile
import time
from pathlib import Path

import httpx
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel

# ===== Configuration =====
HOME = Path.home()
PROJECT_ROOT = HOME / "Desktop" / "chief-of-staff"
WHISPER_MODEL = PROJECT_ROOT / "models" / "whisper" / "ggml-medium.bin"
LITELLM_URL = "http://localhost:4000"
LITELLM_KEY = "sk-cos-local-dev"

app = FastAPI(
    title="Chief of Staff — Specialists",
    description="Wrappers locaux : transcribe, embed, safety",
    version="0.1.0",
)


# ===== Modèles Pydantic =====
class TextRequest(BaseModel):
    text: str


class EmbedResponse(BaseModel):
    vector: list[float]
    dim: int


class SafetyResponse(BaseModel):
    text: str
    safe: bool
    raw: str


class TranscribeResponse(BaseModel):
    text: str
    duration_ms: int


# ===== Endpoints =====
@app.get("/health")
async def health():
    """Vérifie l'accessibilité des dépendances."""
    checks = {"whisper_model": WHISPER_MODEL.exists()}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{LITELLM_URL}/health/liveliness")
            checks["litellm"] = r.status_code == 200
    except Exception:
        checks["litellm"] = False
    return {
        "status": "ok" if all(checks.values()) else "degraded",
        "checks": checks,
    }


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(file: UploadFile = File(...), language: str = "fr"):
    """
    Transcrit un fichier audio en texte via whisper.cpp.
    Audio : .wav 16kHz mono recommandé.
    """
    if not WHISPER_MODEL.exists():
        raise HTTPException(500, f"Whisper model not found at {WHISPER_MODEL}")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        start = time.time()
        result = subprocess.run(
            [
                "whisper-cli",
                "-m", str(WHISPER_MODEL),
                "-l", language,
                "-f", tmp_path,
                "--no-prints",
                "--output-txt",
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )
        duration_ms = int((time.time() - start) * 1000)

        if result.returncode != 0:
            raise HTTPException(500, f"whisper-cli failed: {result.stderr}")

        # whisper-cli écrit le texte dans <input>.txt
        txt_path = Path(tmp_path).with_suffix(".wav.txt")
        if txt_path.exists():
            text = txt_path.read_text(encoding="utf-8").strip()
            txt_path.unlink()
        else:
            text = result.stdout.strip()

        return TranscribeResponse(text=text, duration_ms=duration_ms)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.post("/embed", response_model=EmbedResponse)
async def embed(req: TextRequest):
    """Génère un embedding via Granite Embedding (LiteLLM → Ollama)."""
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{LITELLM_URL}/v1/embeddings",
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            json={"model": "granite-embed", "input": req.text},
        )
        if r.status_code != 200:
            raise HTTPException(500, f"LiteLLM error: {r.text}")
        data = r.json()
        vector = data["data"][0]["embedding"]
        return EmbedResponse(vector=vector, dim=len(vector))


@app.post("/safety", response_model=SafetyResponse)
async def safety(req: TextRequest):
    """Vérifie un texte via Granite Guardian."""
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{LITELLM_URL}/v1/chat/completions",
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            json={
                "model": "granite-guardian",
                "messages": [{"role": "user", "content": req.text}],
                "max_tokens": 20,
            },
        )
        if r.status_code != 200:
            raise HTTPException(500, f"LiteLLM error: {r.text}")
        raw = r.json()["choices"][0]["message"]["content"].strip()
        # Granite Guardian répond "Yes" si risque détecté, "No" sinon
        safe = "no" in raw.lower()
        return SafetyResponse(text=req.text, safe=safe, raw=raw)