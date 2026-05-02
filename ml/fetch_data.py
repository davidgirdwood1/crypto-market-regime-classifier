import argparse
import csv
import json
import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv

from ml.constants import COINBASE_PRODUCTS, COINRANKING_UUIDS, COINS

COINBASE_BASE_URL = "https://api.exchange.coinbase.com"
COINRANKING_BASE_URL = "https://api.coinranking.com/v2"
COINBASE_LIMIT = 300
DAILY_GRANULARITY_SECONDS = 86400
CHROME_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def fetch_json(url: str, headers: dict[str, str] | None = None):
    request_headers = {
        "Accept": "application/json",
        "User-Agent": CHROME_USER_AGENT,
    }
    if headers:
        request_headers.update(headers)

    request = Request(url, headers=request_headers)
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_coinbase_daily_candles(product_id: str, days: int) -> list[dict[str, str]]:
    end = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=days)
    cursor = start
    rows_by_date = {}

    while cursor < end:
        chunk_end = min(cursor + timedelta(days=COINBASE_LIMIT), end)
        params = {
            "start": cursor.isoformat().replace("+00:00", "Z"),
            "end": chunk_end.isoformat().replace("+00:00", "Z"),
            "granularity": DAILY_GRANULARITY_SECONDS,
        }
        url = f"{COINBASE_BASE_URL}/products/{product_id}/candles?{urlencode(params)}"
        payload = fetch_json(url)

        for item in payload:
            timestamp, low, high, open_, close, volume = item[:6]
            date = datetime.fromtimestamp(timestamp, UTC).date().isoformat()
            rows_by_date[date] = {
                "date": date,
                "open": str(open_),
                "high": str(high),
                "low": str(low),
                "close": str(close),
                "volume": str(volume),
            }

        cursor = chunk_end
        time.sleep(0.25)

    return [rows_by_date[date] for date in sorted(rows_by_date)]


def coinranking_time_period(days: int) -> str:
    if days <= 7:
        return "7d"
    if days <= 30:
        return "30d"
    if days <= 90:
        return "3m"
    return "1y"


def fetch_coinranking_daily_prices(uuid: str, days: int) -> list[dict[str, str]]:
    token = os.getenv("COINRANKING_API_KEY") or os.getenv("COINRANKING_ACCESS_TOKEN")
    if not token or token == "replace_me":
        raise RuntimeError(
            "Coinranking fallback requires COINRANKING_API_KEY in .env "
            "or COINRANKING_ACCESS_TOKEN in your environment."
        )

    params = {"timePeriod": coinranking_time_period(days)}
    url = f"{COINRANKING_BASE_URL}/coin/{uuid}/price-history?{urlencode(params)}"
    payload = fetch_json(url, headers={"x-access-token": token})
    if payload.get("status") != "success":
        raise RuntimeError(f"Coinranking returned an unsuccessful response: {payload}")

    start_date = (datetime.now(UTC) - timedelta(days=days)).date()
    rows_by_date = {}
    for item in payload.get("data", {}).get("history", []):
        price = item.get("price")
        timestamp = item.get("timestamp")
        if price is None or timestamp is None:
            continue

        date = datetime.fromtimestamp(timestamp, UTC).date()
        if date < start_date:
            continue

        rows_by_date[date.isoformat()] = {
            "date": date.isoformat(),
            "open": str(price),
            "high": str(price),
            "low": str(price),
            "close": str(price),
            "volume": "0",
        }

    return [rows_by_date[date] for date in sorted(rows_by_date)]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["date", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        writer.writerows(rows)


def fetch_symbol(symbol: str, source: str, days: int, fallback_source: str | None) -> tuple[str, list[dict[str, str]]]:
    try:
        if source == "coinbase":
            return "coinbase", fetch_coinbase_daily_candles(COINBASE_PRODUCTS[symbol], days)
        if source == "coinranking":
            return "coinranking", fetch_coinranking_daily_prices(COINRANKING_UUIDS[symbol], days)
    except (HTTPError, URLError, RuntimeError) as error:
        if fallback_source and fallback_source != source:
            print(f"{source} fetch failed for {symbol}: {error}. Falling back to {fallback_source}.")
            return fetch_symbol(symbol, fallback_source, days, None)
        raise

    raise ValueError(f"Unsupported source: {source}")


def parse_symbols(symbols: str | None) -> list[str]:
    if not symbols:
        return list(COINS)

    parsed = [symbol.strip().upper() for symbol in symbols.split(",") if symbol.strip()]
    unknown_symbols = sorted(set(parsed) - set(COINS))
    if unknown_symbols:
        raise ValueError(f"Unsupported symbols: {', '.join(unknown_symbols)}")

    return parsed


def fetch_missing_files(
    data_dir: Path,
    source: str,
    days: int,
    force: bool,
    fallback_source: str | None,
    symbols: list[str],
) -> None:
    for symbol in symbols:
        path = data_dir / f"{symbol}.csv"
        if path.exists() and not force:
            print(f"Skipping {path}; file already exists. Use --force to replace it.")
            continue

        print(f"Fetching {symbol} from {source}")
        used_source, rows = fetch_symbol(symbol, source, days, fallback_source)
        if not rows:
            raise RuntimeError(f"{used_source} returned no rows for {symbol}")

        write_csv(path, rows)
        print(f"Wrote {len(rows)} {used_source} rows to {path}")
        time.sleep(0.25)


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Fetch real OHLCV CSVs for the MVP.")
    parser.add_argument("--source", choices=["coinbase", "coinranking"], default="coinbase")
    parser.add_argument("--fallback-source", choices=["coinranking", "none"], default="coinranking")
    parser.add_argument("--data-dir", default="data/raw")
    parser.add_argument("--days", type=int, default=1000)
    parser.add_argument("--symbols", help="Comma-separated symbols to fetch, e.g. BTC or BTC,ETH.")
    parser.add_argument("--force", action="store_true", help="Replace existing CSVs instead of skipping them.")
    args = parser.parse_args()

    if args.days < 250:
        raise ValueError("Use at least 250 days so 200-day moving average features can be computed.")

    fallback_source = None if args.fallback_source == "none" else args.fallback_source
    fetch_missing_files(
        Path(args.data_dir),
        args.source,
        args.days,
        args.force,
        fallback_source,
        parse_symbols(args.symbols),
    )


if __name__ == "__main__":
    main()
