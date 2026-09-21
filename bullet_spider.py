"""Safe, offline-first demand capture for Spider Network.

Bullet Spider turns aggregate, public demand signals (or Market Spy opportunities)
into ranked response proposals and production briefs. It never profiles people,
reads private search history, publishes, advertises, or messages customers.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable, Mapping, Protocol, Sequence
from urllib.parse import urlparse


class OpportunityCategory(str, Enum):
    AFFILIATE = "affiliate"
    DIGITAL_PRODUCT = "digital_product"
    DIGITAL_BOOK = "digital_book"
    PRODUCT_DESIGN = "product_design"
    DECOR_ART = "decor_art"


class ResponseType(str, Enum):
    NEW_PRODUCT = "new_product"
    LOCALIZATION = "localization"
    BUNDLE = "bundle"
    SERVICE_OFFER = "service_offer"
    PRICING_LISTING_UPDATE = "pricing_listing_update"


@dataclass(frozen=True)
class DemandSignal:
    signal_id: str
    query_or_topic: str
    geography: str
    observed_at: str
    source_url: str
    metric_name: str
    metric_value: float
    metric_kind: str = "proxy"
    previous_value: float | None = None
    confidence: float = 0.5
    competition: float = 0.5
    supply_gap: float = 0.5
    producibility: float = 0.5
    price_margin: float = 0.5
    price: float | None = None
    currency: str | None = None
    commission_rate: float | None = None
    risk: float = 0.5
    language: str | None = None
    category: str = OpportunityCategory.DIGITAL_PRODUCT.value
    limitations: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OpportunityAssessment:
    opportunity_id: str
    topic: str
    geography: str
    observed_at: str
    source_urls: tuple[str, ...]
    response_type: str
    category: str
    intent_score: float
    urgency_score: float
    competition_score: float
    supply_gap_score: float
    producibility_score: float
    price_margin_score: float
    risk_score: float
    opportunity_score: float
    affiliate_score: float | None
    affiliate_eligible: bool
    confidence: float
    limitations: tuple[str, ...]
    claim_status: str = "proposal_proxy_no_ranking_guarantee"


@dataclass(frozen=True)
class ProductionBrief:
    brief_id: str
    opportunity_id: str
    title: str
    response_type: str
    category: str
    geography: str
    target_language: str | None
    deliverables: tuple[str, ...]
    assigned_spiders: tuple[str, ...]
    source_urls: tuple[str, ...]
    observed_at: str
    review_gates: tuple[str, ...]
    seo_draft: Mapping[str, Any]
    listing_draft: Mapping[str, Any]
    pricing_draft: Mapping[str, Any]
    status: str = "draft_requires_human_approval"
    limitations: tuple[str, ...] = ()


class SignalAdapter(Protocol):
    """Plug-in boundary for public/authorized aggregate signal sources."""
    name: str

    def collect(self, request: Mapping[str, Any]) -> Sequence[DemandSignal]: ...


class OfflineFixtureAdapter:
    """Safe default adapter. It reads caller-supplied fixtures and does no network I/O."""
    name = "offline_fixture"

    def __init__(self, rows: Sequence[Mapping[str, Any]]):
        self._rows = rows

    def collect(self, request: Mapping[str, Any]) -> Sequence[DemandSignal]:
        geography = request.get("geography")
        topic = str(request.get("topic", "")).casefold()
        signals = [signal_from_mapping(row) for row in self._rows]
        return [
            signal for signal in signals
            if (not geography or signal.geography == geography)
            and (not topic or topic in signal.query_or_topic.casefold())
        ]


def _bounded(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 4)


def _parse_timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("observed_at must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _public_source_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("source_url must be an absolute http(s) URL")
    return value


def signal_from_mapping(row: Mapping[str, Any]) -> DemandSignal:
    """Normalize generic rows, including Market Spy opportunity-shaped records."""
    source_urls = row.get("source_urls") or [row.get("source_url")]
    source_url = next((url for url in source_urls if url), None)
    if not source_url:
        raise ValueError("Every signal needs a source URL")
    limitations = tuple(row.get("limitations") or ())
    metric_name = row.get("metric_name") or row.get("metric") or "unspecified_proxy"
    metric_kind = row.get("metric_kind") or row.get("evidence_type") or "proxy"
    if metric_kind not in {"proxy", "verified_sales", "first_party_aggregate"}:
        metric_kind = "proxy"
    return DemandSignal(
        signal_id=str(row.get("signal_id") or row.get("opportunity_id") or row.get("id")),
        query_or_topic=str(row.get("query_or_topic") or row.get("topic") or row.get("product") or ""),
        geography=str(row.get("geography") or "global"),
        observed_at=_parse_timestamp(str(row["observed_at"])),
        source_url=_public_source_url(str(source_url)),
        metric_name=str(metric_name),
        metric_value=float(row.get("metric_value", row.get("value", row.get("score", 0.0)))),
        metric_kind=metric_kind,
        previous_value=(None if row.get("previous_value") is None else float(row["previous_value"])),
        confidence=_bounded(row.get("confidence", 0.5)),
        competition=_bounded(row.get("competition", row.get("competition_score", 0.5))),
        supply_gap=_bounded(row.get("supply_gap", row.get("supply_gap_score", 0.5))),
        producibility=_bounded(row.get("producibility", 0.5)),
        price_margin=_bounded(row.get("price_margin", row.get("margin_score", 0.5))),
        price=(None if row.get("price") is None else float(row["price"])),
        currency=row.get("currency"),
        commission_rate=(None if row.get("commission_rate") is None else float(row["commission_rate"])),
        risk=_bounded(row.get("risk", row.get("risk_score", 0.5))),
        language=row.get("language"),
        category=str(row.get("category", OpportunityCategory.DIGITAL_PRODUCT.value)),
        limitations=limitations,
        metadata=row.get("metadata") or {},
    )


def _intent(signal: DemandSignal) -> float:
    name = signal.metric_name.casefold()
    commercial_terms = ("buy", "price", "order", "download", "template", "near me", "شراء", "ثمن", "طلب")
    lexical = 0.78 if any(term in signal.query_or_topic.casefold() for term in commercial_terms) else 0.48
    metric_boost = 0.12 if any(term in name for term in ("conversion", "cart", "purchase", "commercial")) else 0.0
    return _bounded(lexical + metric_boost + 0.1 * signal.confidence)


def _urgency(signal: DemandSignal) -> float:
    if signal.previous_value is None or signal.previous_value <= 0:
        return _bounded(0.45 * signal.confidence)
    growth = (signal.metric_value - signal.previous_value) / signal.previous_value
    return _bounded(0.45 + min(max(growth, -1.0), 2.0) * 0.25)


def _response_type(signal: DemandSignal) -> ResponseType:
    meta = signal.metadata
    if signal.language and meta.get("existing_language") and signal.language != meta["existing_language"]:
        return ResponseType.LOCALIZATION
    if meta.get("complementary_products", 0) >= 2:
        return ResponseType.BUNDLE
    if meta.get("existing_listing") and signal.supply_gap < 0.5:
        return ResponseType.PRICING_LISTING_UPDATE
    if meta.get("customization_required") or meta.get("service_intent"):
        return ResponseType.SERVICE_OFFER
    return ResponseType.NEW_PRODUCT


def _affiliate_score(signal: DemandSignal, urgency: float, as_of: datetime) -> tuple[float | None, tuple[str, ...]]:
    """Return a fully evidenced affiliate score, or explicit blockers.

    There is no fallback/random pick: every required component must be present.
    """
    blockers = []
    if signal.metric_value is None or signal.previous_value is None:
        blockers.append("missing demand or momentum baseline")
    if not signal.geography or signal.geography == "global":
        blockers.append("missing specific geography")
    if signal.price is None or not signal.currency:
        blockers.append("missing price or currency")
    if signal.commission_rate is None:
        blockers.append("missing commission rate")
    if not signal.source_url:
        blockers.append("missing provenance")
    observed = datetime.fromisoformat(signal.observed_at.replace("Z", "+00:00"))
    age_hours = max(0.0, (as_of - observed).total_seconds() / 3600)
    if age_hours > 168:
        blockers.append("signal is older than seven days")
    if blockers:
        return None, tuple(blockers)
    freshness = _bounded(1.0 - age_hours / 168.0)
    commission = _bounded(signal.commission_rate / 0.5)
    demand = _bounded(signal.metric_value / 100.0)
    score = _bounded(
        0.20 * demand + 0.15 * urgency + 0.10 * (1.0 - signal.competition)
        + 0.10 * signal.price_margin + 0.12 * commission + 0.10 * freshness
        + 0.10 * signal.confidence + 0.08 * signal.supply_gap + 0.05 * (1.0 - signal.risk)
    )
    return score, ()


def _category(value: str) -> OpportunityCategory:
    aliases = {
        "digital_products": OpportunityCategory.DIGITAL_PRODUCT,
        "ebook": OpportunityCategory.DIGITAL_BOOK,
        "ebooks": OpportunityCategory.DIGITAL_BOOK,
        "book": OpportunityCategory.DIGITAL_BOOK,
        "design": OpportunityCategory.PRODUCT_DESIGN,
        "designs": OpportunityCategory.PRODUCT_DESIGN,
        "wall_art": OpportunityCategory.DECOR_ART,
        "decor": OpportunityCategory.DECOR_ART,
        "tableau": OpportunityCategory.DECOR_ART,
    }
    try:
        return OpportunityCategory(value)
    except ValueError:
        if value in aliases:
            return aliases[value]
        raise ValueError(f"Unsupported opportunity category: {value}")


def assess_signal(signal: DemandSignal, as_of: datetime | None = None) -> OpportunityAssessment:
    intent = _intent(signal)
    urgency = _urgency(signal)
    as_of = as_of or datetime.now(timezone.utc)
    affiliate_score, affiliate_blockers = _affiliate_score(signal, urgency, as_of)
    score = _bounded(
        0.24 * intent
        + 0.16 * urgency
        + 0.16 * signal.supply_gap
        + 0.15 * signal.producibility
        + 0.14 * signal.price_margin
        + 0.08 * (1.0 - signal.competition)
        + 0.07 * signal.confidence
        - 0.18 * signal.risk
    )
    limits = list(signal.limitations)
    if signal.metric_kind == "proxy":
        limits.append("The demand metric is a proxy, not verified sales.")
    limits.extend(affiliate_blockers)
    limits.append("Search visibility and ranking are proposals only and are not guaranteed.")
    return OpportunityAssessment(
        opportunity_id=f"bullet-{signal.signal_id}",
        topic=signal.query_or_topic,
        geography=signal.geography,
        observed_at=signal.observed_at,
        source_urls=(signal.source_url,),
        response_type=_response_type(signal).value,
        category=_category(signal.category).value,
        intent_score=intent,
        urgency_score=urgency,
        competition_score=signal.competition,
        supply_gap_score=signal.supply_gap,
        producibility_score=signal.producibility,
        price_margin_score=signal.price_margin,
        risk_score=signal.risk,
        opportunity_score=score,
        affiliate_score=affiliate_score,
        affiliate_eligible=affiliate_score is not None,
        confidence=signal.confidence,
        limitations=tuple(dict.fromkeys(limits)),
    )


REVIEW_GATES = (
    "source_recency_and_provenance",
    "privacy_aggregate_signals_only",
    "intellectual_property_and_license",
    "truthful_claims_and_no_ranking_guarantee",
    "product_quality_and_accessibility",
    "price_and_margin_review",
    "human_publish_approval",
)


def build_production_brief(assessment: OpportunityAssessment, language: str | None = None) -> ProductionBrief:
    response = ResponseType(assessment.response_type)
    category_map = {
        OpportunityCategory.AFFILIATE: ("affiliate_spider", "qa_spider"),
        OpportunityCategory.DIGITAL_PRODUCT: ("digital_products_spider", "qa_spider"),
        OpportunityCategory.DIGITAL_BOOK: ("book_spider", "qa_spider"),
        OpportunityCategory.PRODUCT_DESIGN: ("visual_spider", "digital_products_spider", "qa_spider"),
        OpportunityCategory.DECOR_ART: ("visual_spider", "qa_spider"),
    }
    spider_map = {
        ResponseType.NEW_PRODUCT: ("digital_products_spider", "qa_spider"),
        ResponseType.LOCALIZATION: ("digital_products_spider", "translation_spider", "qa_spider"),
        ResponseType.BUNDLE: ("digital_products_spider", "catalog_spider", "qa_spider"),
        ResponseType.SERVICE_OFFER: ("service_offer_spider", "qa_spider"),
        ResponseType.PRICING_LISTING_UPDATE: ("catalog_spider", "qa_spider"),
    }
    title = f"{assessment.topic} - {assessment.geography}"
    return ProductionBrief(
        brief_id=f"brief-{assessment.opportunity_id}",
        opportunity_id=assessment.opportunity_id,
        title=title,
        response_type=response.value,
        category=assessment.category,
        geography=assessment.geography,
        target_language=language,
        deliverables=("product_or_offer_draft", "listing_draft", "seo_draft", "pricing_draft", "review_report"),
        assigned_spiders=tuple(dict.fromkeys(category_map[_category(assessment.category)] + spider_map[response])),
        source_urls=assessment.source_urls,
        observed_at=assessment.observed_at,
        review_gates=REVIEW_GATES,
        seo_draft={"primary_topic": assessment.topic, "geography": assessment.geography, "status": "proposal_no_ranking_guarantee"},
        listing_draft={"working_title": title, "status": "draft", "publish": False},
        pricing_draft={"strategy": "competitive_range_requires_current_source_review", "currency": None, "amount": None},
        limitations=assessment.limitations,
    )


def run_bullet_spider(
    request: Mapping[str, Any],
    adapters: Iterable[SignalAdapter] | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """Collect, score and brief opportunities without any external side effect."""
    adapters = tuple(adapters or ())
    if not adapters:
        return {
            "status": "offline_safe_no_sources_configured",
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "opportunities": [],
            "briefs": [],
            "limitations": ["No signal adapter was configured; no demand claims were made."],
        }
    signals: list[DemandSignal] = []
    for adapter in adapters:
        signals.extend(adapter.collect(request))
    as_of_raw = request.get("as_of")
    as_of = datetime.fromisoformat(str(as_of_raw).replace("Z", "+00:00")) if as_of_raw else datetime.now(timezone.utc)
    assessments = sorted((assess_signal(signal, as_of=as_of) for signal in signals), key=lambda item: (-(item.affiliate_score or -1), -item.opportunity_score, item.opportunity_id))[:limit]
    language = request.get("language")
    # No score, no recommendation or brief. Rejected assessments remain visible with blockers.
    briefs = [build_production_brief(item, language=language) for item in assessments if item.affiliate_eligible]
    return {
        "status": "drafts_only_requires_human_approval",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "opportunities": [asdict(item) for item in assessments],
        "briefs": [asdict(item) for item in briefs],
        "limitations": [
            "Only aggregate/public/authorized signals may be supplied.",
            "No individual profiling, private search history, publishing, ads, or outreach is performed.",
            "Scores are decision-support proxies, not sales or ranking guarantees.",
        ],
    }
