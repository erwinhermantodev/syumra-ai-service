.PHONY: install scrape-kemenag scrape-signals scrape-all etl build-kb run-scam run-trust run-contract run-guidance test

install:
	pip install -r requirements.txt
	playwright install chromium

scrape-kemenag:
	python pipeline/scrapers/kemenag_scraper.py

scrape-signals:
	python pipeline/scrapers/web_signal_scraper.py

scrape-all:
	python pipeline/scrapers/kemenag_scraper.py
	python pipeline/scrapers/web_signal_scraper.py
	python pipeline/etl/normalizer.py

etl:
	python pipeline/etl/normalizer.py

build-kb:
	python pipeline/guidance/build_kb.py

run-scam:
	uvicorn scam_detector.main:app --port 8001 --reload

run-trust:
	uvicorn trust_score.main:app --port 8002 --reload

run-contract:
	uvicorn contract_review.main:app --port 8003 --reload

run-guidance:
	uvicorn guidance.main:app --port 8004 --reload

test:
	python -m pytest -v
