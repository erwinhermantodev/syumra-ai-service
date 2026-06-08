from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os
import logging
import json

log = logging.getLogger(__name__)
app = FastAPI(title="Syumra Scam Detector", version="1.0.0")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434") + "/api/generate"
MODEL = "llama3"

SCAM_PROMPT = """Kamu adalah sistem deteksi penipuan travel umroh/haji.
Analisis teks agen berikut dan kembalikan JSON:
{{
  "scam_probability": 0.0-1.0,
  "red_flags": ["list of flags"],
  "reasoning": "singkat"
}}
Red flags yang dicari: harga jauh di bawah pasar, tekanan bayar penuh,
tidak ada alamat, akun baru, tidak ada nomor PPIU.
Balas HANYA dengan JSON, tidak ada teks lain.

Teks agen: {text}"""


class ScamRequest(BaseModel):
    agent_text: str
    agent_name: str = ""


class ScamResponse(BaseModel):
    scam_probability: float
    red_flags: list[str]
    reasoning: str


def _parse_ollama_json(raw: str) -> dict:
    """Strip markdown code fences and parse JSON from Ollama response."""
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        if len(parts) >= 2:
            raw = parts[1]
            if raw.startswith("json"):
                raw = raw[4:]
    return json.loads(raw.strip())


@app.post("/analyze", response_model=ScamResponse)
def analyze_scam(req: ScamRequest) -> ScamResponse:
    prompt = SCAM_PROMPT.format(text=req.agent_text[:1000])
    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 256},
            },
            timeout=60,
        )
        r.raise_for_status()
        data = _parse_ollama_json(r.json()["response"])
        return ScamResponse(
            scam_probability=float(data.get("scam_probability", 0.5)),
            red_flags=data.get("red_flags", []),
            reasoning=data.get("reasoning", ""),
        )
    except Exception as e:
        log.error(f"Scam analysis failed: {e}")
        return ScamResponse(
            scam_probability=0.5,
            red_flags=[],
            reasoning="analysis_failed",
        )


@app.get("/health")
def health():
    return {"status": "ok", "service": "scam_detector"}
