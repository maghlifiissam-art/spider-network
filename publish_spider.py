"""
publish_spider.py — وكيل النشر (Publish Spider)
------------------------------------------------------------------
الوكيل اللي كيوصل إنتاج العناكب للناس. كياخد:
  - المحتوى من Media Spider (media.v1 handoff: الفيديو النهائي + العنوان)
  - تعليمات الحملة من Bullet / Sales / وكيل إغلاق الصفقات (publish.v1 job)
وكيرجع publish_receipt لكل منصة لوكلاء البيع (تتبع الروابط والعمولات)
ولسجل العمليات ops_log.

fail-closed بطبعو: dry_run=True افتراضياً، وكل منصة بلا credentials كترجع
إيصال "failed" واضح — ما كترفع والو وما كتطيحش السلسلة.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from publish_contracts import (CONTRACT_VERSION, PLATFORMS, PublishJob,
                               PublishPolicy, PublishReceipt)

try:
    from ops_log import log_operation
except ImportError:  # pragma: no cover
    def log_operation(line: str, status: str, message: str = "", product_name: str = "") -> None:
        pass

RECEIPTS_PATH = Path("data/publish_receipts.json")
DEFAULT_CONFIG = Path(__file__).resolve().parent / "config" / "publish.yaml"


def load_policy(config_path: str | os.PathLike | None = None) -> PublishPolicy:
    """كيقرا config/publish.yaml إلا كان، وإلا كيرجع السياسة الافتراضية (dry_run)."""
    path = Path(config_path) if config_path else DEFAULT_CONFIG
    if not path.exists():
        return PublishPolicy()
    try:
        import yaml  # optional; missing yaml = defaults
        cfg: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except ImportError:
        return PublishPolicy()
    if cfg.get("contract_version", CONTRACT_VERSION) != CONTRACT_VERSION:
        return PublishPolicy()
    platforms = tuple(p for p in cfg.get("enabled_platforms", PLATFORMS) if p in PLATFORMS)
    return PublishPolicy(
        dry_run=bool(cfg.get("dry_run", True)),
        enabled_platforms=platforms or PLATFORMS,
        youtube_privacy=str(cfg.get("youtube_privacy", "private")),
        tiktok_mode=str(cfg.get("tiktok_mode", "draft")),
    )


def _save_receipts(receipts: list[PublishReceipt], path: Path = RECEIPTS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict] = []
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
    existing.extend(r.to_dict() for r in receipts)
    path.write_text(json.dumps(existing[-2000:], ensure_ascii=False, indent=2), encoding="utf-8")


class PublishSpider:
    """القائد: كيوجه publish job واحد لكل المنصات المطلوبة وكيجمع الإيصالات."""

    def __init__(self, policy: PublishPolicy | None = None):
        self.policy = policy or PublishPolicy()

    def run_job(self, job_dict: dict[str, Any]) -> list[dict[str, Any]]:
        job = PublishJob(**{k: v for k, v in job_dict.items()
                            if k in PublishJob.__dataclass_fields__})
        job.validate()
        receipts: list[PublishReceipt] = []
        for platform in job.platforms:
            receipts.append(self._publish_one(job, platform))
        _save_receipts(receipts)
        for r in receipts:
            log_operation(
                "social_publish",
                "success" if r.status in ("published", "draft_ready", "dry_run") else "failed",
                f"{r.platform}: {r.status} - {r.detail}"[:300],
                product_name=job.title,
            )
        return [r.to_dict() for r in receipts]

    def _publish_one(self, job: PublishJob, platform: str) -> PublishReceipt:
        if not self.policy.allows(platform):
            return PublishReceipt(job.job_id, platform, "skipped",
                                  detail="platform disabled fـ config/publish.yaml",
                                  campaign_id=job.campaign_id)
        if self.policy.dry_run:
            return self._adapter(platform)(job, True)
        try:
            return self._adapter(platform)(job, False)
        except Exception as exc:  # adapter bug must never break the chain
            return PublishReceipt(job.job_id, platform, "failed",
                                  detail=f"adapter error: {exc}"[:500],
                                  campaign_id=job.campaign_id)

    def _adapter(self, platform: str):
        if platform == "youtube":
            from publishers import youtube_publisher
            return lambda job, dr: youtube_publisher.publish(
                job, privacy=self.policy.youtube_privacy, dry_run=dr)
        if platform == "facebook":
            from publishers import meta_publisher
            return lambda job, dr: meta_publisher.publish_facebook(job, dry_run=dr)
        if platform == "instagram":
            from publishers import meta_publisher
            return lambda job, dr: meta_publisher.publish_instagram(
                job, video_url=os.environ.get("PUBLISH_STAGING_VIDEO_URL", ""), dry_run=dr)
        if platform == "tiktok":
            from publishers import tiktok_publisher
            return lambda job, dr: tiktok_publisher.publish(
                job, mode=self.policy.tiktok_mode, dry_run=dr)
        raise ValueError(f"unknown platform: {platform}")


def job_from_media_handoff(handoff: dict[str, Any], job_id: str,
                           platforms: list[str] | None = None, **overrides) -> dict[str, Any]:
    """يبني publish job من media.v1 handoff (الربط Media -> Publish).
    كيتوقع payload فيه: video_path, title, description (واختياري hashtags)."""
    payload = handoff.get("payload", {})
    job = {
        "job_id": job_id,
        "run_id": handoff.get("run_id", ""),
        "video_path": payload.get("video_path", ""),
        "title": payload.get("title", ""),
        "description": payload.get("description", ""),
        "hashtags": payload.get("hashtags", []),
        "platforms": platforms or list(PLATFORMS),
        "sender": "media_spider",
    }
    job.update(overrides)
    return job
