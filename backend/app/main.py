from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.explain import explain_regime
from backend.app.schemas import Coin, RegimeExplanation, RegimePrediction

app = FastAPI(title="Crypto Market Regime Classifier")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/coins", response_model=list[Coin])
def get_coins(db: Session = Depends(get_db)) -> list[Coin]:
    rows = db.execute(text("SELECT symbol, name FROM coins ORDER BY symbol")).mappings().all()
    return [Coin(symbol=row["symbol"], name=row["name"]) for row in rows]


def fetch_predictions(db: Session, symbol: str, limit: int | None = None) -> list[RegimePrediction]:
    sql = """
        SELECT
            rp.symbol,
            rp.price_date AS date,
            rp.regime,
            rp.confidence,
            rp.features,
            ((op.low + op.high) / 2.0) AS price
        FROM regime_predictions rp
        LEFT JOIN ohlcv_prices op
            ON op.symbol = rp.symbol
            AND op.price_date = rp.price_date
        WHERE rp.symbol = :symbol
        ORDER BY rp.price_date DESC
    """
    params = {"symbol": symbol.upper()}
    if limit:
        sql += " LIMIT :limit"
        params["limit"] = limit

    rows = db.execute(text(sql), params).mappings().all()
    return [
        RegimePrediction(
            symbol=row["symbol"],
            date=row["date"],
            regime=row["regime"],
            confidence=float(row["confidence"]),
            price=float(row["price"]) if row["price"] is not None else None,
            features=dict(row["features"]),
        )
        for row in rows
    ]


@app.get("/api/regime/{symbol}/latest", response_model=RegimePrediction)
def get_latest_regime(symbol: str, db: Session = Depends(get_db)) -> RegimePrediction:
    predictions = fetch_predictions(db, symbol, limit=1)
    if not predictions:
        raise HTTPException(status_code=404, detail=f"No predictions found for {symbol.upper()}")
    return predictions[0]


@app.get("/api/regime/{symbol}/history", response_model=list[RegimePrediction])
def get_regime_history(symbol: str, limit: int = 365, db: Session = Depends(get_db)) -> list[RegimePrediction]:
    return list(reversed(fetch_predictions(db, symbol, limit=limit)))


@app.get("/api/regime/{symbol}/explain", response_model=RegimeExplanation)
def get_regime_explanation(symbol: str, db: Session = Depends(get_db)) -> RegimeExplanation:
    latest = get_latest_regime(symbol, db)
    explanation, drivers = explain_regime(latest.regime, latest.features)
    return RegimeExplanation(
        symbol=latest.symbol,
        date=latest.date,
        regime=latest.regime,
        confidence=latest.confidence,
        explanation=explanation,
        drivers=drivers,
    )
