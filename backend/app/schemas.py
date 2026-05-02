from datetime import date
from typing import Any

from pydantic import BaseModel


class Coin(BaseModel):
    symbol: str
    name: str


class RegimePrediction(BaseModel):
    symbol: str
    date: date
    regime: str
    confidence: float
    price: float | None = None
    features: dict[str, Any]


class RegimeExplanation(BaseModel):
    symbol: str
    date: date
    regime: str
    confidence: float
    explanation: str
    drivers: list[str]
