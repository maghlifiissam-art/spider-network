"""Platform-evolution track: every cycle adopt ONE new free capability into RIMAZ.

State machine per backlog item (dev_team/evolution_backlog.json):
  candidate -> evaluated -> approved -> built -> verified -> shipped   (or rejected)
Gates (an item cannot advance without passing them):
  free_tier_only   no card, no paid plan, no recurring cost
  no_secrets_in_repo
  low_data_ok      must not hurt the Morocco low-data requirement
  measurable       names the metric it should move (read from measure/analyze loop)
  testable         has a check that can run in CI or on the live site
`pick_next` returns the highest-scoring approved/evaluated item; the weekly run builds it,
a verification step checks its metric 7 days later and marks it keep/revert.
"""
import json
from pathlib import Path

BACKLOG = Path(__file__).parent / "evolution_backlog.json"
GATES = ("free_tier_only", "no_secrets_in_repo", "low_data_ok", "measurable", "testable")


def score(item):
    gates_ok = all(item.get("gates", {}).get(g) for g in GATES)
    if not gates_ok:
        return -1
    return item.get("impact", 1) * 2 + item.get("effort_inverse", 1)  # 1-5 each


def pick_next(items=None):
    items = items if items is not None else json.loads(BACKLOG.read_text(encoding="utf-8"))["items"]
    ready = [i for i in items if i["state"] in ("evaluated", "approved") and score(i) > 0]
    return max(ready, key=score) if ready else None


def verify(item, metric_before, metric_after, min_lift=0.0):
    """After shipping: keep only if the named metric did not drop."""
    return "keep" if metric_after >= metric_before * (1 + min_lift) else "revert"


if __name__ == "__main__":
    n = pick_next()
    print(n["id"] if n else "none ready")
