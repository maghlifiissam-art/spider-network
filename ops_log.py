"""
ops_log.py — سجل العمليات المشترك لكل خطوط الإنتاج
------------------------------------------------------------------
كل خط إنتاج (auto_publish_book, auto_publish_comic, auto_publish_coloring_book,
auto_publish_visual, boss_spider, monitor_spider) كيسجل فيه أي عملية درها
— نجحت ولا فشلات — باش لوحة التحكم تقدر تعرض تقرير شامل.
"""

import os
import json
from datetime import datetime, timezone

LOG_PATH = "data/ops_log.json"
LINES = ["book", "comic", "coloring_book", "poster", "logo", "marketing", "news_blog", "engineering", "electronics", "cloud", "monitor"]


def log_operation(line: str, status: str, message: str = "", product_name: str = "") -> None:
    """
    line: أحد LINES أعلاه
    status: "success" أو "failed"
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "line": line,
        "status": status,
        "message": message,
        "product_name": product_name,
    }
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    log = []
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            log = json.load(f)
    log.append(entry)
    log = log[-2000:]  # نبقاو غير آخر 2000 عملية باش الملف يبقى خفيف
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def load_log() -> list:
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def get_stats() -> dict:
    """يرجع dict: {line: {"success": n, "failed": n, "total": n}}"""
    log = load_log()
    stats = {line: {"success": 0, "failed": 0, "total": 0} for line in LINES}
    for entry in log:
        line = entry.get("line", "unknown")
        if line not in stats:
            stats[line] = {"success": 0, "failed": 0, "total": 0}
        stats[line]["total"] += 1
        if entry.get("status") == "success":
            stats[line]["success"] += 1
        else:
            stats[line]["failed"] += 1
    return stats


def get_recent(limit: int = 30) -> list:
    return list(reversed(load_log()[-limit:]))
