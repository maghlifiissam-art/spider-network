# Automatic Development Team (v1)

Closed loop: measure -> analyze -> guide, plus a platform-evolution track.

- `measure.py`   reads public posts + `post_counts` view (public anon key, no secrets), appends to `data/history.jsonl`.
- `analyze.py`   scores posts, groups by format / topic / title shape / length / number / posting hour, shrinks small groups toward the mean, writes `insights/latest.json` and `insights/content_guidance.md`. No recommendations until 30 learnable posts; a "winner" needs 5+ posts and a 15% lead.
- `guidance.py`  `load_guidance()` for content spiders; returns a prompt snippet.
- `platform_evolution.py` + `evolution_backlog.json`: one new free capability per cycle, gated (free tier, no secrets, low-data, measurable, testable), verified after shipping (keep/revert).
- Loop: `.github/workflows/dev-team.yml` every 6 h, commits data back to main. No human input.

Known gap (v2): watch time / completion is not stored yet. See backlog item `watch-signals`.
