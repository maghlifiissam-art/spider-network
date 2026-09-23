"""AliExpress Affiliate API connector (read-only).

Talks to the official AliExpress Open Platform gateway (``/sync``) with the
Affiliate API methods:

* ``aliexpress.affiliate.hotproduct.query`` - hot / best-selling affiliate products
  for a ship-to country, with price, 30-day sales volume, rating and commission.
* ``aliexpress.affiliate.product.query`` - keyword search with the same fields.
* ``aliexpress.affiliate.link.generate`` - turn normal AliExpress URLs into
  affiliate tracking links.

Secrets are never stored in the repository. Credentials come only from the
environment:

    ALIEXPRESS_APP_KEY       app key from https://openservice.aliexpress.com (App Console)
    ALIEXPRESS_APP_SECRET    app secret for that key
    ALIEXPRESS_TRACKING_ID   Portals tracking ID (default: "default")

The connector performs no purchases, publishing or account changes.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass, field
from typing import Callable, Iterable
from urllib.parse import urlencode

GATEWAY_URL = os.getenv("ALIEXPRESS_GATEWAY_URL", "https://api-sg.aliexpress.com/sync")
HOT_PRODUCTS_METHOD = "aliexpress.affiliate.hotproduct.query"
PRODUCT_QUERY_METHOD = "aliexpress.affiliate.product.query"
LINK_GENERATE_METHOD = "aliexpress.affiliate.link.generate"
PRODUCT_FIELDS = ",".join((
    "product_id", "product_title", "product_detail_url", "product_main_image_url",
    "target_sale_price", "target_sale_price_currency", "target_original_price",
    "target_original_price_currency", "lastest_volume", "evaluate_rate",
    "commission_rate", "hot_product_commission_rate", "promotion_link",
    "first_level_category_name", "second_level_category_name", "discount", "shop_url",
))


class AliExpressConfigError(RuntimeError):
    """Credentials are missing; nothing was requested."""


class AliExpressAPIError(RuntimeError):
    """The gateway answered with an error payload."""


@dataclass(frozen=True)
class Credentials:
    app_key: str
    app_secret: str
    tracking_id: str = "default"

    @classmethod
    def from_env(cls) -> "Credentials":
        key = os.getenv("ALIEXPRESS_APP_KEY", "").strip()
        secret = os.getenv("ALIEXPRESS_APP_SECRET", "").strip()
        if not key or not secret:
            raise AliExpressConfigError("ALIEXPRESS_APP_KEY and ALIEXPRESS_APP_SECRET must be set in the environment")
        return cls(key, secret, os.getenv("ALIEXPRESS_TRACKING_ID", "default").strip() or "default")

    def __repr__(self) -> str:  # never leak the secret in logs/tracebacks
        return f"Credentials(app_key='{self.app_key[:4]}…', app_secret='***', tracking_id='{self.tracking_id}')"


def is_configured() -> bool:
    return bool(os.getenv("ALIEXPRESS_APP_KEY", "").strip() and os.getenv("ALIEXPRESS_APP_SECRET", "").strip())


def sign(params: dict, app_secret: str) -> str:
    """HMAC-SHA256 signature for the /sync gateway: sorted key+value pairs, upper-case hex."""
    payload = "".join(f"{key}{params[key]}" for key in sorted(params) if key != "sign" and params[key] is not None)
    return hmac.new(app_secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest().upper()


def build_request_url(method: str, business_params: dict, credentials: Credentials, timestamp_ms: int | None = None) -> str:
    params = {
        "app_key": credentials.app_key,
        "method": method,
        "sign_method": "sha256",
        "timestamp": str(timestamp_ms if timestamp_ms is not None else int(time.time() * 1000)),
        **{k: str(v) for k, v in business_params.items() if v is not None and v != ""},
    }
    params["sign"] = sign(params, credentials.app_secret)
    return f"{GATEWAY_URL}?{urlencode(params)}"


def _percent(value) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).strip().rstrip("%"))
    except ValueError:
        return None


def _number(value) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


def _unwrap(payload: dict, method: str) -> dict:
    if "error_response" in payload:
        err = payload["error_response"]
        raise AliExpressAPIError(f"{err.get('code')}: {err.get('msg') or err.get('sub_msg')}")
    key = method.replace(".", "_") + "_response"
    resp = payload.get(key, {}).get("resp_result")
    if resp is None:
        raise AliExpressAPIError(f"unexpected response shape for {method}")
    code = str(resp.get("resp_code", "200"))
    if code != "200":
        raise AliExpressAPIError(f"{code}: {resp.get('resp_msg')}")
    return resp.get("result") or {}


@dataclass(frozen=True)
class AffiliateProduct:
    product_id: str
    title: str
    product_url: str
    image_url: str | None
    sale_price: float | None
    original_price: float | None
    currency: str | None
    volume_30d: float | None
    rating_percent: float | None
    commission_rate: float | None
    category: str
    affiliate_link: str | None
    rank: int
    raw_keys: tuple[str, ...] = field(default=(), repr=False)


def parse_products(payload: dict, method: str = HOT_PRODUCTS_METHOD) -> list[AffiliateProduct]:
    result = _unwrap(payload, method)
    rows = (result.get("products") or {}).get("product") or []
    products = []
    for rank, row in enumerate(rows, 1):
        commission = _percent(row.get("hot_product_commission_rate")) or _percent(row.get("commission_rate"))
        products.append(AffiliateProduct(
            product_id=str(row.get("product_id", "")),
            title=str(row.get("product_title", "")).strip(),
            product_url=str(row.get("product_detail_url", "")),
            image_url=row.get("product_main_image_url"),
            sale_price=_number(row.get("target_sale_price")),
            original_price=_number(row.get("target_original_price")),
            currency=row.get("target_sale_price_currency") or row.get("target_original_price_currency"),
            volume_30d=_number(row.get("lastest_volume")),
            rating_percent=_percent(row.get("evaluate_rate")),
            commission_rate=commission,
            category=str(row.get("first_level_category_name") or ""),
            affiliate_link=row.get("promotion_link"),
            rank=rank,
            raw_keys=tuple(sorted(row)),
        ))
    return products


def hot_products_params(ship_to_country: str, page_size: int = 50, keywords: str | None = None,
                        target_currency: str = "USD", target_language: str = "EN", tracking_id: str = "default") -> dict:
    return {
        "ship_to_country": ship_to_country.upper(),
        "target_currency": target_currency,
        "target_language": target_language,
        "page_no": 1,
        "page_size": max(1, min(page_size, 50)),
        "sort": "LAST_VOLUME_DESC",
        "keywords": keywords,
        "tracking_id": tracking_id,
        "fields": PRODUCT_FIELDS,
    }


def fetch_products(ship_to_country: str, get_bytes: Callable[[str, str], bytes], page_size: int = 50,
                   keywords: str | None = None, credentials: Credentials | None = None) -> list[AffiliateProduct]:
    """Best sellers (or keyword results) for a country. ``get_bytes(url, cache_key)`` does the HTTP."""
    creds = credentials or Credentials.from_env()
    method = PRODUCT_QUERY_METHOD if keywords else HOT_PRODUCTS_METHOD
    params = hot_products_params(ship_to_country, page_size, keywords, tracking_id=creds.tracking_id)
    url = build_request_url(method, params, creds)
    cache_key = f"aliexpress-{method}-{ship_to_country.lower()}-{(keywords or 'top').lower()}-{page_size}"
    return parse_products(json.loads(get_bytes(url, cache_key)), method)


def generate_links(source_urls: Iterable[str], get_bytes: Callable[[str, str], bytes],
                   credentials: Credentials | None = None) -> dict[str, str]:
    """Map each AliExpress URL to its affiliate tracking link."""
    creds = credentials or Credentials.from_env()
    urls = [u for u in source_urls if u]
    if not urls:
        return {}
    params = {"promotion_link_type": 0, "source_values": ",".join(urls), "tracking_id": creds.tracking_id}
    url = build_request_url(LINK_GENERATE_METHOD, params, creds)
    result = _unwrap(json.loads(get_bytes(url, f"aliexpress-links-{hashlib.sha1(params['source_values'].encode()).hexdigest()[:16]}")), LINK_GENERATE_METHOD)
    rows = (result.get("promotion_links") or {}).get("promotion_link") or []
    return {row.get("source_value"): row.get("promotion_link") for row in rows if row.get("promotion_link")}
