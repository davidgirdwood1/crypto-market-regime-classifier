# Crypto Market Regime Classifier Documentation

This document provides a deeper walkthrough of the project architecture, data pipeline, machine-learning workflow, API layer, frontend dashboard, and local demo path.

## Files Created

### Root

`README.md`

High-level project overview and setup guide. It explains the tech stack, folder structure, CSV format, API endpoints, and local run commands.

`requirements.txt`

Python dependencies for the backend and ML pipeline:

- FastAPI and Uvicorn for the API
- SQLAlchemy and psycopg for PostgreSQL access
- pandas, numpy, scikit-learn, and joblib for data processing and model training
- pydantic-settings and python-dotenv for environment configuration

`docker-compose.yml`

If you already have PostgreSQL installed locally, you can skip Docker and create the database manually with a tool such as DBeaver or psql.

`.env.example`

Example environment variables. The important value for the MVP is:

```text
DATABASE_URL=postgresql+psycopg://<POSTGRES_USER>:<POSTGRES_PASSWORD>@localhost:5433/<POSTGRES_DB>
```

Update your real `.env` to match your local PostgreSQL username, password, host, port, and database name.

`.gitignore`

Updated to ignore generated artifacts, raw CSV data, processed CSV data, Python environments, build outputs, and local secrets.

### Database

`db/schema.sql`

PostgreSQL schema for the MVP.

Tables:

- `coins`: supported crypto assets
- `ohlcv_prices`: historical OHLCV rows
- `model_runs`: metadata and metrics for each training run
- `regime_predictions`: model predictions by symbol and date

It also seeds the five supported coins:

- BTC
- ETH
- SOL
- LINK
- DOGE

### Data Folders

`data/raw/.gitkeep`

Keeps the raw data folder in git. This folder is where static CSV files go, such as `BTC.csv`, `ETH.csv`, `SOL.csv`, `LINK.csv`, and `DOGE.csv`.

`data/processed/.gitkeep`

Keeps a future processed-data folder in git. The current MVP does not require this folder yet.

### Artifacts

`artifacts/.gitkeep`

Keeps the model artifact folder in git. Training writes generated model outputs here, but those generated files are ignored by git.

Expected generated files:

- `artifacts/regime_classifier.joblib`
- `artifacts/training_metrics.json`

### Machine Learning Pipeline

`ml/__init__.py`

Marks `ml` as a Python package so scripts can be run with `py -3 -m ml.<script_name>` or `python -m ml.<script_name>`.

`ml/constants.py`

Shared constants:

- supported coins
- five regime names
- feature column names used by training and prediction

`ml/settings.py`

Loads ML pipeline settings from `.env`, mainly `DATABASE_URL`.

`ml/db.py`

Creates a SQLAlchemy database engine for ML scripts.

`ml/features.py`

Normalizes OHLCV CSV data and computes model features:

- 7-day return
- 30-day return
- 90-day return
- rolling volatility
- 50-day moving average
- 200-day moving average
- price ratio to 50-day moving average
- price ratio to 200-day moving average
- drawdown from recent high
- volume trend

`ml/labels.py`

Creates rule-based labels for the five regimes. This gives the MVP a simple explainable target before moving to more advanced labeling or unsupervised approaches.

`ml/generate_sample_data.py`

Generates synthetic OHLCV CSV files for BTC, ETH, SOL, LINK, and DOGE in `data/raw`.

This is included so the first demo can run without downloading Kaggle data or calling an external API.

`ml/fetch_data.py`

Fetches real daily OHLCV data. Coinbase Exchange is the preferred source, with an automatic Coinranking fallback if Coinbase is unavailable.

Coinbase products:

- BTC-USD
- ETH-USD
- SOL-USD
- LINK-USD
- DOGE-USD

Coinranking UUIDs:

- BTC: Qwsogvtv82FCd
- ETH: razxDUgYGNAdQ
- SOL: zNZHO_Sjf
- LINK: VLqpJwogdhHNb
- DOGE: a91GCGd_u96cF

Coinranking requires `COINRANKING_API_KEY` in `.env`. Its free price-history endpoint returns timestamped prices rather than full OHLCV candles, so fallback rows use the price for open, high, low, and close with `volume=0`.

It writes normalized CSVs to `data/raw` using the same format as the ingestion pipeline:

```text
date,open,high,low,close,volume
```

By default, it skips a symbol if that CSV already exists. Use `--force` to replace existing CSVs.

`ml/ingest.py`

Reads CSV files from `data/raw`, normalizes them, and upserts rows into PostgreSQL:

- inserts or updates coins
- inserts or updates OHLCV price rows

`ml/train.py`

Loads OHLCV data from PostgreSQL, computes features, creates labels, trains a `RandomForestClassifier`, saves model artifacts, creates a model run record, and optionally writes predictions back to PostgreSQL.

Use `--write-db` to populate `regime_predictions`.

### Backend

`backend/__init__.py`

Marks `backend` as a Python package.

`backend/app/__init__.py`

Marks `backend/app` as a Python package.

`backend/app/settings.py`

Loads backend settings from `.env`, mainly `DATABASE_URL`.

`backend/app/database.py`

Creates the backend SQLAlchemy engine and request-scoped database sessions.

`backend/app/schemas.py`

Pydantic response models for:

- coins
- regime predictions
- regime explanations

`backend/app/explain.py`

Creates a simple rules-based natural-language explanation for the latest regime prediction using feature values.

This is the placeholder explanation layer that can later be replaced or enhanced with an NVIDIA-hosted LLM API.

`backend/app/main.py`

FastAPI application.

Endpoints:

- `GET /health`
- `GET /api/coins`
- `GET /api/regime/{symbol}/latest`
- `GET /api/regime/{symbol}/history`
- `GET /api/regime/{symbol}/explain`

### Frontend

`frontend/package.json`

React/Vite frontend package definition.

Dependencies:

- React
- Vite
- Recharts
- lucide-react

`frontend/index.html`

Vite HTML entrypoint.

`frontend/vite.config.js`

Vite configuration for the React app.

`frontend/.env.example`

Frontend API URL example:

```text
VITE_API_BASE_URL=http://localhost:8000
```

`frontend/src/main.jsx`

Main React dashboard.

Includes:

- coin selector
- current regime card
- confidence score
- latest feature summary
- regime timeline chart
- explanation panel
- historical predictions table

`frontend/src/styles.css`

Dashboard styling and responsive layout.

## Intended Run Order

The full run order is:

1. Create `.env` from `.env.example`.
2. Update `DATABASE_URL` to match your local PostgreSQL database.
3. Create the PostgreSQL database if it does not already exist.
4. Run `db/schema.sql` against that database.
5. Create and activate a Python virtual environment.
6. Install Python dependencies from `requirements.txt`.
7. Fetch real Coinbase CSV data, or generate synthetic demo CSV data.
8. Ingest CSV data into PostgreSQL.
9. Train the classifier and write predictions to PostgreSQL.
10. Start the FastAPI backend.
11. Install frontend dependencies.
12. Start the Vite React frontend.
13. Open the dashboard in the browser.

## Smallest Path To A Working Local Demo

If you already have PostgreSQL installed locally, you can skip Docker and create the database manually with a tool such as DBeaver or psql.

### 1. Create A Database

In DBeaver, create a PostgreSQL database named:

```text
crypto_regime
```

You can use another name if you prefer, but then your `DATABASE_URL` and `POSTGRES_DB_B` must match it.

### 2. Create `.env`

From Git Bash at the repo root:

```bash
cp .env.example .env
```

Edit `.env` so `DATABASE_URL` and others matches your local PostgreSQL credentials.

Example:

```text
DATABASE_URL=postgresql+psycopg://<POSTGRES_USER>:<POSTGRES_PASSWORD>@localhost:5433/<POSTGRES_DB>
VITE_API_BASE_URL=http://localhost:8000
COINRANKING_API_KEY=replace_me
```

### 3. Run The Schema

In DBeaver, open `db/schema.sql` and execute it against the `POSTGRES_DB` database.

This creates the tables and inserts the five coin rows.

### 4. Install Python Dependencies

```bash
# Windows Git Bash
source .venv/Scripts/activate

# macOS/Linux
source .venv/bin/activate

python -m pip install -r requirements.txt
```

### 5. Fetch Real Coinbase CSVs

The MVP can use real Coinbase Exchange OHLCV data without an API key. Coinbase is tried first, and Coinranking price history is used as a token-backed fallback if Coinbase is unavailable.

If `data/raw/BTC.csv`, `ETH.csv`, `SOL.csv`, `LINK.csv`, or `DOGE.csv` already exist, this command skips them:

```bash
py -3 -m ml.fetch_data --source coinbase --days 1000
```

To replace existing synthetic CSVs with real Coinbase data:

```bash
py -3 -m ml.fetch_data --source coinbase --days 1000 --force
```

To smoke test one coin first:

```bash
py -3 -m ml.fetch_data --source coinbase --fallback-source none --symbols BTC --days 1000 --force
```

To test Coinranking directly:

```bash
py -3 -m ml.fetch_data --source coinranking --days 365 --force
```

### 5b. Optional Synthetic Demo CSVs

```bash
py -3 -m ml.generate_sample_data
```

This writes:

- `data/raw/BTC.csv`
- `data/raw/ETH.csv`
- `data/raw/SOL.csv`
- `data/raw/LINK.csv`
- `data/raw/DOGE.csv`

### 6. Ingest CSVs Into PostgreSQL

```bash
py -3 -m ml.ingest --data-dir data/raw
```

At this point, DBeaver should show rows in `ohlcv_prices`.

### 7. Train The Model And Save Predictions

```bash
py -3 -m ml.train --write-db
```

At this point, DBeaver should show rows in:

- `model_runs`
- `regime_predictions`

### 8. Start The Backend

```bash
uvicorn backend.app.main:app --reload --port 8000
```

Check:

```text
http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

### 9. Start The Frontend

In a second Git Bash terminal:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Open the Vite URL shown in the terminal, usually:

```text
http://127.0.0.1:5173
```

## Minimal Demo Success Criteria

The smallest demo is working when:

- DBeaver shows OHLCV rows in `ohlcv_prices`.
- DBeaver shows prediction rows in `regime_predictions`.
- `http://localhost:8000/health` returns `{"status":"ok"}`.
- The React dashboard loads coins.
- Selecting BTC, ETH, SOL, LINK, or DOGE shows a current regime, confidence score, timeline chart, table, and explanation.

## Notes

The first demo does not need Kaggle data, Coinranking fallback data, PyTorch, or external LLM explanations.

The fastest useful proof is:

```text
Coinbase CSVs -> PostgreSQL -> trained sklearn model -> predictions table -> FastAPI -> React dashboard
```
