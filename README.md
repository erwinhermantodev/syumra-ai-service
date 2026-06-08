# Syumra AI Services

A Python-based AI microservices monorepo that powers the intelligent features of the [Syumra](https://syumra.id) Hajj & Umrah platform. It provides four independent FastAPI services plus a data pipeline, all backed by a local LLM (via Ollama) and a vector database (ChromaDB).

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Services](#services)
  - [Guidance Chat](#1-guidance-chat--port-8004)
  - [Scam Detector](#2-scam-detector--port-8001)
  - [Trust Score](#3-trust-score--port-8002)
  - [Contract Review](#4-contract-review--port-8003)
- [Data Pipeline](#data-pipeline)
- [Knowledge Base](#knowledge-base)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Environment Variables](#environment-variables)
- [Running Services](#running-services)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Project Structure](#project-structure)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│               Syumra Backend (Go)               │
│            api.syumra.id/api/v1/…               │
└──────────┬──────────┬──────────┬────────────────┘
           │          │          │
    :8004  │   :8001  │   :8002  │   :8003
     ▼           ▼          ▼          ▼
┌─────────┐ ┌─────────┐ ┌──────────┐ ┌──────────────┐
│Guidance │ │  Scam   │ │  Trust   │ │  Contract    │
│  Chat   │ │Detector │ │  Score   │ │   Review     │
└────┬────┘ └────┬────┘ └──────────┘ └──────┬───────┘
     │           │                           │
     ▼           ▼                           ▼
┌──────────────────────────────────────────────────┐
│           Ollama (LLM — llama3)                  │
│               localhost:11434                    │
└──────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────┐
│           ChromaDB (Vector Store)                │
│               localhost:8000                     │
└──────────────────────────────────────────────────┘
```

**Tech stack:** Python 3.11 · FastAPI · Uvicorn · Ollama (llama3) · ChromaDB · Playwright · pdfplumber · PostgreSQL

---

## Services

### 1. Guidance Chat — port `8004`

An AI-powered Q&A assistant for Hajj & Umrah pilgrims. It retrieves relevant passages from a curated knowledge base (ChromaDB) and generates answers using a local LLM. Automatically replies in the **same language as the question** (Indonesian / Arabic / English).

**Endpoint:** `POST /chat`

```json
// Request
{
  "text": "Apa saja rukun umrah?",
  "user_id": "usr_123",
  "phase": "ritual",
  "lang": "id"
}

// Response
{
  "answer": "Rukun Umrah ada 5 perkara...",
  "lang": "id",
  "sources": ["Rukun Umrah ada 5 perkara...", "..."]
}
```

**`phase` values:** `predeparture` | `departure` | `ritual` | `daily` | `return`

**`lang` values:** `id` (Indonesian) | `ar` (Arabic) | `en` (English)

---

### 2. Scam Detector — port `8001`

Analyzes travel agent text to detect potential Hajj/Umrah fraud. Uses a local LLM with a specialized prompt to identify red flags such as suspiciously low prices, absence of a PPIU license number, or high-pressure sales tactics.

**Endpoint:** `POST /analyze`

```json
// Request
{
  "agent_text": "Umrah murah PROMO hanya Rp 8 juta! Bayar lunas sekarang...",
  "agent_name": "Travel Maju Mundur"
}

// Response
{
  "scam_probability": 0.87,
  "red_flags": ["harga jauh di bawah pasar", "tekanan bayar penuh", "tidak ada nomor PPIU"],
  "reasoning": "Harga sangat di bawah rata-rata pasar dan tidak ada nomor lisensi resmi."
}
```

---

### 3. Trust Score — port `8002`

Computes a deterministic 0–100 trust score for a travel agent using a weighted formula. No LLM involved — fully rule-based and fast.

**Scoring formula:**

| Factor | Weight | Description |
|---|---|---|
| PPIU Registry Verified | 30 pts | Boolean — registered with Kemenag |
| Years Active | 20 pts | Capped at 10 years |
| Low Complaint Rate | 20 pts | `(1 - complaint_rate) × 20` |
| Positive Review Sentiment | 15 pts | `sentiment × 15` |
| Price Consistency | 15 pts | `price_consistency × 15` |

**Tier:** `green` ≥ 70 · `amber` 40–69 · `red` < 40

**Endpoint:** `POST /compute`

```json
// Request
{
  "ppiu_verified": true,
  "years_active": 7.5,
  "complaint_rate": 0.05,
  "review_sentiment": 0.85,
  "price_consistency": 0.90
}

// Response
{
  "score": 89,
  "tier": "green"
}
```

---

### 4. Contract Review — port `8003`

Downloads a PDF contract from a URL, extracts the text, and uses a local LLM to identify risky clauses (e.g. missing refund policy, ambiguous departure dates, full-payment-only terms).

**Endpoint:** `POST /review`

```json
// Request
{
  "pdf_url": "https://example.com/contract.pdf",
  "user_id": "usr_123"
}

// Response
{
  "risk_level": "high",
  "risky_clauses": [
    {
      "clause": "Tidak ada kebijakan refund",
      "risk": "Jamaah berisiko kehilangan seluruh uang jika ada pembatalan.",
      "recommendation": "Minta klausul refund minimal 50% jika dibatalkan 30 hari sebelum keberangkatan."
    }
  ],
  "summary": "Kontrak memiliki 2 klausul berisiko tinggi terkait refund dan tanggal keberangkatan."
}
```

---

## Data Pipeline

The pipeline is responsible for collecting, normalizing, and indexing data into ChromaDB.

```
pipeline/
├── scrapers/
│   ├── kemenag_scraper.py      # Scrapes official PPIU agent list from haji.kemenag.go.id
│   └── web_signal_scraper.py   # Collects scam signals and travel agent reviews
└── etl/
│   └── normalizer.py           # Normalizes and deduplicates scraped data
└── guidance/
    └── build_kb.py             # Seeds the ChromaDB manasik_knowledge collection
```

### Running the pipeline

```bash
# 1. Scrape official Kemenag PPIU registry → writes to PostgreSQL
make scrape-kemenag

# 2. Scrape web signals (scam reports, reviews)
make scrape-signals

# 3. Run both scrapers + ETL normalization
make scrape-all

# 4. Build / rebuild the ChromaDB knowledge base for the Guidance Chat
make build-kb
```

> **Safety check:** The Kemenag scraper aborts the database write if it parses fewer than 100 agents, preventing corrupted data from a page layout change.

---

## Knowledge Base

The Guidance Chat retrieves answers from the `manasik_knowledge` ChromaDB collection, seeded with curated Islamic jurisprudence content:

| Folder | Content |
|---|---|
| `knowledge/manasik/` | Complete Hajj & Umrah ritual guides (rukun, wajib, larangan) |
| `knowledge/doa/` | Prayers (dua) specific to each ritual phase |
| `knowledge/kemenag/` | Official Kemenag regulations and announcements |

Documents are tagged with `phase`, `topic`, and `lang` metadata for filtered retrieval.

---

## Prerequisites

| Dependency | Version | Purpose |
|---|---|---|
| Python | ≥ 3.11 | Runtime |
| [Ollama](https://ollama.com) | latest | Local LLM server |
| ChromaDB | 0.5.x | Vector store (via Docker) |
| PostgreSQL | ≥ 14 | Agent verification data |

### Install Ollama and pull the model

```bash
# Install Ollama (macOS)
brew install ollama

# Pull the required model
ollama pull llama3
```

---

## Setup

```bash
# 1. Clone the repository
git clone git@github.com:erwinhermantodev/syumra-ai-service.git
cd syumra-ai-service

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install all dependencies (includes Playwright for scraping)
make install

# 4. Copy and configure environment variables
cp .env.example .env
# Edit .env with your actual values

# 5. Start ChromaDB with Docker
docker-compose up -d

# 6. Seed the guidance knowledge base
make build-kb
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | — | PostgreSQL connection string |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `CHROMA_HOST` | `localhost` | ChromaDB host |
| `REDIS_URL` | `redis://localhost:6379` | Redis (reserved for future caching) |

Copy `.env.example` to `.env` and fill in values before starting services.

---

## Running Services

Each service can be started individually. All support `--reload` for development.

```bash
# Guidance Chat      → http://localhost:8004
make run-guidance

# Scam Detector      → http://localhost:8001
make run-scam

# Trust Score        → http://localhost:8002
make run-trust

# Contract Review    → http://localhost:8003
make run-contract
```

### Health checks

Every service exposes a `GET /health` endpoint:

```bash
curl http://localhost:8004/health
# {"status":"ok","service":"guidance"}

curl http://localhost:8001/health
# {"status":"ok","service":"scam_detector"}

curl http://localhost:8002/health
# {"status":"ok","service":"trust_score"}

curl http://localhost:8003/health
# {"status":"ok","service":"contract_review"}
```

### Interactive API docs

Each FastAPI service exposes Swagger UI automatically:

- Guidance: http://localhost:8004/docs
- Scam Detector: http://localhost:8001/docs
- Trust Score: http://localhost:8002/docs
- Contract Review: http://localhost:8003/docs

---

## API Reference

### Common response wrapper (from the Go backend)

All endpoints exposed via the Go backend return:

```json
{
  "success": true,
  "data": { /* service-specific payload */ },
  "error": null
}
```

### Backend routes

| Method | Path | Service |
|---|---|---|
| `POST` | `/api/v1/guidance/chat` | Guidance Chat |
| `POST` | `/api/v1/scam/analyze` | Scam Detector |
| `POST` | `/api/v1/agents/{id}/trust` | Trust Score |
| `POST` | `/api/v1/contracts/review` | Contract Review |

---

## Testing

```bash
# Run all tests with verbose output
make test

# Or directly with pytest
python -m pytest -v
```

Tests cover:
- **Trust Score** — boundary conditions (green/amber/red tiers, score clamping, unverified agents)
- **Scam Detector** — response structure and fallback behavior
- **Guidance Chat** — ChromaDB unavailable fallback, language routing

---

## Project Structure

```
syumra-ai-services/
├── guidance/                   # Hajj/Umrah AI chat service (port 8004)
│   └── main.py
├── scam_detector/              # Scam analysis service (port 8001)
│   ├── main.py
│   └── test_scam_detector.py
├── trust_score/                # Trust scoring service (port 8002)
│   ├── main.py
│   └── test_trust_score.py
├── contract_review/            # PDF contract review service (port 8003)
│   └── main.py
├── pipeline/
│   ├── scrapers/
│   │   ├── kemenag_scraper.py  # Official PPIU registry scraper
│   │   └── web_signal_scraper.py
│   ├── etl/
│   │   └── normalizer.py       # Data normalization & deduplication
│   └── guidance/
│       └── build_kb.py         # ChromaDB knowledge base seeder
├── knowledge/
│   ├── manasik/                # Ritual guide documents
│   ├── doa/                    # Prayer texts
│   └── kemenag/                # Kemenag regulations
├── docker-compose.yml          # ChromaDB container
├── Makefile                    # Developer shortcuts
├── requirements.txt            # Python dependencies
└── .env.example                # Environment variable template
```

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Run tests before committing: `make test`
4. Open a Pull Request targeting `master`

---

## License

© 2025 Syumra. All rights reserved.
