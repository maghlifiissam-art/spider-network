"""
blog_spider.py - عنكبوت التدوينات (RSS مجاني)
-----------------------------------------------
كيقرا خلاصات RSS عمومية مجانية، كيختار خبر جديد ما تكتبش عليه من قبل،
وكيكتب تدوينة بكلماته الخاصة (ماشي نسخ) مع اسم المصدر والرابط.
كل تدوينة كتتحفظ كمسودة فـ blog/drafts/ وكتستنى المراجعة. ما كاين نشر تلقائي.
بلا NewsAPI، بلا مصاريف.
"""
import datetime
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

import requests

MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
DRAFTS_DIR = os.path.join(os.path.dirname(__file__), "blog", "drafts")
SEEN_FILE = os.path.join(os.path.dirname(__file__), "blog", "seen.json")

# خلاصات عمومية مجانية (تقنية / ذكاء اصطناعي / عمل رقمي)
FEEDS = [
    ("BBC Technology", "https://feeds.bbci.co.uk/news/technology/rss.xml"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
    ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ("Hacker News (front page)", "https://hnrss.org/frontpage?points=150"),
]
UA = {"User-Agent": "SpiderNetworkBlog/1.0 (+https://github.com/maghlifiissam-art/spider-network)"}


def _text(el, tag):
    for child in el:
        if child.tag.split("}")[-1] == tag:
            return (child.text or "").strip()
    return ""


def _link(el):
    for child in el:
        if child.tag.split("}")[-1] == "link":
            return (child.text or child.attrib.get("href") or "").strip()
    return ""


def fetch_items(limit_per_feed: int = 8) -> list:
    items = []
    for name, url in FEEDS:
        try:
            r = requests.get(url, headers=UA, timeout=20)
            r.raise_for_status()
            root = ET.fromstring(r.content)
        except Exception as e:  # feed واحد ماخدامش ما يوقفش الباقي
            print(f"skip {name}: {e}", file=sys.stderr)
            continue
        entries = [e for e in root.iter() if e.tag.split("}")[-1] in ("item", "entry")]
        for e in entries[:limit_per_feed]:
            title = _text(e, "title")
            link = _link(e)
            desc = re.sub(r"<[^>]+>", " ", _text(e, "description") or _text(e, "summary"))
            desc = re.sub(r"\s+", " ", desc).strip()[:600]
            if title and link:
                items.append({"source": name, "title": title, "url": link, "summary": desc})
    return items


def load_seen() -> set:
    try:
        return set(json.load(open(SEEN_FILE)))
    except Exception:
        return set()


def save_seen(seen: set) -> None:
    os.makedirs(os.path.dirname(SEEN_FILE), exist_ok=True)
    json.dump(sorted(seen)[-500:], open(SEEN_FILE, "w"), ensure_ascii=False, indent=0)


def write_post(item: dict, language: str = "العربية") -> str:
    from groq import Groq
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    system = f"""You are a careful blogger writing in {language} (simple Moroccan-friendly Modern Standard Arabic).
Write a short blog post (350-500 words) about the news item below, based STRICTLY on the title and summary given.
Rules:
- Do NOT invent facts, numbers, quotes or details that are not in the item.
- Use your own words. Never copy sentences from the source.
- Name the source in the text ("According to {item['source']}...").
- Structure: a title line starting with '# ', a short intro, 2 short sections with '## ' headers, a one-paragraph takeaway for a small entrepreneur.
- End with a 'المصدر / Source' line with the source name and URL.
If the item gives too little detail, write a shorter post and say that details are limited."""
    user = f"Source: {item['source']}\nTitle: {item['title']}\nSummary: {item['summary']}\nURL: {item['url']}"
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.5,
        max_tokens=1500,
    )
    return resp.choices[0].message.content.strip()


def main() -> int:
    items = fetch_items()
    seen = load_seen()
    fresh = [i for i in items if i["url"] not in seen]
    print(f"{len(items)} items, {len(fresh)} new")
    if not fresh:
        return 0
    if "--dry-run" in sys.argv:
        for i in fresh[:5]:
            print("-", i["source"], "|", i["title"])
        return 0
    item = fresh[0]
    body = write_post(item)
    day = datetime.date.today().isoformat()
    slug = re.sub(r"[^a-z0-9]+", "-", item["title"].lower()).strip("-")[:50] or "post"
    os.makedirs(DRAFTS_DIR, exist_ok=True)
    path = os.path.join(DRAFTS_DIR, f"{day}-{slug}.md")
    header = f"<!-- status: DRAFT (needs review) | source: {item['source']} | url: {item['url']} -->\n\n"
    open(path, "w", encoding="utf-8").write(header + body + "\n")
    seen.add(item["url"])
    save_seen(seen)
    print("draft:", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
