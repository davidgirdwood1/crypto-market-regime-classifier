import pandas as pd

from ml.constants import FEATURE_COLUMNS


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data.columns = [str(col).strip().lower() for col in data.columns]

    required = {"date", "open", "high", "low", "close"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {sorted(missing)}")

    if "volume" not in data.columns:
        data["volume"] = 0

    data["date"] = pd.to_datetime(data["date"]).dt.date
    numeric_cols = ["open", "high", "low", "close", "volume"]
    for col in numeric_cols:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    return data.dropna(subset=["date", "open", "high", "low", "close"]).sort_values("date")


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    data = normalize_ohlcv(df)
    data["close"] = data["close"].astype(float)
    data["volume"] = data["volume"].fillna(0).astype(float)

    data["return_7d"] = data["close"].pct_change(7)
    data["return_30d"] = data["close"].pct_change(30)
    data["return_90d"] = data["close"].pct_change(90)
    data["rolling_volatility"] = data["close"].pct_change().rolling(30).std()
    data["ma_50"] = data["close"].rolling(50).mean()
    data["ma_200"] = data["close"].rolling(200).mean()
    data["ma_50_ratio"] = data["close"] / data["ma_50"] - 1
    data["ma_200_ratio"] = data["close"] / data["ma_200"] - 1
    recent_high = data["close"].rolling(90).max()
    data["drawdown_recent_high"] = data["close"] / recent_high - 1

    volume_ma_30 = data["volume"].rolling(30).mean()
    volume_ma_90 = data["volume"].rolling(90).mean()
    data["volume_trend"] = volume_ma_30 / volume_ma_90 - 1
    data.loc[data["volume"].eq(0), "volume_trend"] = 0

    return data.dropna(subset=FEATURE_COLUMNS).reset_index(drop=True)
