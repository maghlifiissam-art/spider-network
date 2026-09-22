"""Versioned, fail-closed contracts for the Publish Spider subnetwork (publish.v1).

The Publish Spider is the explicit, separate publish action that README_MEDIA.md
keeps outside the media module. It receives:
  - content   from the Media Spider (media.v1 handoff: final video paths, title)
  - campaign instructions from Bullet / Sales / closing agents (publish_job)
and returns a typed publish_receipt per platform so the Sales Spider and the
deal-closing agent can track where each product/video is live.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Literal

CONTRACT_VERSION = "publish.v1"
Platform = Literal["youtube", "facebook", "instagram", "tiktok"]
PLATFORMS: tuple[str, ...] = ("youtube", "facebook", "instagram", "tiktok")
ReceiptStatus = Literal["draft_ready", "published", "pending_audit", "skipped", "failed", "dry_run"]
Sender = Literal["media_spider", "bullet_spider", "sales_spider", "closing_spider", "user", "other"]


def _iso(ts: str) -> None:
    datetime.fromisoformat(ts.replace("Z", "+00:00"))


@dataclass
class PublishJob:
    """One publishing order. Created from a Media Spider handoff plus campaign
    instructions from the Bullet/Sales/closing agents."""
    job_id: str
    run_id: str                      # media.v1 run_id this content came from
    video_path: str
    title: str
    description: str
    platforms: list[str]
    sender: Sender = "media_spider"
    campaign_id: str = ""            # sales/bullet campaign this publish serves
    source_brief_id: str = ""        # bullet production brief reference
    product_sku: str = ""            # optional: product being promoted
    utm_campaign: str = ""           # optional: link tracking for sales follow-up
    hashtags: list[str] = field(default_factory=list)
    thumbnail_path: str = ""
    scheduled_at: str = ""           # optional ISO datetime; empty = publish now
    contract_version: str = CONTRACT_VERSION
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def validate(self) -> None:
        if self.contract_version != CONTRACT_VERSION:
            raise ValueError("unsupported publish contract")
        if not self.job_id or not self.run_id:
            raise ValueError("job_id and run_id required")
        if not self.video_path or not self.title:
            raise ValueError("video_path and title required")
        unknown = [p for p in self.platforms if p not in PLATFORMS]
        if unknown:
            raise ValueError(f"unknown platforms: {unknown}")
        if not self.platforms:
            raise ValueError("at least one platform required")
        if self.scheduled_at:
            _iso(self.scheduled_at)
        for tag in self.hashtags:
            if tag.startswith("#") or " " in tag:
                raise ValueError(f"hashtag must be bare word, got: {tag}")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass
class PublishReceipt:
    """One result per platform. Returned to the Sales/closing agents and ops_log."""
    job_id: str
    platform: Platform
    status: ReceiptStatus
    detail: str = ""
    url: str = ""                    # public or studio URL when known
    privacy_state: str = ""          # e.g. private/public/draft
    campaign_id: str = ""
    contract_version: str = CONTRACT_VERSION
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    published_at: str = ""

    def validate(self) -> None:
        if self.contract_version != CONTRACT_VERSION:
            raise ValueError("unsupported publish contract")
        if not self.job_id:
            raise ValueError("job_id required")
        if self.platform not in PLATFORMS:
            raise ValueError(f"unknown platform: {self.platform}")
        if self.url and not self.url.startswith(("https://", "http://")):
            raise ValueError("receipt url must be a URL")
        if self.published_at:
            _iso(self.published_at)

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass(frozen=True)
class PublishPolicy:
    """Fail-closed publishing policy. Nothing posts unless dry_run is False AND
    the platform is enabled AND its credentials exist in the environment."""
    dry_run: bool = True
    enabled_platforms: tuple[str, ...] = PLATFORMS
    youtube_privacy: str = "private"        # locked private until the YouTube API audit passes
    tiktok_mode: str = "draft"              # draft inbox until TikTok approves direct post
    def allows(self, platform: str) -> bool:
        return platform in self.enabled_platforms
