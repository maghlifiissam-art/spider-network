"""Hook for content spiders: read what the Development Team learned.

    from dev_team.guidance import load_guidance
    g = load_guidance()          # {"status": "collecting"|"ready", "prefer": {"title_question": "question", ...}}
    prompt += g["prompt_snippet"]  # drop into any title/hook-writing prompt

Safe by default: when data is insufficient, returns no preferences and asks for variation
(so the loop still generates informative data).
"""
import json
from pathlib import Path

LATEST = Path(__file__).parent / "insights" / "latest.json"


def load_guidance(path=LATEST):
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {"status": "collecting", "winners": []}
    prefer = {w["feature"]: w["value"] for w in d.get("winners", [])} if d.get("status") == "ready" else {}
    if prefer:
        snippet = "Data from past performance shows these work best on RIMAZ: " + "; ".join(f"{k}={v}" for k, v in prefer.items()) + ". Follow them unless the topic clearly demands otherwise."
    else:
        snippet = "No proven pattern yet: vary title shape (question vs statement), length and posting hour across posts so performance data becomes informative."
    return {"status": d.get("status", "collecting"), "prefer": prefer, "prompt_snippet": snippet}
