# Development Guide

Status: Work in Progress (WIP)

This repository is currently under development. The scraper foundatio is in place, but the data pipeline, model training, and prediction workflows are still being completed.

Complete setup, testing, and execution reference for all project components.

## Table of Contents
1. [Environment Setup](#environment-setup)
2. [Component Execution](#component-execution)
3. [Testing](#testing)
4. [Troubleshooting](#troubleshooting)

---

## Environment Setup

### Initial Setup Steps

1. **Clone and navigate to project:**
```bash
cd "Tunisian Car Market Valuation Engine"
```

2. **Create virtual environment:**
```bash
python -m venv .env
```

3. **Activate virtual environment:**
```powershell
# Windows PowerShell
.env\Scripts\Activate.ps1

# Command Prompt
.env\Scripts\activate.bat

# Bash/Git Bash
source .env/Scripts/activate
```

4. **Install dependencies:**
```bash
pip install -r requirements.txt
```

### Verify Setup
```bash
python -c "import scrapy; import pandas; print('Setup OK')"
```

---

## Component Execution

### 1. Scrapers (Scrapy Web Scraping)

**Source:** `scrapers/` directory  
**Main Spider:** `automobile_tn_spider.py` (scrapes automobile.tn)

**Run scraper:**
```bash
# Crawl automobile.tn website
scrapy crawl "Automobile TN"

# Additional options:
scrapy crawl "Automobile TN" -a max_pages=50
scrapy crawl "Automobile TN" -o output.json
```

**Configuration:**
- Settings: `scrapers/common/settings.py`
  - Bot name: "TuniCar"
  - Concurrency: 4 requests
  - Download delay: 3 seconds
  - Auto-throttling enabled

**Spider Modules:**
- Normalizers: `scrapers/common/normalizers.py` (fuel, gearbox, price, mileage)
- Pipelines: `scrapers/common/pipelines.py` (data processing)
- Schema: `scrapers/common/schema.py` (data models)

---

### 2. Data Pipeline

**Location:** `pipeline/` directory

**Step 1: Normalize**
```bash
python pipeline/normalize.py
```
- Normalizes text, prices, mileage, fuel type, gearbox, region

**Step 2: Validate**
```bash
python pipeline/validate.py
```
- Validates data integrity and constraints

**Step 3: Deduplicate**
```bash
python pipeline/deduplicate.py
```
- Removes duplicate entries

**Full Pipeline (DVC):**
```bash
dvc repro pipeline/dvc.yaml
```

---

### 3. ML Model

**Location:** `model/` directory

**Training:**
```bash
python model/train.py
```
- Trains valuation model on processed data
- Logs metrics to MLflow (`model/mlflow_tracking/`)

**Prediction:**
```bash
python model/predict.py
```
- Generates price predictions for new listings

**MLflow Tracking:**
```bash
mlflow ui --backend-store-uri sqlite:///model/mlflow_tracking/mlflow.db
```

---

### 4. Infrastructure

**Location:** `infra/` directory

**Docker Services:**
```bash
# Start all services
docker-compose -f infra/docker-compose.yml up -d

# Stop services
docker-compose -f infra/docker-compose.yml down

# View logs
docker-compose -f infra/docker-compose.yml logs -f
```

**Services:**
- **Prometheus** (Metrics collection)
  - URL: `http://localhost:9090`
  - Config: `infra/prometheus/`

- **Grafana** (Visualization)
  - URL: `http://localhost:3000`
  - Config: `infra/graphana/`

- **Webhook Receiver** (Event handling)
  - Config: `infra/webhook-receiver/`

---

### 5. API

**Location:** `api/` directory

*Status: Currently in development*

```bash
python api/main.py
```

---

## Testing

### Run Scraper Tests
```bash
# Run all scraper tests
pytest scrapers/tests/

# Run specific test file
pytest scrapers/tests/test_step1_scrappers.py

# Run with verbose output
pytest scrapers/tests/ -v

# Run with coverage
pytest scrapers/tests/ --cov=scrapers
```

**Test Location:** `scrapers/tests/test_step1_scrappers.py`  
**Tests:** Regex patterns for price negotiability detection

### Run Model Tests (when available)
```bash
pytest model/tests/ -v
```

### Run Pipeline Tests (when available)
```bash
pytest pipeline/tests/ -v
```

---

## Development Workflow

### Daily Workflow

1. **Activate environment:**
```powershell
.env\Scripts\Activate.ps1
```

2. **Run scraper (data collection):**
```bash
scrapy crawl "Automobile TN"
```

3. **Process data (pipeline):**
```bash
python pipeline/normalize.py
python pipeline/validate.py
python pipeline/deduplicate.py
```

4. **Train/evaluate model:**
```bash
python model/train.py
python model/predict.py
```

5. **Run tests:**
```bash
pytest scrapers/tests/ -v
```

### Before Committing

```bash
# Run all tests
pytest

# Check code quality (if pre-commit hooks configured)
pre-commit run --all-files
```

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `scrapers/spiders/automobile_tn_spider.py` | Main web scraper |
| `scrapers/common/settings.py` | Scrapy configuration |
| `scrapers/common/normalizers.py` | Data normalization functions |
| `scrapers/common/schema.py` | Data models & enums |
| `pipeline/normalize.py` | Text normalization pipeline |
| `pipeline/validate.py` | Data validation |
| `pipeline/deduplicate.py` | Duplicate removal |
| `pipeline/dvc.yaml` | DVC pipeline stages |
| `model/train.py` | Model training script |
| `model/predict.py` | Prediction script |
| `infra/docker-compose.yml` | Container orchestration |
| `scrapy.cfg` | Scrapy project config |

---

## Troubleshooting

### Virtual Environment Issues
```bash
# Recreate venv if corrupted
rmdir .env /s /q
python -m venv .env
.env\Scripts\activate
pip install -r requirements.txt
```

### Scrapy Issues
```bash
# Check spider availability
scrapy list

# Validate spider code
scrapy check

# Debug single URL
scrapy shell "https://www.automobile.tn/fr/occasion"
```

### Docker Issues
```bash
# Rebuild containers
docker-compose -f infra/docker-compose.yml up --build

# Clean volumes
docker-compose -f infra/docker-compose.yml down -v
```

### Port Already in Use
```bash
# Windows: Find and kill process on port
netstat -ano | findstr :9090
taskkill /PID <PID> /F

# Docker alternative:
docker-compose -f infra/docker-compose.yml down
```

---

## Environment Variables (.env)

Create `.env` file in project root with:

```
# Example configuration
PYTHONUNBUFFERED=1
SCRAPY_BOT_NAME=TuniCar

# Add credentials as needed
```

---

## Notes

- Project uses virtual environment in `.env/` directory
- Data is scraped from `https://www.automobile.tn`
- Model tracking via MLflow
- Infrastructure managed with Docker Compose
- Roadmap: Complete API implementation, expand model evaluation
