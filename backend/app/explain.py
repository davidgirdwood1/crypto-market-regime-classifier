from typing import Any


def explain_regime(regime: str, features: dict[str, Any]) -> tuple[str, list[str]]:
    drivers = []

    return_30d = float(features.get("return_30d", 0))
    return_90d = float(features.get("return_90d", 0))
    drawdown = float(features.get("drawdown_recent_high", 0))
    ma_200_ratio = float(features.get("ma_200_ratio", 0))
    volatility = float(features.get("rolling_volatility", 0))
    volume_trend = float(features.get("volume_trend", 0))

    if return_30d > 0.08:
        drivers.append(f"30-day return is positive at {return_30d:.1%}.")
    elif return_30d < -0.08:
        drivers.append(f"30-day return is weak at {return_30d:.1%}.")

    if return_90d > 0.15:
        drivers.append(f"90-day momentum is strong at {return_90d:.1%}.")
    elif return_90d < -0.15:
        drivers.append(f"90-day momentum is negative at {return_90d:.1%}.")

    if ma_200_ratio > 0:
        drivers.append(f"Price is {ma_200_ratio:.1%} above its 200-day moving average.")
    else:
        drivers.append(f"Price is {abs(ma_200_ratio):.1%} below its 200-day moving average.")

    if drawdown < -0.20:
        drivers.append(f"Recent drawdown is elevated at {drawdown:.1%}.")

    if volatility > 0.06:
        drivers.append(f"Rolling volatility is high at {volatility:.1%}.")

    if abs(volume_trend) > 0.15:
        direction = "rising" if volume_trend > 0 else "falling"
        drivers.append(f"Volume trend is {direction} at {volume_trend:.1%}.")

    if not drivers:
        drivers.append("Feature values are close to neutral thresholds.")

    explanation = f"The model classifies the latest observation as {regime} based on momentum, trend, drawdown, volatility, and volume features."
    return explanation, drivers
