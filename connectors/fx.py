"""Currency conversion to Moroccan dirham (MAD) from a free, keyless public source.

Rates come from https://open.er-api.com/v6/latest/<BASE>. ``MARKET_SPY_FX_OVERRIDE``
(e.g. ``USD:MAD=10.05``) pins a rate for offline runs. The rate, its source and
timestamp are always returned so reports never show an unexplained number.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Callable

FX_URL = "https://open.er-api.com/v6/latest/{base}"


@dataclass(frozen=True)
class Rate:
    base: str
    quote: str
    value: float
    source_url: str
    as_of: str


def _override(base: str, quote: str) -> Rate | None:
    raw = os.getenv("MARKET_SPY_FX_OVERRIDE", "")
    for part in raw.split(","):
        if "=" not in part:
            continue
        pair, value = part.split("=", 1)
        if pair.strip().upper() == f"{base}:{quote}":
            return Rate(base, quote, float(value), "env:MARKET_SPY_FX_OVERRIDE", "manual")
    return None


def get_rate(base: str, quote: str, get_bytes: Callable[[str, str], bytes]) -> Rate:
    base, quote = base.upper(), quote.upper()
    if base == quote:
        return Rate(base, quote, 1.0, "identity", "n/a")
    pinned = _override(base, quote)
    if pinned:
        return pinned
    url = FX_URL.format(base=base)
    payload = json.loads(get_bytes(url, f"fx-{base.lower()}"))
    if payload.get("result") != "success" or quote not in payload.get("rates", {}):
        raise ValueError(f"no {base}->{quote} rate from {url}")
    return Rate(base, quote, float(payload["rates"][quote]), url, str(payload.get("time_last_update_utc", "")))


def convert(amount: float | None, rate: Rate) -> float | None:
    return None if amount is None else round(amount * rate.value, 2)
