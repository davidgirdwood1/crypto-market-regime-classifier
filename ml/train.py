import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sqlalchemy import text

from ml.constants import FEATURE_COLUMNS
from ml.db import get_engine
from ml.features import compute_features
from ml.labels import add_labels


def load_prices_from_db() -> pd.DataFrame:
    query = """
        SELECT symbol, price_date AS date, open, high, low, close, volume
        FROM ohlcv_prices
        ORDER BY symbol, price_date
    """
    return pd.read_sql(query, get_engine())


def build_training_frame(prices: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for symbol, group in prices.groupby("symbol"):
        featured = compute_features(group.drop(columns=["symbol"]))
        featured["symbol"] = symbol
        frames.append(add_labels(featured))

    if not frames:
        raise ValueError("No training data found. Ingest CSVs first.")

    return pd.concat(frames, ignore_index=True)


def save_predictions(training_df: pd.DataFrame, model, model_run_id: int) -> None:
    probabilities = model.predict_proba(training_df[FEATURE_COLUMNS])
    classes = list(model.classes_)
    predictions = model.predict(training_df[FEATURE_COLUMNS])

    rows = []
    for idx, row in training_df.reset_index(drop=True).iterrows():
        confidence = float(max(probabilities[idx]))
        features = {col: float(row[col]) for col in FEATURE_COLUMNS}
        rows.append(
            {
                "symbol": row["symbol"],
                "price_date": row["date"],
                "regime": predictions[idx],
                "confidence": confidence,
                "model_run_id": model_run_id,
                "features": json.dumps(features),
            }
        )

    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO regime_predictions(symbol, price_date, regime, confidence, model_run_id, features)
                VALUES (:symbol, :price_date, :regime, :confidence, :model_run_id, CAST(:features AS jsonb))
                ON CONFLICT (symbol, price_date) DO UPDATE SET
                    regime = EXCLUDED.regime,
                    confidence = EXCLUDED.confidence,
                    model_run_id = EXCLUDED.model_run_id,
                    features = EXCLUDED.features,
                    created_at = NOW()
                """
            ),
            rows,
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-db", action="store_true")
    args = parser.parse_args()

    prices = load_prices_from_db()
    training_df = build_training_frame(prices)
    x = training_df[FEATURE_COLUMNS]
    y = training_df["regime"]

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y,
    )

    model = RandomForestClassifier(
        n_estimators=250,
        random_state=42,
        class_weight="balanced",
        min_samples_leaf=3,
    )
    model.fit(x_train, y_train)

    y_pred = model.predict(x_test)
    accuracy = accuracy_score(y_test, y_pred)
    macro_f1 = f1_score(y_test, y_pred, average="macro")

    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(exist_ok=True)
    joblib.dump(model, artifacts_dir / "regime_classifier.joblib")
    (artifacts_dir / "training_metrics.json").write_text(
        json.dumps({"accuracy": accuracy, "macro_f1": macro_f1}, indent=2),
        encoding="utf-8",
    )

    model_run_id = None
    if args.write_db:
        with get_engine().begin() as conn:
            result = conn.execute(
                text(
                    """
                    INSERT INTO model_runs(model_name, accuracy, macro_f1, metadata)
                    VALUES (:model_name, :accuracy, :macro_f1, CAST(:metadata AS jsonb))
                    RETURNING id
                    """
                ),
                {
                    "model_name": "RandomForestClassifier",
                    "accuracy": float(accuracy),
                    "macro_f1": float(macro_f1),
                    "metadata": json.dumps({"features": FEATURE_COLUMNS}),
                },
            )
            model_run_id = result.scalar_one()
        save_predictions(training_df, model, model_run_id)

    print(f"Accuracy: {accuracy:.3f}")
    print(f"Macro F1: {macro_f1:.3f}")
    if model_run_id:
        print(f"Saved predictions for model_run_id={model_run_id}")


if __name__ == "__main__":
    main()
