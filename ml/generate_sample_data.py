from pathlib import Path

import numpy as np
import pandas as pd

from ml.constants import COINS


def generate_symbol(symbol: str, days: int = 900) -> pd.DataFrame:
    rng = np.random.default_rng(abs(hash(symbol)) % (2**32))
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=days, freq="D")

    base_prices = {
        "BTC": 28000,
        "ETH": 1800,
        "SOL": 35,
        "LINK": 8,
        "DOGE": 0.08,
    }

    drift = {
        "BTC": 0.0009,
        "ETH": 0.0010,
        "SOL": 0.0013,
        "LINK": 0.0008,
        "DOGE": 0.0011,
    }

    shocks = rng.normal(drift[symbol], 0.035, days)
    cycle = 0.018 * np.sin(np.linspace(0, 18, days))
    returns = shocks + cycle
    close = base_prices[symbol] * np.exp(np.cumsum(returns))
    open_ = close * (1 + rng.normal(0, 0.008, days))
    high = np.maximum(open_, close) * (1 + rng.uniform(0.002, 0.035, days))
    low = np.minimum(open_, close) * (1 - rng.uniform(0.002, 0.035, days))
    volume = rng.lognormal(mean=14, sigma=0.6, size=days)

    return pd.DataFrame(
        {
            "date": dates.date,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }
    )


def main() -> None:
    output_dir = Path("data/raw")
    output_dir.mkdir(parents=True, exist_ok=True)
    for symbol in COINS:
        path = output_dir / f"{symbol}.csv"
        generate_symbol(symbol).to_csv(path, index=False)
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
