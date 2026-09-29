"""Daily source-backed discovery. No publication, outreach, purchase, or private data."""
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import requests
from bullet_spider import MarketSpyHandoffAdapter, run_bullet_spider
from market_spy_spider import Signal, SourceUnavailable, build_report, google_trends_signals

# Themes are research hypotheses, not product picks. Wikipedia readership is GLOBAL,
# not US buyer activity, and is never used to claim local demand or sales.
THEMES = (
    ("employment law", "ebook", "Employment_law"),
    ("small business", "ebook", "Small_business"),
    ("software development", "digital_product", "Software_development"),
    ("design tools", "digital_product", "Graphic_design"),
)
USER_AGENT = "SpiderNetwork-MarketSpy/1.0 (https://github.com/maghlifiissam-art/spider-network)"


def wikipedia_readership(title, fetch=requests.get, today=None):
    """One official Wikimedia public aggregate endpoint call per theme, no retries."""
    today = today or datetime.now(timezone.utc).date()
    end = today - timedelta(days=2)  # completed data, with one-day lag
    start = end - timedelta(days=13)
    url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
           f"en.wikipedia.org/all-access/user/{quote(title, safe='')}/daily/"
           f"{start:%Y%m%d}/{end:%Y%m%d}")
    try:
        response = fetch(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, timeout=15)
    except requests.RequestException as exc:
        raise SourceUnavailable(f"Wikimedia network error: {exc}") from exc
    if response.status_code != 200:
        raise SourceUnavailable(f"Wikimedia HTTP {response.status_code}; stopped without retry")
    items = response.json().get("items", [])
    views = [item["views"] for item in items if isinstance(item.get("views"), int)]
    if len(views) != 14:
        raise SourceUnavailable("Wikimedia returned incomplete two-week data")
    # Show both weeks, but do not manufacture commercial growth from them.
    return Signal(
        product=title.replace("_", " "), source_name="Wikimedia Analytics pageviews",
        source_url=url, observed_at=datetime.now(timezone.utc).isoformat(),
        geography="global", metric="English Wikipedia article views (last seven complete days)",
        value=float(sum(views[7:])), unit="article views", is_proxy=True, confidence=0.45,
        limitations=(f"Previous seven complete days: {sum(views[:7])} views; readership change is not buyer intent.",
                     "English Wikipedia audience is global, not US-specific; article views are not product searches, sales, or revenue.",
                     "A preselected research theme is not proof of product-market fit."),
    )


def run(geography="US", themes=THEMES):
    geography = geography.upper()
    if len(geography) != 2 or not geography.isalpha():
        raise ValueError("geography must be a two-letter ISO country code")
    rows = []
    for query, category, article in themes:
        try:
            local = build_report(query, geography, google_trends_signals(query, geography), market_category=category)
        except (SourceUnavailable, ValueError) as exc:
            local = build_report(query, geography, [], [f"google_trends: {exc}"], market_category=category)
        try:
            global_report = build_report(query, "global", [wikipedia_readership(article)], market_category=category)
            global_error = None
        except (SourceUnavailable, ValueError, requests.RequestException) as exc:
            global_report = build_report(query, "global", [], market_category=category)
            global_error = str(exc)
        # Market Spy handoffs preserve factual no-go assessments. Experimental
        # briefs are separate and never claim verified product demand.
        bullet = run_bullet_spider({}, [MarketSpyHandoffAdapter(local), MarketSpyHandoffAdapter(global_report)], limit=10)
        rows.append({
            "theme": query, "category": category,
            "source_errors": local["source_errors"] + ([global_error] if global_error else []),
            "local_signals": local["signals"][:20],
            "global_language_proxy_signals": global_report["signals"][:5],
            "ranked_research_candidates": local["opportunities"][:10] + global_report["opportunities"][:5],
            "bullet_assessments": bullet["opportunities"],
            "draft_briefs": bullet["briefs"],
            "experimental_briefs": [experimental_brief(item, category) for item in
                                    global_report["opportunities"][:1]],
        })
    rows.sort(key=lambda row: -max((signal.get("value") or 0 for signal in row["global_language_proxy_signals"]), default=0))
    return {
        "requested_geography": geography, "observed_at": datetime.now(timezone.utc).isoformat(),
        "themes": rows,
        "disclaimer": "Global Wikipedia readership and public search proxies are not buyer intent, sales, or US demand. Experimental topic briefs may move quickly to rights/quality review, but are not verified winners. This workflow does not publish or target people.",
    }


def experimental_brief(candidate, category):
    """A fast research-to-production handoff, not evidence of purchase intent."""
    return {
        "topic": candidate["product"],
        "geography": candidate["geography"],
        "category": category,
        "source_urls": candidate["source_urls"],
        "metric_or_proxy": candidate["metric_or_proxy"],
        "evidence_label": "LOW CONFIDENCE: broad global informational readership only; no local product demand or sales evidence",
        "priority_basis": "relative article views within four preselected themes only, not likelihood of sales",
        "status": "experimental_production_handoff_requires_rights_and_quality_review",
        "instructions": "Narrow to an original useful product, check sources and rights, then publish through the approved product workflow if quality and legal review pass. Do not claim demand or sales proven by this signal.",
        "publish": False,
    }


def digest(report):
    lines = [f"# Market Spy + Bullet: {report['requested_geography']} research", "", report["disclaimer"], ""]
    for theme in report["themes"]:
        lines.append(f"## {theme['theme']} ({theme['category']})")
        lines.extend(f"- Source unavailable: {error}" for error in theme["source_errors"])
        if not theme["ranked_research_candidates"]:
            lines.append("- No source-backed research lead found. No demand claim.")
        for item in theme["ranked_research_candidates"][:5]:
            lines.append(f"- Research lead ({item['geography']}): {item['product']} | proxy score {item['opportunity_score']}/100 | {item['metric_or_proxy']} | {', '.join(item['source_urls'])}")
        for brief in theme["experimental_briefs"]:
            lines.append(f"- Experimental brief for production: {brief['topic']} | {brief['evidence_label']} | {brief['status']}")
        lines.append(f"- Bullet: {len(theme['bullet_assessments'])} factual no-go assessments, {len(theme['draft_briefs'])} fully qualified briefs; {len(theme['experimental_briefs'])} low-confidence briefs for rights/quality review. Nothing published here.")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--geography", default="US")
    parser.add_argument("--output", default="demand_report.json")
    args = parser.parse_args()
    report = run(args.geography)
    output = Path(args.output)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    digest_path = output.with_suffix(".md")
    digest_path.write_text(digest(report), encoding="utf-8")
    print(digest(report))


if __name__ == "__main__":
    main()
