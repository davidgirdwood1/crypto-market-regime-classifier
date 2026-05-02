# Crypto Market Regime Classifier

A full-stack portfolio project that fetches real crypto market data, trains an explainable baseline classifier, and visualizes market regimes for BTC, ETH, SOL, LINK, and DOGE.

The app turns daily OHLCV data into rolling features such as returns, volatility, moving-average ratios, drawdown from recent highs, and volume trend. A rule-based labeling step creates five market regimes, then a scikit-learn classifier learns those regimes and writes daily predictions back to PostgreSQL for the FastAPI and React dashboard.

## Screenshots

Main dashboard view:

![Main dashboard screenshot](docs/screenshots/main-view.png)

Regime changes table:

![Regime changes table screenshot](docs/screenshots/table-view.png)

## What It Shows

- Current predicted regime for each supported coin
- Classifier confidence for the selected regime
- Latest momentum, drawdown, volatility, and moving-average context
- A regime timeline across real historical market data
- A table of regime-change dates, estimated price, confidence, and key features
- A short rule-based explanation for the latest prediction

## Stack

- Frontend: React + Vite
- Backend: FastAPI
- Database: PostgreSQL
- ML: Python, pandas, scikit-learn
- Data sources: Coinbase Exchange public candles, with optional Coinranking fallback

## How The Pipeline Works

```text
Coinbase daily candles
  -> CSV files in data/raw
  -> PostgreSQL ohlcv_prices table
  -> pandas feature engineering
  -> rule-based regime labels
  -> RandomForestClassifier training
  -> regime_predictions table
  -> FastAPI endpoints
  -> React dashboard
```

Coinbase Exchange is the primary source because its public candle endpoint returns daily OHLCV data without requiring an API key. Coinranking can be used as a fallback if you provide `COINRANKING_API_KEY`, but its price-history endpoint returns prices rather than full OHLCV candles, so fallback rows use that price for open, high, low, and close with `volume=0`.

## Project Structure

```text
backend/              FastAPI app and DB access
frontend/             React dashboard
ml/                   data fetching, ingestion, feature engineering, labels, training
db/schema.sql         PostgreSQL schema
data/raw/             local generated CSVs, ignored by git
artifacts/            local trained model outputs, ignored by git
documentation.md      detailed project notes and run order
docker-compose.yml    optional local PostgreSQL
```

## Local Setup

1. Create environment files:

```bash
cp .env.example .env
cd frontend
cp .env.example .env
cd ..
```

2. Start PostgreSQL:

```bash
docker compose up -d postgres
```

3. Create a Python virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

4. Initialize the database:

```bash
psql "$DATABASE_URL" -f db/schema.sql
```

If `psql` is not on your PATH, run the schema through Docker:

```bash
docker compose exec -T postgres psql -U crypto -d crypto_regime < db/schema.sql
```

5. Fetch real Coinbase OHLCV CSVs (not needed if CSV files are already present in ./data/raw)

```bash
python -m ml.fetch_data --source coinbase --fallback-source none --days 1000 --force
```

To smoke test one coin first:

```bash
python -m ml.fetch_data --source coinbase --fallback-source none --symbols BTC --days 1000 --force
```

6. Ingest CSV data into PostgreSQL:

```bash
python -m ml.ingest --data-dir data/raw
```

7. Train the model and write predictions:

```bash
python -m ml.train --write-db
```

8. Run the API:

```bash
uvicorn backend.app.main:app --reload --port 8000
```

9. Run the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in your terminal, usually `http://localhost:5173`.

## Resetting Local Data

If you want a clean refresh after replacing CSVs, truncate generated DB tables and rerun ingest/train:

```sql
TRUNCATE regime_predictions, model_runs, ohlcv_prices RESTART IDENTITY;
```

```bash
python -m ml.ingest --data-dir data/raw
python -m ml.train --write-db
```

## API Endpoints

- `GET /health`
- `GET /api/coins`
- `GET /api/regime/{symbol}/latest`
- `GET /api/regime/{symbol}/history`
- `GET /api/regime/{symbol}/explain`

## Future Improvements

- Use Tailwind CSS and scope component styling
- Update the look and feel of the graph
- Add support to type in any coin to classifier
- Support more fetch protocols from market data providers
- Add scheduled refresh jobs for prices and predictions
- Add richer model evaluation and walk-forward validation
- Host the site live on AWS or Vercel 

## More Detailed Documentation

See [documentation.md](./docs/documentation.md) for a deeper file-by-file walkthrough and detailed local demo notes.
