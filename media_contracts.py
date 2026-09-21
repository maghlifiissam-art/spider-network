"""Versioned, fail-closed contracts for the Nexa Stories media subnetwork."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Literal

CONTRACT_VERSION = "media.v1"
Stage = Literal["trend_scout","story_writer","fact_checker","visual_director","voice_sound","editor","rights_qa"]

@dataclass(frozen=True)
class EvidenceClaim:
    claim_id: str
    text: str
    source_url: str
    confidence: float
    observed_at: str
    kind: Literal["historical","later_chronicle","literary","creative_dramatization"]
    def validate(self) -> None:
        if not self.source_url.startswith(("https://", "http://")): raise ValueError("claim source_url required")
        if not 0 <= self.confidence <= 1: raise ValueError("confidence must be 0..1")
        datetime.fromisoformat(self.observed_at.replace("Z", "+00:00"))

@dataclass
class MediaHandoff:
    run_id: str
    sender: Stage
    recipient: Stage
    payload_type: str
    payload: dict[str, Any]
    claims: list[EvidenceClaim] = field(default_factory=list)
    contract_version: str = CONTRACT_VERSION
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    def validate(self) -> None:
        if self.contract_version != CONTRACT_VERSION: raise ValueError("unsupported media contract")
        if not self.run_id or not self.payload_type: raise ValueError("run_id and payload_type required")
        for claim in self.claims: claim.validate()
    def to_dict(self) -> dict[str, Any]:
        self.validate(); return asdict(self)

@dataclass(frozen=True)
class QAGate:
    rights_manifest_complete: bool
    evidence_complete: bool
    character_consistency_pass: bool
    arabic_visual_inspection_pass: bool
    user_reviewed: bool
    publish_requested: bool = False
    def decision(self) -> Literal["go_draft", "no_go"]:
        # Publishing is intentionally never granted here. User review is a separate later gate.
        return "go_draft" if all((self.rights_manifest_complete, self.evidence_complete,
            self.character_consistency_pass, self.arabic_visual_inspection_pass)) else "no_go"
    @property
    def publish_allowed(self) -> bool: return False
