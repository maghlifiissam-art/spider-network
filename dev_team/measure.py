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
            "channel_id": p.get("channel_id"), "created_at": p["created_at"], "series": bool(p.get("series_id")),
            "views": c.get("views", p.get("views", 0)) or 0, "likes": c.get("likes", 0) or 0,
            "comments": c.get("comments", 0) or 0, "reactions": c.get("reactions", 0) or 0,
        })
    return rows


# v1.1 funnel: three distinct counts, tracked over time in data/funnel.jsonl.
# Platform-owned channels (spider channel, demo seed) never count as outside creators.
PLATFORM_OWNERS = {"0cfc1fa7-bb64-44a8-92b9-4863d98409df",   # nexastory (platform spider channel)
                   "5d3e0000-0000-4000-8000-00000000d3a0"}   # rimazdemo (seed)
ACTIVATION_MIN_POSTS = 1   # "publishing creator" = non-platform account owning a channel with >=1 published, non-sponsored, non-pinned post


def fetch_registered():
    """Registered accounts. auth.users is not public, so this needs the optional admin
    key (env RIMAZ_SB_SERVICE, a CI secret, never in the repo). Without it: None (unknown), never a guess."""
    svc = os.environ.get("RIMAZ_SB_SERVICE")
    if not svc:
        return None
    req = urllib.request.Request(f"{BASE}/auth/v1/admin/users?page=1&per_page=1", headers={"apikey": svc, "Authorization": f"Bearer {svc}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return int(r.headers.get("x-total-count") or json.load(r).get("total"))
    except Exception:
        return None


def funnel(rows, registered=None, channels=None):
    """Pure function: rows from fetch() (+channel_id) -> funnel snapshot."""
    own = [r for r in rows if not r["sponsored"] and not r["pinned"]]
    per_channel = {}
    for r in own:
        per_channel[r.get("channel_id")] = per_channel.get(r.get("channel_id"), 0) + 1
    channels = channels or {}
    creators = {channels.get(cid, cid) for cid, n in per_channel.items() if n >= ACTIVATION_MIN_POSTS}
    creators -= PLATFORM_OWNERS
    outside = [r for r in own if channels.get(r.get("channel_id"), r.get("channel_id")) not in PLATFORM_OWNERS]
    return {
        "registered_accounts": registered,
        "publishing_creators": len(creators),
        "activation_rule": f">={ACTIVATION_MIN_POSTS} published non-sponsored non-pinned post, excluding platform-owned channels",
        "viewer": {
            "views": sum(r["views"] for r in rows), "likes": sum(r["likes"] for r in rows),
            "comments": sum(r["comments"] for r in rows), "reactions": sum(r["reactions"] for r in rows),
            "posts_total": len(rows), "posts_by_outside_creators": len(outside),
            "views_on_outside_creators": sum(r["views"] for r in outside),
        },
    }


def run_funnel(now=None, rows=None, registered="auto", channels=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    rows = fetch() if rows is None else rows
    if channels is None:
        channels = {c["id"]: c["owner_id"] for c in _get("channels?select=id,owner_id&limit=5000")}
    reg = fetch_registered() if registered == "auto" else registered
    snap = {"t": now.isoformat(timespec="seconds"), **funnel(rows, reg, channels)}
    DATA.mkdir(exist_ok=True)
    with open(DATA / "funnel.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(snap, ensure_ascii=False) + "\n")
    return snap


def run(now=None, rows=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    rows = fetch() if rows is None else rows
    DATA.mkdir(exist_ok=True)
    with open(DATA / "history.jsonl", "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({"t": now.isoformat(timespec="seconds"), **r}, ensure_ascii=False) + "\n")
    return len(rows)


if __name__ == "__main__":
    _rows = fetch()
    print(f"measured {run(rows=_rows)} posts")
    print("funnel", json.dumps(run_funnel(rows=_rows), ensure_ascii=False))
