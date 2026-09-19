#!/usr/bin/env python3
"""Background runner for the Spider Network (used by GitHub Actions or cron).

Runs the spiders on a task, appends results to data/spider_log.json and
optionally emails a report via Gmail (App Password).

Usage:
    python monitor.py --task "ملخص أداء هذا الأسبوع"
    python monitor.py --spiders affiliate,media --no-email
"""

from __future__ import annotations

import argparse
import json
import os
import smtplib
import sys
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path

from spiders.base import BaseSpider
from spiders import ALL_SPIDERS

LOG_PATH = Path(os.getenv("SPIDER_LOG_PATH", "data/spider_log.json"))
MAX_LOG_ENTRIES = 500


def load_log(path: Path = LOG_PATH) -> list:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def save_log(entries: list, path: Path = LOG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries[-MAX_LOG_ENTRIES:], ensure_ascii=False, indent=2),
                    encoding="utf-8")


def send_email(subject: str, body: str) -> tuple[bool, str]:
    user = os.getenv("GMAIL_USER")
    password = os.getenv("GMAIL_APP_PASSWORD")
    recipient = os.getenv("RECIPIENT_EMAIL") or user
    if not (user and password and recipient):
        return False, "Email secrets missing (GMAIL_USER / GMAIL_APP_PASSWORD / RECIPIENT_EMAIL)"
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = recipient
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(user, password)
            server.send_message(msg)
        return True, f"Email sent to {recipient}"
    except Exception as exc:
        return False, f"Email failed: {exc}"


def run_cycle(task: str, spider_names: list[str] | None = None) -> list[dict]:
    names = spider_names or list(ALL_SPIDERS)
    results = []
    for name in names:
        cls = ALL_SPIDERS.get(name)
        if not cls:
            print(f"⚠️ Unknown spider '{name}' — skipped", file=sys.stderr)
            continue
        spider: BaseSpider = cls()
        print(f"🕷️ Running {spider.title} ...")
        result = spider.run(task)
        status = "✅" if result.ok else f"❌ {result.error}"
        print(f"   {status} ({result.elapsed_seconds}s)")
        results.append(result.to_dict())
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Spider Network background runner")
    parser.add_argument("--task", default="أنشئ تقرير أداء أسبوعي موجز "
                        "(فرص، ترندات، اقتراحات تنفيذية) لتخصصك.")
    parser.add_argument("--spiders", default=",".join(ALL_SPIDERS),
                        help="Comma-separated spider names (default: all)")
    parser.add_argument("--no-email", action="store_true")
    parser.add_argument("--log-path", default=str(LOG_PATH))
    args = parser.parse_args()

    names = [n.strip() for n in args.spiders.split(",") if n.strip()]

    cycle_entries = run_cycle(args.task, names)

    log_path = Path(args.log_path)
    log = load_log(log_path)
    log.append({
        "cycle": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": args.task,
        "results": cycle_entries,
    })
    save_log(log, log_path)
    print(f"📝 Log updated: {log_path}")

    if not args.no_email:
        ok_spiders = [r["spider"] for r in cycle_entries if r["ok"]]
        body = f"🕷️ Spider Network Report\n\nTask: {args.task}\n\n"
        for entry in cycle_entries:
            body += f"--- {entry['spider']} ({'OK' if entry['ok'] else 'FAILED'}) ---\n"
            body += entry["output"] or entry["error"]
            body += "\n\n"
        sent, info = send_email(
            f"🕷️ Spider Report [{','.join(ok_spiders) or 'none'}]", body
        )
        print(("📧 " + info) if sent else ("⚠️ " + info))

    failed = [e for e in cycle_entries if not e["ok"]]
    return 1 if failed and not cycle_entries else 0


if __name__ == "__main__":
    sys.exit(main())
