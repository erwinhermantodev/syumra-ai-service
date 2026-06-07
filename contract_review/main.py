from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pdfplumber
import requests
import os
import json
import logging
import tempfile

log = logging.getLogger(__name__)
app = FastAPI(title="Syumra Contract Review", version="1.0.0")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434") + "/api/generate"
MODEL = "llama3:8b"

REVIEW_PROMPT = """Kamu adalah AI penganalisis kontrak umroh/haji.
Analisis kontrak berikut dan identifikasi klausul berisiko.
Kembalikan JSON:
{{
  "risk_level": "low|medium|high",
  "risky_clauses": [
    {{"clause": "...", "risk": "...", "recommendation": "..."}}
  ],
  "summary": "ringkasan singkat"
}}
Cari: tanggal keberangkatan tidak jelas, tidak ada kebijakan refund,
tidak ada jaminan hotel, bahasa visa ambigu, pembayaran penuh tanpa cicilan.
Teks kontrak:
{text}"""


class ReviewRequest(BaseModel):
    pdf_url: str
    user_id: str


class RiskyClause(BaseModel):
    clause: str
    risk: str
    recommendation: str


class ReviewResponse(BaseModel):
    risk_level: str
    risky_clauses: list[RiskyClause]
    summary: str


def extract_pdf_text(url: str) -> str:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(r.content)
        tmp_path = f.name
    with pdfplumber.open(tmp_path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def _parse_ollama_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        if len(parts) >= 2:
            raw = parts[1]
            if raw.startswith("json"):
                raw = raw[4:]
    return json.loads(raw.strip())


@app.post("/review", response_model=ReviewResponse)
def review_contract(req: ReviewRequest) -> ReviewResponse:
    try:
        text = extract_pdf_text(req.pdf_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot read PDF: {e}")

    prompt = REVIEW_PROMPT.format(text=text[:3000])
    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 1024},
            },
            timeout=90,
        )
        r.raise_for_status()
        data = _parse_ollama_json(r.json()["response"])
        return ReviewResponse(
            risk_level=data.get("risk_level", "medium"),
            risky_clauses=[RiskyClause(**c) for c in data.get("risky_clauses", [])],
            summary=data.get("summary", ""),
        )
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Contract review failed: {e}")
        raise HTTPException(status_code=500, detail="AI review failed")


@app.get("/health")
def health():
    return {"status": "ok", "service": "contract_review"}
