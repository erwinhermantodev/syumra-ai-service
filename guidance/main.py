from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os
import logging

log = logging.getLogger(__name__)
app = FastAPI(title="Syumra Guidance Chat", version="1.0.0")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434") + "/api/generate"
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")

SYSTEM_PROMPT: dict[str, str] = {
    "id": (
        "Kamu adalah asisten panduan ibadah Haji/Umrah yang berpengetahuan luas. "
        "Jawab berdasarkan sumber Islam yang sahih (Quran, Hadis, fiqh muktamad). "
        "Gunakan bahasa yang mudah dipahami jamaah awam. "
        "Tambahkan disclaimer: 'Konsultasikan dengan ustadz untuk kepastian hukum.'"
    ),
    "ar": "أنت مرشد متخصص في مناسك الحج والعمرة. أجب بناءً على المصادر الإسلامية الصحيحة.",
    "en": (
        "You are a knowledgeable Hajj/Umrah guide assistant. "
        "Answer based on authentic Islamic sources. Be clear and practical."
    ),
}


class GuidanceQuery(BaseModel):
    text: str
    user_id: str
    phase: str = "ritual"  # predeparture | departure | ritual | daily | return
    lang: str = "id"       # id | ar | en


class GuidanceResponse(BaseModel):
    answer: str
    lang: str
    sources: list[str]


def _retrieve_context(query: str, phase: str) -> list[str]:
    """Retrieve relevant chunks from ChromaDB. Returns [] if unavailable."""
    try:
        import chromadb
        client = chromadb.HttpClient(host=CHROMA_HOST, port=8000)
        collection = client.get_collection("manasik_knowledge")
        where = {"phase": phase} if phase else None
        results = collection.query(
            query_texts=[query],
            n_results=4,
            where=where,
        )
        return results["documents"][0] if results["documents"] else []
    except Exception as e:
        log.warning(f"ChromaDB unavailable, proceeding without context: {e}")
        return []


@app.post("/chat", response_model=GuidanceResponse)
def guidance_chat(q: GuidanceQuery) -> GuidanceResponse:
    lang = q.lang if q.lang in SYSTEM_PROMPT else "id"
    context_docs = _retrieve_context(q.text, q.phase)
    context = "\n\n".join(context_docs) if context_docs else "Tidak ada konteks tambahan."

    prompt = f"""{SYSTEM_PROMPT[lang]}

Konteks referensi:
{context}

Pertanyaan: {q.text}
Jawaban:"""

    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                "model": "llama3:8b",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 512},
            },
            timeout=90,
        )
        r.raise_for_status()
        answer = r.json()["response"].strip()
    except Exception as e:
        log.error(f"Ollama call failed: {e}")
        answer = "Maaf, layanan AI sedang tidak tersedia. Silakan coba lagi nanti."

    return GuidanceResponse(answer=answer, lang=lang, sources=context_docs[:2])


@app.get("/health")
def health():
    return {"status": "ok", "service": "guidance"}
