"""
opportunity_spider.py - صائد المكافآت
Reads free public sources (Devpost open hackathons API, fundsforNGOs RSS),
keeps remote-friendly entries with prizes, writes a daily digest to
opportunities/YYYY-MM-DD.md and tracks seen items. Report-only: no sign-ups,
no submissions, no spend. A human reviews every entry before acting.
"""
import datetime, json, os, re, xml.etree.ElementTree as ET
import requests

BASE = os.path.dirname(__file__)
OUT = os.path.join(BASE, "opportunities")
SEEN = os.path.join(OUT, "seen.json")
UA = {"User-Agent": "SpiderNetworkOpportunities/1.0 (+https://github.com/maghlifiissam-art/spider-network)"}
TAG = re.compile(r"<[^>]+>")


def devpost():
    r = requests.get("https://devpost.com/api/hackathons",
                     params={"status[]": "open", "order_by": "prize-amount"}, headers=UA, timeout=30)
    r.raise_for_status()
    for h in r.json().get("hackathons", []):
        loc = (h.get("displayed_location") or {}).get("location", "")
        if "online" not in loc.lower():
            continue
        prize = TAG.sub("", h.get("prize_amount") or "").strip()
        amt = int(re.sub(r"[^0-9]", "", prize) or 0)
        tier = "BIG" if amt >= 50000 else "MID" if amt >= 5000 else "SMALL"
        yield {"id": "dp-%s" % h["id"], "src": "Devpost", "title": h["title"], "url": h["url"],
               "tier": tier, "info": "prize %s | deadline %s" % (prize or "n/a", h.get("submission_period_dates", "n/a"))}


def fundsforngos():
    r = requests.get("https://www.fundsforngos.org/feed/", headers=UA, timeout=30)
    r.raise_for_status()
    for it in ET.fromstring(r.content).iter("item"):
        link = it.findtext("link") or ""
        yield {"id": link, "src": "fundsforNGOs", "title": it.findtext("title") or "", "url": link,
               "info": (it.findtext("pubDate") or "")}


def main():
    os.makedirs(OUT, exist_ok=True)
    seen = set(json.load(open(SEEN))) if os.path.exists(SEEN) else set()
    new = []
    for src in (devpost, fundsforngos):
        try:
            new += [x for x in src() if x["id"] not in seen]
        except Exception as e:
            print("source failed:", src.__name__, e)
    if not new:
        print("nothing new"); return
    day = datetime.date.today().isoformat()
    lines = ["# Opportunities %s" % day, "", "Review before acting. Eligibility and terms are unchecked.", ""]
    for x in new[:40]:
        lines.append("- [%s]%s %s - %s (%s)" % (x["src"], " " + x.get("tier", "GRANT"), x["title"], x["url"], x["info"]))
    open(os.path.join(OUT, day + ".md"), "w").write("\n".join(lines) + "\n")
    json.dump(sorted(seen | {x["id"] for x in new}), open(SEEN, "w"))
    print("wrote", len(new))


if __name__ == "__main__":
    main()
