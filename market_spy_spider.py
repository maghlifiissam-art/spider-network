"""Market Spy Spider: source-backed market intelligence without commerce side effects.

The module consumes public, permitted feeds, labels every value as an observed metric
or proxy, and never turns missing data into estimated sales.  It has no purchase,
publishing, or account-writing capability.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import math
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import quote

import requests

from connectors import aliexpress_connector as aliexpress
from connectors import fx

USER_AGENT = os.getenv("MARKET_SPY_USER_AGENT", "SpiderNetwork-MarketSpy/1.0 (+public-feed-research)")
TIMEOUT_SECONDS = int(os.getenv("MARKET_SPY_TIMEOUT_SECONDS", "15"))
CACHE_TTL_SECONDS = max(900, int(os.getenv("MARKET_SPY_CACHE_TTL_SECONDS", "3600")))
CACHE_DIR = Path(os.getenv("MARKET_SPY_CACHE_DIR", "data/market_spy_cache"))
MARKET_SPY_CONTRACT_VERSION = "market_spy_handoff.v1"

APPLE_COUNTRIES = {"us", "gb", "fr", "de", "es", "it", "ca", "au", "jp", "ma"}


MARKET_CATEGORY_PROFILES = {
    "digital_product": {
        "label": "Digital products",
        "required_metrics": ["demand_momentum", "geography", "competition", "price", "freshness", "provenance", "confidence", "rights_risk"],
        "criteria": ["download/search demand", "format and platform fit", "price band", "competition", "production effort", "rights/licensing risk"],
    },
    "ebook": {
        "label": "Digital books / ebooks",
        "required_metrics": ["topic_demand", "geography_language", "competition", "price", "freshness", "provenance", "confidence", "rights_risk"],
        "criteria": ["topic and keyword demand", "language/geography fit", "reader intent", "price band", "category competition", "copyright and source risk"],
    },
    "design_asset": {
        "label": "Designs and downloadable creative assets",
        "required_metrics": ["style_demand", "geography", "competition", "price", "freshness", "provenance", "confidence", "rights_risk"],
        "criteria": ["style/use-case demand", "file-format fit", "commercial-license expectations", "price band", "competition", "trademark/copyright risk"],
    },
    "wall_art_decor": {
        "label": "Painted wall art and decor",
        "required_metrics": ["style_demand", "geography", "competition", "price", "freshness", "provenance", "confidence", "fulfillment_risk"],
        "criteria": ["decor style and room-use demand", "print versus original-painting format", "size/material/fulfillment cost", "local price band", "competition", "shipping and rights risk"],
    },
    "sticker": {
        "label": "Stickers",
        "required_metrics": ["use_case_demand", "format_printability", "geography", "competition", "price", "freshness", "provenance", "confidence", "licensing_risk"],
        "criteria": ["use-case demand", "digital/print format", "printability and material fit", "price band", "competition", "licensing/IP risk"],
    },
    "logo": {
        "label": "Logos",
        "required_metrics": ["use_case_demand", "geography", "competition", "price", "freshness", "provenance", "confidence", "originality_review", "similarity_review", "trademark_ip_risk"],
        "criteria": ["business/use-case demand", "originality review", "similarity search", "price band", "competition", "trademark/IP risk"],
    },
    "children_coloring_book": {
        "label": "Children coloring books",
        "required_metrics": ["theme_demand", "age_band", "geography_language", "format_printability", "print_economics", "competition", "price", "freshness", "provenance", "confidence", "child_safety", "illustration_rights_risk"],
        "criteria": ["age band", "theme demand", "language/geography", "print format", "print economics", "competition", "child safety", "illustration rights"],
    },
    "illustrated_story": {
        "label": "Illustrated stories",
        "required_metrics": ["audience_demand", "age_band", "geography_language", "format_printability", "competition", "price", "freshness", "provenance", "confidence", "illustration_rights_risk", "user_supplied_topic", "user_supplied_message"],
        "criteria": ["demand", "age band", "language/geography", "format", "price", "competition", "illustration rights", "user-supplied story topic and message"],
    },
    "physical_product": {
        "label": "Physical products",
        "required_metrics": ["demand_momentum", "geography", "competition", "price", "freshness", "provenance", "confidence", "fulfillment_risk"],
        "criteria": ["demand momentum", "local availability", "landed price", "competition", "margin inputs", "fulfillment/returns risk"],
    },
}


def classify_market_category(query: str, requested: str | None = None) -> str:
    if requested in MARKET_CATEGORY_PROFILES:
        return requested
    text = query.casefold()
    rules = (
        ("illustrated_story", ("illustrated story", "illustrated stories", "قصة مصورة", "قصص مصورة", "القصص المرسومة")),
        ("children_coloring_book", ("coloring book", "colouring book", "كتاب تلوين", "كتب التلوين")),
        ("sticker", ("sticker", "stickers", "ملصق", "ملصقات")),
        ("logo", ("logo", "logos", "شعار", "شعارات")),
        ("wall_art_decor", ("wall art", "painting", "painted", "tableau", "تابلو", "لوحة", "ديكور", "decor")),
        ("ebook", ("ebook", "e-book", "digital book", "كتاب رقمي", "كتب رقمية")),
        ("digital_product", ("digital product", "download", "منتج رقمي", "منتجات رقمية")),
        ("design_asset", ("design", "template", "svg", "printable", "تصميم", "قالب")),
    )
    for category, words in rules:
        if any(word in text for word in words):
            return category
    return "physical_product"


class SourceUnavailable(RuntimeError):
    """A source refused, throttled, challenged, or failed the request."""


@dataclasses.dataclass(frozen=True)
class Signal:
    product: str
    source_name: str
    source_url: str
    observed_at: str
    geography: str
    metric: str
    value: float | None
    unit: str
    is_proxy: bool
    confidence: float
    category: str = ""
    price: float | None = None
    currency: str | None = None
    first_released_at: str | None = None
    limitations: tuple[str, ...] = ()
    commission_rate: float | None = None
    risk_score: float | None = None
    rank_position: int | None = None
    rating_percent: float | None = None
    original_price: float | None = None
    price_mad: float | None = None
    original_price_mad: float | None = None
    product_url: str | None = None
    affiliate_link: str | None = None
    image_url: str | None = None

    def to_dict(self) -> dict:
        value = dataclasses.asdict(self)
        value["limitations"] = list(self.limitations)
        return value


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_key(value: str) -> str:
    return re.sub(r"[^a-z0-9_.-]+", "-", value.lower()).strip("-")[:120]


def _cached_get(url: str, cache_key: str, fetcher: Callable | None = None) -> bytes:
    """Fetch once per conservative TTL; stop on blocking instead of retrying."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{_safe_key(cache_key)}.cache"
    if cache_path.exists() and time.time() - cache_path.stat().st_mtime < CACHE_TTL_SECONDS:
        return cache_path.read_bytes()
    fetch = fetcher or requests.get
    try:
        response = fetch(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise SourceUnavailable(f"network error for {url}: {exc}") from exc
    status = getattr(response, "status_code", 200)
    if status in (403, 429):
        raise SourceUnavailable(f"source blocked or throttled the request ({status}); stopped without retry")
    if status >= 400:
        raise SourceUnavailable(f"source returned HTTP {status}")
    content = getattr(response, "content", None)
    if content is None:
        content = response.text.encode("utf-8")
    cache_path.write_bytes(content)
    return content


def _parse_traffic(text: str) -> float | None:
    cleaned = text.upper().replace("+", "").replace(",", "").strip()
    match = re.match(r"([0-9.]+)\s*([KMB]?)", cleaned)
    if not match:
        return None
    number = float(match.group(1))
    return number * {"": 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}[match.group(2)]


def google_trends_signals(query: str, country: str, fetcher: Callable | None = None) -> list[Signal]:
    """Read Google's public daily-trends RSS. Traffic is search-volume proxy, not sales."""
    geo = country.upper()
    url = f"https://trends.google.com/trending/rss?geo={quote(geo)}"
    root = ET.fromstring(_cached_get(url, f"google-trends-{geo}", fetcher))
    observed_at = _utc_now()
    query_tokens = {t for t in re.findall(r"\w+", query.lower()) if len(t) > 2}
    output: list[Signal] = []
    ns = {"ht": "https://trends.google.com/trending/rss"}
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        haystack = title.lower()
        if query_tokens and not any(token in haystack for token in query_tokens):
            continue
        traffic_text = item.findtext("ht:approx_traffic", default="", namespaces=ns)
        output.append(Signal(
            product=title,
            source_name="Google Trends daily RSS",
            source_url=url,
            observed_at=observed_at,
            geography=geo,
            metric="approximate search traffic",
            value=_parse_traffic(traffic_text),
            unit="searches",
            is_proxy=True,
            confidence=0.68 if traffic_text else 0.5,
            limitations=(
                "Search interest is a demand proxy, not verified sales or revenue.",
                "The public daily feed is selective and does not represent every product or category.",
            ),
        ))
    return output


def apple_chart_signals(query: str, country: str, fetcher: Callable | None = None) -> list[Signal]:
    """Read Apple Marketing Tools charts and enrich price/release data via iTunes Lookup."""
    geo = country.lower()
    if geo not in APPLE_COUNTRIES:
        return []
    observed_at = _utc_now()
    query_tokens = {t for t in re.findall(r"\w+", query.lower()) if len(t) > 2}
    signals: list[Signal] = []
    for chart, chart_label in (("top-free", "free app chart rank"), ("top-paid", "paid app chart rank")):
        chart_url = f"https://rss.marketingtools.apple.com/api/v2/{geo}/apps/{chart}/100/apps.json"
        payload = json.loads(_cached_get(chart_url, f"apple-{geo}-{chart}", fetcher))
        entries = payload.get("feed", {}).get("results", [])
        candidates = []
        for rank, item in enumerate(entries, 1):
            name = item.get("name", "")
            artist = item.get("artistName", "")
            genres = item.get("genres", [])
            name = name.get("label", "") if isinstance(name, dict) else name
            artist = artist.get("label", "") if isinstance(artist, dict) else artist
            genres = [g.get("name", g.get("label", "")) if isinstance(g, dict) else g for g in genres]
            text = " ".join([str(name), str(artist), " ".join(genres)]).lower()
            if query_tokens and not any(token in text for token in query_tokens):
                continue
            candidates.append((rank, item))
        details = _apple_lookup([item.get("id") for _, item in candidates if item.get("id")], geo, fetcher)
        for rank, item in candidates:
            detail = details.get(str(item.get("id")), {})
            signals.append(Signal(
                product=name or "Unknown app",
                source_name="Apple Marketing Tools chart",
                source_url=chart_url,
                observed_at=observed_at,
                geography=geo.upper(),
                metric=chart_label,
                value=float(rank),
                unit="rank (1 is highest)",
                is_proxy=True,
                confidence=0.82,
                category=", ".join(genres),
                price=detail.get("price"),
                currency=detail.get("currency"),
                first_released_at=detail.get("releaseDate"),
                limitations=(
                    "Chart position is an Apple storefront popularity proxy; Apple does not publish unit sales here.",
                    "Coverage is limited to apps and the selected storefront country.",
                ),
            ))
    return signals


def _apple_lookup(ids: Iterable[str], country: str, fetcher: Callable | None = None) -> dict[str, dict]:
    ids = list(ids)
    if not ids:
        return {}
    url = f"https://itunes.apple.com/lookup?id={quote(','.join(ids))}&country={quote(country)}"
    try:
        payload = json.loads(_cached_get(url, f"itunes-lookup-{country}-{'-'.join(ids)}", fetcher))
    except SourceUnavailable:
        return {}
    return {str(row.get("trackId")): row for row in payload.get("results", []) if row.get("trackId")}


def google_books_signals(query: str, country: str, fetcher: Callable | None = None) -> list[Signal]:
    """Public Google Books catalog signals for ebooks. Catalog volume/price are proxies, not sales."""
    url = f"https://www.googleapis.com/books/v1/volumes?q={quote(query)}&filter=ebooks&maxResults=40&country={quote(country.upper())}"
    payload = json.loads(_cached_get(url, f"google-books-{country}-{query}", fetcher))
    observed_at = _utc_now()
    total = payload.get("totalItems")
    output = []
    for item in payload.get("items", []):
        info = item.get("volumeInfo", {})
        sale = item.get("saleInfo", {})
        price_info = sale.get("retailPrice") or sale.get("listPrice") or {}
        title = info.get("title") or "Untitled ebook"
        categories = info.get("categories") or []
        published = info.get("publishedDate")
        output.append(Signal(
            product=title,
            source_name="Google Books public catalog",
            source_url=url,
            observed_at=observed_at,
            geography=country.upper(),
            metric="ebook catalog result count",
            value=float(total) if isinstance(total, (int, float)) else None,
            unit="catalog matches",
            is_proxy=True,
            confidence=0.62,
            category=", ".join(categories),
            price=price_info.get("amount"),
            currency=price_info.get("currencyCode"),
            first_released_at=published,
            limitations=(
                "Catalog result count and listed price are availability/competition proxies, not verified demand or sales.",
                "Coverage and prices vary by country, publisher metadata, and Google Books availability.",
            ),
        ))
    return output


TARGET_CURRENCY = os.getenv("MARKET_SPY_TARGET_CURRENCY", "MAD")


def _aliexpress_risk_score(rating_percent: float | None, volume: float | None) -> float | None:
    """Safety score (0-100, higher = lower risk) from buyer rating and sales depth.

    Rating is the AliExpress positive-feedback rate. Low volume means the rating is
    thin evidence, so it is discounted. Missing rating means unknown risk (None).
    """
    if rating_percent is None:
        return None
    depth = 1.0 if (volume or 0) >= 500 else 0.9 if (volume or 0) >= 100 else 0.75
    return round(max(0.0, min(100.0, rating_percent)) * depth, 2)


def aliexpress_signals(query: str, country: str, fetcher: Callable | None = None, top_n: int | None = None) -> list[Signal]:
    """Official AliExpress Affiliate API: best sellers per ship-to country (real 30-day volume)."""
    if not aliexpress.is_configured():
        raise SourceUnavailable("AliExpress Affiliate API credentials are not configured (ALIEXPRESS_APP_KEY/ALIEXPRESS_APP_SECRET)")
    get_bytes = lambda url, key: _cached_get(url, key, fetcher)
    keywords = None if top_n else (query.strip() or None)
    try:
        products = aliexpress.fetch_products(country, get_bytes, page_size=50, keywords=keywords)
    except aliexpress.AliExpressAPIError as exc:
        raise SourceUnavailable(f"AliExpress API error: {exc}") from exc
    observed_at = _utc_now()
    rates: dict[str, fx.Rate] = {}
    output: list[Signal] = []
    for item in products:
        price_mad = original_mad = None
        limitations = [
            "Volume is AliExpress-reported recent sales across all buyers, not only this country.",
            "Commission rate is the current published rate and can change; earnings are not guaranteed.",
        ]
        if item.currency and item.sale_price is not None:
            try:
                rate = rates.get(item.currency) or fx.get_rate(item.currency, TARGET_CURRENCY, get_bytes)
                rates[item.currency] = rate
                price_mad = fx.convert(item.sale_price, rate)
                original_mad = fx.convert(item.original_price, rate)
                limitations.append(f"{TARGET_CURRENCY} price converted at {rate.value} {rate.base}->{rate.quote} ({rate.source_url}, {rate.as_of}); checkout price may differ.")
            except (SourceUnavailable, ValueError, json.JSONDecodeError) as exc:
                limitations.append(f"Currency conversion unavailable: {exc}")
        output.append(Signal(
            product=item.title,
            source_name="AliExpress Affiliate API (hot products)" if top_n else "AliExpress Affiliate API (product search)",
            source_url=item.product_url or aliexpress.GATEWAY_URL,
            observed_at=observed_at,
            geography=country.upper(),
            metric="units sold (recent, AliExpress-reported)",
            value=item.volume_30d,
            unit="orders",
            is_proxy=False,
            confidence=0.85 if item.volume_30d is not None else 0.6,
            category=item.category,
            price=item.sale_price,
            currency=item.currency,
            limitations=tuple(limitations),
            commission_rate=item.commission_rate,
            risk_score=_aliexpress_risk_score(item.rating_percent, item.volume_30d),
            rank_position=item.rank,
            rating_percent=item.rating_percent,
            original_price=item.original_price,
            price_mad=price_mad,
            original_price_mad=original_mad,
            product_url=item.product_url,
            affiliate_link=item.affiliate_link,
            image_url=item.image_url,
        ))
    return output


def _signal_score(signal: Signal) -> float:
    if signal.value is None:
        metric_strength = 0.25
    elif "rank" in signal.metric:
        metric_strength = max(0.0, 1.0 - (signal.value - 1.0) / 100.0)
    elif "traffic" in signal.metric:
        metric_strength = min(1.0, math.log10(max(signal.value, 1.0)) / 7.0)
    elif "units sold" in signal.metric:
        metric_strength = min(1.0, math.log10(max(signal.value, 1.0)) / 5.0)
    else:
        metric_strength = 0.4
    newness = 0.0
    if signal.first_released_at:
        try:
            released = datetime.fromisoformat(signal.first_released_at.replace("Z", "+00:00"))
            if released.tzinfo is None:
                released = released.replace(tzinfo=timezone.utc)
            age_days = max(0, (datetime.now(timezone.utc) - released).days)
            newness = max(0.0, 1.0 - age_days / 365.0)
        except ValueError:
            pass
    return round(100 * signal.confidence * (0.8 * metric_strength + 0.2 * newness), 2)


def _profit_evidence_gate(signal: Signal, market_category: str) -> dict:
    """No-go unless every action-driving profit input is source-backed and strong enough."""
    evidence = {
        "demand_purchase_intent_proxy": _signal_score(signal) if signal.value is not None else None,
        "competition": round(max(0.0, 100.0 - signal.value), 2) if signal.value is not None and "rank" in signal.metric else None,
        "price": signal.price,
        "margin_potential": None,
        "trend_velocity": None,
        "freshness": 100.0 if signal.observed_at else None,
        "geography": 100.0 if signal.geography else None,
        "production_cost": None,
        "production_time": None,
        "confidence": round(signal.confidence * 100, 2),
        "rights_fulfillment_market_risk": None,
        "provenance": 100.0 if signal.source_url else None,
    }
    if signal.commission_rate is not None:
        # Affiliate listing: nothing is produced, the margin is the published commission.
        evidence["competition"] = evidence["competition"] if evidence["competition"] is not None else _rank_competition(signal)
        evidence["margin_potential"] = _commission_score(signal.commission_rate)
        evidence["trend_velocity"] = _signal_score(signal) if signal.value is not None else None
        evidence["production_cost"] = 0.0
        evidence["production_time"] = 0.0
        evidence["rights_fulfillment_market_risk"] = signal.risk_score
    required = tuple(evidence)
    missing = [key for key in required if evidence[key] is None]
    demand = evidence["demand_purchase_intent_proxy"]
    weak_profit = demand is not None and demand < 35.0
    decision = "go" if not missing and not weak_profit else "no-go"
    reasons = []
    if missing:
        reasons.append("missing source-backed inputs: " + ", ".join(missing))
    if weak_profit:
        reasons.append("demand/purchase-intent proxy is below the conservative 35/100 floor")
    return {
        "decision": decision,
        "evidence": evidence,
        "missing_required_data": missing,
        "reasons": reasons,
        "profit_guaranteed": False,
        "disclaimer": "The score is a decision aid, not a profit or ranking guarantee.",
    }


def _category_scorecard(signal: Signal, market_category: str) -> dict:
    profile = MARKET_CATEGORY_PROFILES[market_category]
    observed = {
        "demand_momentum": _signal_score(signal) if signal.value is not None else None,
        "topic_demand": _signal_score(signal) if signal.value is not None else None,
        "style_demand": _signal_score(signal) if signal.value is not None else None,
        "geography": 100.0 if signal.geography else None,
        "geography_language": None,
        "competition": round(max(0.0, 100.0 - signal.value), 2) if signal.value is not None and "rank" in signal.metric else None,
        "price": signal.price,
        "freshness": 100.0 if signal.observed_at else None,
        "provenance": 100.0 if signal.source_url else None,
        "confidence": round(signal.confidence * 100, 2),
        "rights_risk": None,
        "fulfillment_risk": None,
        "use_case_demand": _signal_score(signal) if signal.value is not None else None,
        "format_printability": None,
        "licensing_risk": None,
        "originality_review": None,
        "similarity_review": None,
        "trademark_ip_risk": None,
        "theme_demand": _signal_score(signal) if signal.value is not None else None,
        "audience_demand": _signal_score(signal) if signal.value is not None else None,
        "age_band": None,
        "print_economics": None,
        "child_safety": None,
        "illustration_rights_risk": None,
        "user_supplied_topic": None,
        "user_supplied_message": None,
    }
    missing = [key for key in profile["required_metrics"] if observed.get(key) is None]
    return {
        "market_category": market_category,
        "category_label": profile["label"],
        "criteria": profile["criteria"],
        "components": {key: observed.get(key) for key in profile["required_metrics"]},
        "eligible": not missing,
        "category_score": None if missing else round(sum(float(observed[key]) for key in profile["required_metrics"]) / len(profile["required_metrics"]), 2),
        "missing_required_data": missing,
        "rule": "Missing category-specific data means no recommendation, production brief, or publish action.",
    }


def _commission_score(rate: float | None) -> float | None:
    """Commission percent mapped to 0-100 (10%+ = 100)."""
    return None if rate is None else round(min(100.0, max(0.0, rate) * 10.0), 2)


def _rank_competition(signal: Signal) -> float | None:
    """Position in a best-seller list: rank 1 of 50 scores ~100, rank 50 scores ~2."""
    if signal.rank_position is None:
        return None
    return round(max(0.0, 100.0 - (signal.rank_position - 1) * 2.0), 2)


def _price_fit(price_mad: float | None) -> float | None:
    """Impulse-buy fit for social traffic: 20-400 MAD is best, very cheap or expensive scores lower."""
    if price_mad is None:
        return None
    if 20 <= price_mad <= 400:
        return 100.0
    if price_mad < 20:
        return 70.0
    return round(max(30.0, 100.0 - (price_mad - 400) / 20.0), 2)


def _affiliate_scorecard(signal: Signal, signals: list[Signal]) -> dict:
    """Transparent affiliate gate. Missing commercial inputs can never become a recommendation."""
    matching = [s for s in signals if s.product.casefold() == signal.product.casefold()]
    demand = _signal_score(signal)
    freshness = 100.0 if signal.observed_at else None
    provenance = round(100 * signal.confidence, 2) if signal.source_url else None
    competition = None
    ranks = [s.value for s in matching if s.value is not None and "rank" in s.metric]
    if ranks:
        competition = round(max(0.0, 100.0 - min(ranks)), 2)
    if competition is None:
        competition = next((c for c in (_rank_competition(s) for s in matching) if c is not None), None)
    price = next((s.price for s in matching if s.price is not None), None)
    price_mad = next((s.price_mad for s in matching if s.price_mad is not None), None)
    commission_rate = next((s.commission_rate for s in matching if s.commission_rate is not None), None)
    risk = next((s.risk_score for s in matching if s.risk_score is not None), None)
    components = {
        "demand_momentum": demand,
        "geography": 100.0 if signal.geography else None,
        "competition": competition,
        "price": price,
        "commission": commission_rate,
        "freshness": freshness,
        "provenance": provenance,
        "confidence": round(100 * signal.confidence, 2),
        "risk": risk,
    }
    required = ("demand_momentum", "geography", "competition", "price", "commission", "freshness", "provenance", "confidence", "risk")
    missing = [key for key in required if components[key] is None]
    normalized = dict(components)
    if not missing:
        normalized["commission"] = _commission_score(commission_rate)
        # Raw price is not a score; use MAD price fit when known, otherwise neutral.
        normalized["price"] = _price_fit(price_mad) if price_mad is not None else 50.0
    return {
        "eligible": not missing,
        "recommendation_score": None if missing else round(sum(float(normalized[k]) for k in required) / len(required), 2),
        "components": components,
        "normalized_components": None if missing else normalized,
        "commission_rate_percent": commission_rate,
        "price_mad": price_mad,
        "missing_required_data": missing,
        "rule": "No affiliate recommendation or publish brief when any required component is missing.",
    }


def build_report(query: str, geography: str, signals: list[Signal], errors: list[str] | None = None, market_category: str | None = None) -> dict:
    market_category = classify_market_category(query, market_category)
    category_profile = MARKET_CATEGORY_PROFILES[market_category]
    ranked = sorted(signals, key=_signal_score, reverse=True)
    prices = [s.price for s in signals if s.price is not None]
    opportunities = []
    seen = set()
    for signal in ranked:
        key = signal.product.casefold()
        if key in seen:
            continue
        seen.add(key)
        affiliate_scorecard = _affiliate_scorecard(signal, signals)
        category_scorecard = _category_scorecard(signal, market_category)
        profit_gate = _profit_evidence_gate(signal, market_category)
        opportunities.append({
            "product": signal.product,
            "opportunity_score": _signal_score(signal),
            "affiliate_scorecard": affiliate_scorecard,
            "category_scorecard": category_scorecard,
            "profit_evidence_gate": profit_gate,
            "geography": signal.geography,
            "metric_or_proxy": signal.metric,
            "is_verified_sales": not signal.is_proxy and "sales" in signal.metric.lower(),
            "confidence": signal.confidence,
            "observed_at": signal.observed_at,
            "source_urls": sorted({s.source_url for s in signals if s.product.casefold() == key}),
            "limitations": sorted({note for s in signals if s.product.casefold() == key for note in s.limitations}),
            "feeds": ["Affiliate Spider", "Digital Products Spider"],
            "price": signal.price,
            "currency": signal.currency,
            "price_mad": signal.price_mad,
            "original_price_mad": signal.original_price_mad,
            "sales_volume": signal.value if "units sold" in signal.metric else None,
            "rating_percent": signal.rating_percent,
            "commission_rate_percent": signal.commission_rate,
            "product_url": signal.product_url,
            "affiliate_link": signal.affiliate_link,
            "image_url": signal.image_url,
            "rank_position": signal.rank_position,
        })
    return {
        "query": query,
        "geography": geography.upper(),
        "market_category": market_category,
        "category_profile": category_profile,
        "generated_at": _utc_now(),
        "verified_sales_available": any(not s.is_proxy and "sales" in s.metric.lower() for s in signals),
        "sales_disclaimer": "No true sales claim is made unless a source explicitly reports sales. Chart rank and search interest are proxies.",
        "profit_policy": "No random selection: every recommendation needs source-backed demand/purchase-intent, competition, price/margin potential, trend velocity/freshness, geography, production cost/time, confidence, provenance, and risks. Missing inputs or weak potential is no-go. Profit is never guaranteed.",
        "price_summary": {
            "currency_note": "Currencies are not converted; compare only like-for-like values.",
            "observations": len(prices),
            "minimum": min(prices) if prices else None,
            "maximum": max(prices) if prices else None,
            "average": round(sum(prices) / len(prices), 2) if prices else None,
        },
        "competition_proxy": {
            "matching_chart_entries": sum("rank" in s.metric for s in signals),
            "limitation": "Matching chart-entry count is only a visibility/competition proxy, not total seller count.",
        },
        "opportunities": opportunities,
        "signals": [s.to_dict() | {"score": _signal_score(s)} for s in ranked],
        "source_errors": errors or [],
        "handoff": {
            "schema_version": MARKET_SPY_CONTRACT_VERSION,
            "affiliate_spider": [item for item in opportunities if item["affiliate_scorecard"]["eligible"] and item["profit_evidence_gate"]["decision"] == "go"][:10],
            "affiliate_candidates_requiring_data": [item for item in opportunities if not item["affiliate_scorecard"]["eligible"] or item["profit_evidence_gate"]["decision"] != "go"][:10],
            "digital_product_spider": [item for item in opportunities if market_category == "digital_product" and item["category_scorecard"]["eligible"] and item["profit_evidence_gate"]["decision"] == "go"][:10],
            "ebook_spider": [item for item in opportunities if market_category == "ebook" and item["category_scorecard"]["eligible"] and item["profit_evidence_gate"]["decision"] == "go"][:10],
            "design_asset_spider": [item for item in opportunities if market_category == "design_asset" and item["category_scorecard"]["eligible"] and item["profit_evidence_gate"]["decision"] == "go"][:10],
            "wall_art_decor_spider": [item for item in opportunities if market_category == "wall_art_decor" and item["category_scorecard"]["eligible"] and item["profit_evidence_gate"]["decision"] == "go"][:10],
            "sticker_spider": [item for item in opportunities if market_category == "sticker" and item["category_scorecard"]["eligible"] and item["profit_evidence_gate"]["decision"] == "go"][:10],
            "logo_spider": [item for item in opportunities if market_category == "logo" and item["category_scorecard"]["eligible"] and item["profit_evidence_gate"]["decision"] == "go"][:10],
            "children_coloring_book_spider": [item for item in opportunities if market_category == "children_coloring_book" and item["category_scorecard"]["eligible"] and item["profit_evidence_gate"]["decision"] == "go"][:10],
            "illustrated_story_spider": [item for item in opportunities if market_category == "illustrated_story" and item["category_scorecard"]["eligible"] and item["profit_evidence_gate"]["decision"] == "go"][:10],
            "physical_product_spider": [item for item in opportunities if market_category == "physical_product" and item["category_scorecard"]["eligible"] and item["profit_evidence_gate"]["decision"] == "go"][:10],
            "category_candidates_requiring_data": [item for item in opportunities if not item["category_scorecard"]["eligible"] or item["profit_evidence_gate"]["decision"] != "go"][:10],
            "execution_allowed": False,
            "allowed_automation": ["public_signal_monitoring", "opportunity_scoring", "rejection", "brief_drafts", "listing_drafts"],
            "forbidden_actions": ["publishing", "spending", "account_creation", "user_representative_messaging"],
            "affiliate_policy": "Data-scored only: missing demand/momentum, geography, competition, price, commission, freshness, provenance, confidence, or risk means no recommendation and no publish brief.",
            "digital_products_policy": "Category-scored only: ebooks, digital products, designs, wall art/decor, stickers, logos, coloring books, illustrated stories, and physical products each use their own required metrics. Missing data means no recommendation, production brief, or publish action.",
            "logo_policy": "Originality/similarity checks are required risk reviews, never a trademark clearance claim.",
            "illustrated_story_policy": "Market Spy may assess demand, age band, language/geography, format, price, competition, and illustration rights only. Story topic and message must come from the user; no automatic story production.",
        },
    }


def research_market(query: str, geography: str = "US", fetcher: Callable | None = None, market_category: str | None = None,
                    top_n: int | None = None) -> dict:
    """Collect source-backed signals. Partial source failure remains explicit in the report.

    ``top_n`` switches to best-sellers-per-geography mode: the AliExpress Affiliate API
    hot-product list for ``geography`` (no keyword filter), ranked and cut to N.
    """
    signals: list[Signal] = []
    errors: list[str] = []
    if top_n:
        resolved_category = market_category if market_category in MARKET_CATEGORY_PROFILES else "physical_product"
        sources = [("aliexpress", lambda q, g, f: aliexpress_signals(q, g, f, top_n=top_n))]
    else:
        resolved_category = classify_market_category(query, market_category)
        sources = [("google_trends", google_trends_signals)]
        if resolved_category == "digital_product":
            sources.append(("apple_charts", apple_chart_signals))
        elif resolved_category == "ebook":
            sources.append(("google_books", google_books_signals))
        elif resolved_category == "physical_product" and aliexpress.is_configured():
            sources.append(("aliexpress", aliexpress_signals))
    for name, source in sources:
        try:
            signals.extend(source(query, geography, fetcher))
        except (SourceUnavailable, ValueError, ET.ParseError, json.JSONDecodeError) as exc:
            errors.append(f"{name}: {exc}")
    report = build_report(query, geography, signals, errors, resolved_category)
    if top_n:
        report["mode"] = "top_n_per_geography"
        report["top_n"] = top_n
        report["opportunities"] = report["opportunities"][:top_n]
        report["price_summary"]["currency_note"] = f"price is in the source currency; price_mad is converted to {TARGET_CURRENCY} with the rate named in each item's limitations."
    return report


def top_products_by_geography(geographies: Iterable[str], n: int = 10, fetcher: Callable | None = None) -> dict[str, dict]:
    """Top N best sellers for each geography (read-only)."""
    return {geo.upper(): research_market("", geo, fetcher, top_n=n) for geo in geographies}


def format_report(report: dict) -> str:
    lines = [
        f"# Market Spy: {report['query']} ({report['geography']})",
        f"Observed at: {report['generated_at']}",
        "",
        report["sales_disclaimer"],
        report["profit_policy"],
        "",
    ]
    if not report["opportunities"]:
        lines.append("No matching public signals were available. Broaden the field or try another geography; no demand value was invented.")
    for index, item in enumerate(report["opportunities"][:10], 1):
        lines.extend([
            f"## {index}. {item['product']} - score {item['opportunity_score']}",
            f"- Geography: {item['geography']}",
            f"- Metric/proxy: {item['metric_or_proxy']}",
            f"- Confidence: {item['confidence']:.0%}",
            f"- Verified sales: {'yes' if item['is_verified_sales'] else 'no'}",
            *([f"- Price: {item['price_mad']} MAD" + (f" (was {item['original_price_mad']} MAD)" if item.get('original_price_mad') and item['original_price_mad'] != item['price_mad'] else "")] if item.get("price_mad") is not None else []),
            *([f"- Sales volume: {int(item['sales_volume'])} | rating: {item.get('rating_percent')}% | commission: {item.get('commission_rate_percent')}%"] if item.get("sales_volume") is not None else []),
            *([f"- Affiliate score: {item['affiliate_scorecard']['recommendation_score']}"] if item["affiliate_scorecard"]["eligible"] else []),
            *([f"- Affiliate link: {item['affiliate_link']}"] if item.get("affiliate_link") else []),
            f"- Sources: {', '.join(item['source_urls'])}",
            f"- Limitations: {'; '.join(item['limitations'])}",
            "",
        ])
    if report["source_errors"]:
        lines.extend(["## Source limits", *[f"- {error}" for error in report["source_errors"]]])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Source-backed market intelligence (read-only)")
    parser.add_argument("query", nargs="?", default="", help="Product, field, or niche (optional with --top)")
    parser.add_argument("--geography", default="US", help="ISO country code, e.g. US, FR, MA")
    parser.add_argument("--category", choices=sorted(MARKET_CATEGORY_PROFILES), help="Optional explicit market category")
    parser.add_argument("--top", type=int, default=None, help="Best-sellers mode: top N products for --geography (AliExpress Affiliate API)")
    parser.add_argument("--json", action="store_true", help="Print structured JSON")
    args = parser.parse_args()
    report = research_market(args.query, args.geography, market_category=args.category, top_n=args.top)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else format_report(report))


if __name__ == "__main__":
    main()
