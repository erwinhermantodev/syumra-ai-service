import chromadb
from chromadb.utils import embedding_functions
import os

client = chromadb.HttpClient(host=os.getenv("CHROMA_HOST", "localhost"), port=8000)
ef = embedding_functions.OllamaEmbeddingFunction(
    url=os.getenv("OLLAMA_URL", "http://localhost:11434") + "/api/embeddings",
    model_name="nomic-embed-text",
)
collection = client.get_or_create_collection("manasik_knowledge", embedding_function=ef)

SEED_DOCS = [
    {"text": "Tawaf adalah mengelilingi Ka'bah sebanyak 7 kali berlawanan arah jarum jam dimulai dari Hajar Aswad.", "phase": "ritual", "topic": "tawaf", "lang": "id"},
    {"text": "Sa'i adalah berjalan bolak-balik antara Bukit Shafa dan Marwa sebanyak 7 kali.", "phase": "ritual", "topic": "sai", "lang": "id"},
    {"text": "Wukuf di Arafah adalah rukun Haji yang paling utama, dilaksanakan pada 9 Dzulhijjah mulai Dzuhur hingga Maghrib.", "phase": "ritual", "topic": "wukuf", "lang": "id"},
    {"text": "Mabit di Muzdalifah dilakukan setelah wukuf Arafah, mengumpulkan batu untuk lempar jumrah.", "phase": "ritual", "topic": "mabit", "lang": "id"},
    {"text": "Jumrah adalah melempar batu ke tiga tiang: Ula, Wusta, dan Aqabah.", "phase": "ritual", "topic": "jumrah", "lang": "id"},
    {"text": "Dokumen wajib sebelum keberangkatan: paspor valid ≥6 bulan, visa, kartu meningitis, surat mahram (jika perlu).", "phase": "predeparture", "topic": "documents", "lang": "id"},
    {"text": "Tawaf circumambulates the Kaaba 7 times counter-clockwise starting from the Black Stone (Hajar Aswad).", "phase": "ritual", "topic": "tawaf", "lang": "en"},
]

try:
    existing_ids = set(collection.get()["ids"])
except Exception:
    existing_ids = set()

new_docs = [d for i, d in enumerate(SEED_DOCS) if f"doc_{i}" not in existing_ids]
if new_docs:
    indices = [i for i, d in enumerate(SEED_DOCS) if f"doc_{i}" not in existing_ids]
    collection.add(
        documents=[d["text"] for d in new_docs],
        metadatas=[{"phase": d["phase"], "topic": d["topic"], "lang": d["lang"]} for d in new_docs],
        ids=[f"doc_{i}" for i in indices],
    )
    print(f"Ingested {len(new_docs)} documents into manasik_knowledge")
else:
    print("Knowledge base already up to date")
