from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Syumra Trust Score Service", version="1.0.0")


class AgentData(BaseModel):
    ppiu_verified: bool
    years_active: float
    complaint_rate: float    # 0.0–1.0
    review_sentiment: float  # 0.0–1.0
    price_consistency: float # 0.0–1.0


class TrustScoreResponse(BaseModel):
    score: int
    tier: str  # green / amber / red


@app.post("/compute", response_model=TrustScoreResponse)
def compute_trust_score(agent: AgentData) -> TrustScoreResponse:
    """
    Weighted trust score formula:
      30pts  — PPIU registry verified
      20pts  — years active (capped at 10 years)
      20pts  — low complaint rate
      15pts  — positive review sentiment
      15pts  — price consistency

    Tier: green >= 70 | amber 40–69 | red < 40
    """
    score = 0.0
    score += 30 if agent.ppiu_verified else 0
    score += 20 * min(agent.years_active / 10, 1.0)
    score += 20 * (1.0 - max(0.0, min(agent.complaint_rate, 1.0)))
    score += 15 * max(0.0, min(agent.review_sentiment, 1.0))
    score += 15 * max(0.0, min(agent.price_consistency, 1.0))
    final = int(round(max(0.0, min(score, 100.0))))
    tier = "green" if final >= 70 else ("amber" if final >= 40 else "red")
    return TrustScoreResponse(score=final, tier=tier)


@app.get("/health")
def health():
    return {"status": "ok", "service": "trust_score"}
