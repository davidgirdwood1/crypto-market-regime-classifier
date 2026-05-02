import pandas as pd


def label_regime(row: pd.Series) -> str:
    momentum = (row["return_30d"] * 0.45) + (row["return_90d"] * 0.35) + (row["ma_200_ratio"] * 0.20)
    drawdown = row["drawdown_recent_high"]
    volatility = row["rolling_volatility"]

    if momentum <= -0.25 or drawdown <= -0.45:
        return "Raging Bear"
    if momentum <= -0.08 or drawdown <= -0.25:
        return "Bearish"
    if momentum >= 0.30 and drawdown > -0.12 and volatility < 0.08:
        return "Raging Bull"
    if momentum >= 0.08 and drawdown > -0.20:
        return "Bullish"
    return "Sideways"


def add_labels(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data["regime"] = data.apply(label_regime, axis=1)
    return data
