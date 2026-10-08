# Automatic Development Team (v1)

Closed loop: measure -> analyze -> guide, plus a platform-evolution track.

- `measure.py`   reads public posts + `post_counts` view (public anon key, no secrets), appends to `data/history.jsonl`.
- `analyze.py`   scores posts, groups by format / topic / title shape / length / number / posting hour, shrinks small groups toward the mean, writes `insights/latest.json` and `insights/content_guidance.md`. No recommendations until 30 learnable posts; a "winner" needs 5+ posts and a 15% lead.
- `guidance.py`  `load_guidance()` for content spiders; returns a prompt snippet.
- `platform_evolution.py` + `evolution_backlog.json`: one new free capability per cycle, gated (free tier, no secrets, low-data, measurable, testable), verified after shipping (keep/revert).
- Loop: `.github/workflows/dev-team.yml` every 6 h, commits data back to main. No human input.

Known gap (v2): watch time / completion is not stored yet. See backlog item `watch-signals`.

## v1.1 funnel (target: 1000 publishing creators)

`measure.py` also appends one snapshot per run to `data/funnel.jsonl`; `analyze.py` writes `insights/funnel.json` (latest, change since previous run, progress vs 1000, activation rate).
Three distinct counts:
1. `registered_accounts` - needs optional CI secret `RIMAZ_SB_SERVICE` (auth.users is not public). Without it the value is `null` (unknown), never guessed. Not a public counter.
2. `publishing_creators` - **activation rule: an account owning a channel with >=1 published, non-sponsored, non-pinned post, excluding platform-owned channels** (spider channel, demo seed). Public data only.
3. `viewer` - views, likes, comments, reactions, posts total / by outside creators, views on outside creators' posts. Public data only.
