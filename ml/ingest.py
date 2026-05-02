import argparse
from pathlib import Path

from sqlalchemy import text

from ml.constants import COINS
from ml.db import get_engine
from ml.features import normalize_ohlcv


def ingest_file(path: Path, symbol: str) -> int:
    df = normalize_ohlcv(__import__("pandas").read_csv(path))
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO coins(symbol, name)
                VALUES (:symbol, :name)
                ON CONFLICT (symbol) DO UPDATE SET name = EXCLUDED.name
                """
            ),
            {"symbol": symbol, "name": COINS.get(symbol, symbol)},
        )

        rows = [
            {
                "symbol": symbol,
                "price_date": row.date,
                "open": float(row.open),
                "high": float(row.high),
                "low": float(row.low),
                "close": float(row.close),
                "volume": float(row.volume or 0),
            }
            for row in df.itertuples(index=False)
        ]

        conn.execute(
            text(
                """
                INSERT INTO ohlcv_prices(symbol, price_date, open, high, low, close, volume)
                VALUES (:symbol, :price_date, :open, :high, :low, :close, :volume)
                ON CONFLICT (symbol, price_date) DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume
                """
            ),
            rows,
        )

    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/raw")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    total = 0
    for path in sorted(data_dir.glob("*.csv")):
        symbol = path.stem.upper()
        total += ingest_file(path, symbol)
        print(f"Ingested {path}")

    print(f"Ingested {total} OHLCV rows")


if __name__ == "__main__":
    main()
