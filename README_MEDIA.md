# Media Spider — Nexa Stories

`media.v1` is an independent, fail-closed story/film subnetwork routed by `domain: media`. Its leaders are Trend Scout, Story Writer, independent Continuity/Fact Checker, Visual Director, Voice & Sound, Editor, and rights/quality QA. Handoffs are typed and versioned; trend/history claims require `source_url`, `confidence`, and `observed_at`.

Defaults are offline, deterministic and zero-cost. Provider adapters are replaceable; no phone app is a dependency. Missing rights, evidence or visual continuity returns `no_go`. The spider never enables publishing: first-user review and a later explicit publish action stay outside this module.

Run: `python -m unittest tests/test_media_spider.py -v`. Streamlit page: `pages/9_Media_Spider.py`.

## Director Spider (directing.v1)

`director_spider.py` is the directing specialist for Nexa Stories, Funimal and other video channels. From a script
(`SCENE`/`INT.`/`EXT.`/`مشهد` headings, or paragraphs) or explicit scenes it builds a deterministic direction plan:
scene breakdown, shot list (size, angle, lens, movement, duration), rhythm (average shot length, cuts per minute by mood
and channel), lighting (style, contrast ratio, colour temperature, motivation), transitions with sound bridges, VFX cues,
sound design (music cue, ambience, SFX) and continuity rules. The first shot is a channel-specific hook.

Offline and zero-cost. Every music/SFX/footage asset must be `original`, `licensed`, `public_domain` or `generated_owned`
(licensed/public domain need a `source_url`), otherwise the plan is `no_go`. `publish_allowed` is always false.
`to_media_handoff(plan, run_id)` returns a `media.v1` handoff from `visual_director` to `editor`.

```bash
python3 director_spider.py script.txt --title "Sayf" --channel nexa_stories
python3 -m pytest tests/test_director_spider.py
```
