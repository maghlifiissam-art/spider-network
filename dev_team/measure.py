"""Measurement spider: snapshot per-post performance from the live RIMAZ platform.

Reads only public data (posts + the public post_counts view) with the public
anon key that already ships in the web client. No secrets. Zero cost.
Appends one row per post per run to dev_team/data/history.jsonl so velocity
(views gained between runs) can be computed later.
"""
import json, os, sys, urllib.request, datetime as dt
from pathlib import Path

BASE = os.environ.get("RIMAZ_SB_URL", "https://eyasbfywyatrkpkljxek.supabase.co")
KEY = os.environ.get("RIMAZ_SB_ANON", "sb_publishable_1hlN6DuTPcl-rCJufPHBZw_gAr502Jq")  # public anon key
DATA = Path(__file__).parent / "data"
PINNED_PREFIXES = ("7f3e348e", "07fdc522")  # pinned promos: reported, excluded from learning


def _get(path):
    req = urllib.request.Request(f"{BASE}/rest/v1/{path}", headers={"apikey": KEY})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch():
    posts = _get("posts?select=id,kind,topic,title,is_sponsored,created_at,series_id,channel_id,views,comments_off&order=created_at.desc&limit=1000")
    counts = {c["post_id"]: c for c in _get("post_counts?select=*&limit=5000")}
    rows = []
    for p in posts:
        c = counts.get(p["id"], {})
        rows.append({
            "id": p["id"], "kind": p["kind"], "topic": p["topic"], "title": p.get("title") or "",
            "sponsored": bool(p["is_sponsored"]), "pinned": p["id"].startswith(PINNED_PREFIXES),
            "created_at": p["created_at"], "series": bool(p.get("series_id")),
            "views": c.get("views", p.get("views", 0)) or 0, "likes": c.get("likes", 0) or 0,
            "comments": c.get("comments", 0) or 0, "reactions": c.get("reactions", 0) or 0,
        })
    return rows


def run(now=None, rows=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    rows = fetch() if rows is None else rows
    DATA.mkdir(exist_ok=True)
    with open(DATA / "history.jsonl", "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({"t": now.isoformat(timespec="seconds"), **r}, ensure_ascii=False) + "\n")
    return len(rows)


if __name__ == "__main__":
    print(f"measured {run()} posts")
