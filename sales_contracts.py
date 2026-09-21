"""Versioned, fail-closed contracts for the Sales Spider subnetwork (sales.v1)."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Literal

CONTRACT_VERSION = "sales.v1"
Channel = Literal["whatsapp", "tally", "web", "other"]
DealStatus = Literal["new", "qualified", "negotiating", "won", "lost", "no_reply"]

BANNED_PHRASES = (
    "ربح مضمون", "ضمان النجاح", "ربح مؤكد", "غنى سريع", "ناجح 100%",
    "guaranteed profit", "get rich quick",
)


def _iso(ts: str) -> None:
    datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _no_hype(text: str) -> None:
    low = text.lower()
    for phrase in BANNED_PHRASES:
        if phrase.lower() in low:
            raise ValueError(f"banned hype phrase: {phrase}")


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    price_mad: float
    delivery: Literal["email_after_payment_verification", "affiliate_external"]
    commission_rate: float = 1.0  # our share of the gross (1.0 = own product)
    active: bool = True

    def validate(self) -> None:
        if not self.sku or not self.name:
            raise ValueError("product sku and name required")
        if self.price_mad < 0:
            raise ValueError("price_mad must be >= 0")
        if not 0 <= self.commission_rate <= 1:
            raise ValueError("commission_rate must be 0..1")


@dataclass(frozen=True)
class Lead:
    lead_id: str
    channel: Channel
    source_ref: str
    product_sku: str
    created_at: str
    name: str = ""
    note: str = ""

    def validate(self) -> None:
        if not self.lead_id:
            raise ValueError("lead_id required")
        if not self.source_ref:
            raise ValueError("lead source_ref required: attribution is mandatory")
        if not self.product_sku:
            raise ValueError("product_sku required")
        _iso(self.created_at)


@dataclass(frozen=True)
class ObjectionScript:
    objection_id: str
    trigger_keywords: tuple
    reply_template: str

    def validate(self) -> None:
        if not self.objection_id or not self.reply_template:
            raise ValueError("objection script incomplete")
        if not self.trigger_keywords:
            raise ValueError("trigger keywords required")
        _no_hype(self.reply_template)


@dataclass
class ReplyDraft:
    draft_id: str
    lead_id: str
    body: str
    objection_id: str | None = None
    approved: bool = False
    send_allowed: bool = False
    contract_version: str = CONTRACT_VERSION
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def validate(self) -> None:
        if self.contract_version != CONTRACT_VERSION:
            raise ValueError("unsupported sales contract")
        if not self.draft_id or not self.lead_id or not self.body:
            raise ValueError("draft id, lead and body required")
        if self.approved:
            raise ValueError("drafts are never pre-approved; human review required")
        if self.send_allowed:
            raise ValueError("automatic sending is disabled by design")
        _no_hype(self.body)

    def review_dict(self) -> dict:
        """Stable serialization for pipelines (no runtime timestamp)."""
        self.validate()
        return {"draft_id": self.draft_id, "lead_id": self.lead_id,
                "objection_id": self.objection_id, "body": self.body,
                "approved": self.approved, "send_allowed": self.send_allowed}


@dataclass(frozen=True)
class DealOutcome:
    lead_id: str
    product_sku: str
    status: DealStatus
    price_mad: float
    payment_verified: bool = False

    def validate(self) -> None:
        if self.status == "won" and not self.payment_verified:
            raise ValueError("a deal can only be won after payment verification")
        if self.price_mad < 0:
            raise ValueError("price_mad must be >= 0")


@dataclass(frozen=True)
class AttributionEvent:
    lead_id: str
    source_ref: str
    campaign: str
    medium: str

    def validate(self) -> None:
        if not self.lead_id or not self.source_ref or not self.campaign:
            raise ValueError("attribution requires lead, source and campaign")


@dataclass(frozen=True)
class CommissionRecord:
    record_id: str
    lead_id: str
    product_sku: str
    gross_mad: float
    commission_mad: float
    beneficiary: Literal["owner", "affiliate_program"]
    status: Literal["pending", "paid"] = "pending"

    def validate(self) -> None:
        if self.gross_mad < 0:
            raise ValueError("gross must be >= 0")
        if not 0 <= self.commission_mad <= self.gross_mad:
            raise ValueError("commission must be within gross")
