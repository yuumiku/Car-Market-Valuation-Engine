# Tunisian Car Market Valuation Engine

Status: Work in Progress (WIP)

ML-based system to scrape, process, and predict prices for used cars from the Tunisian market.

This repository is currently under development. The scraper foundatio is in place, but the data pipeline, model training, and prediction workflows are still being completed.

## Quick Start

### Prerequisites
- Python 3.8+
- Virtual environment (venv)

### Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure environment variables:**
Create a `.env` file in the project root with necessary credentials.

## Running the Project

### Scrape Data
```bash
scrapy crawl "Automobile TN"
```

### Run Tests
```bash
pytest scrapers/tests/
```

### Train Model
```bash
python model/train.py
```

### Make Predictions
```bash
python model/predict.py
```

### Run Data Pipeline
```bash
python pipeline/normalize.py

python pipeline/validate.py

python pipeline/deduplicate.py
```

### Start Infrastructure (Docker)
```bash
docker-compose -f infra/docker-compose.yml up
```

Prometheus: `http://localhost:9090`  
Grafana: `http://localhost:3000`

## Project Structure

- **scrapers/** - Web scraping (Scrapy spiders)
- **model/** - ML model (training & predictions)
- **pipeline/** - Data processing (normalize, validate, deduplicate)
- **api/** - REST API endpoints
- **infra/** - Docker, Prometheus, Grafana setup
- **tailscale/** - Network configuration

## Development
See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed setup, testing, and execution guides.
