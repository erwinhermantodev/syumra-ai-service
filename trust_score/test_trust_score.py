from fastapi.testclient import TestClient
from trust_score.main import app

client = TestClient(app)


def test_compute_trust_score_perfect_agent():
    response = client.post("/compute", json={
        "ppiu_verified": True,
        "years_active": 10,
        "complaint_rate": 0.0,
        "review_sentiment": 1.0,
        "price_consistency": 1.0,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 100
    assert data["tier"] == "green"


def test_compute_trust_score_unverified_agent():
    response = client.post("/compute", json={
        "ppiu_verified": False,
        "years_active": 0,
        "complaint_rate": 1.0,
        "review_sentiment": 0.0,
        "price_consistency": 0.0,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 0
    assert data["tier"] == "red"


def test_compute_trust_score_partial_agent():
    """ppiu(30) + 5yrs(10) + complaint_0.5(10) + sentiment_0.5(7.5) + price_0.5(7.5) = 65"""
    response = client.post("/compute", json={
        "ppiu_verified": True,
        "years_active": 5,
        "complaint_rate": 0.5,
        "review_sentiment": 0.5,
        "price_consistency": 0.5,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 65
    assert data["tier"] == "amber"


def test_compute_trust_score_amber_boundary():
    """Score of exactly 40 should be amber."""
    # ppiu=False(0) + years=10(20) + complaint=0(20) + sentiment=0(0) + price=0(0) = 40
    response = client.post("/compute", json={
        "ppiu_verified": False,
        "years_active": 10,
        "complaint_rate": 0.0,
        "review_sentiment": 0.0,
        "price_consistency": 0.0,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 40
    assert data["tier"] == "amber"


def test_score_clamped_above_100():
    """Over-spec inputs must not exceed 100."""
    response = client.post("/compute", json={
        "ppiu_verified": True,
        "years_active": 999,
        "complaint_rate": -5,
        "review_sentiment": 99,
        "price_consistency": 99,
    })
    assert response.status_code == 200
    assert response.json()["score"] == 100


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "trust_score"
