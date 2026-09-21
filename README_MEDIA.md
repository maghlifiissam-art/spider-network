# Media Spider — Nexa Stories

`media.v1` is an independent, fail-closed story/film subnetwork routed by `domain: media`. Its leaders are Trend Scout, Story Writer, independent Continuity/Fact Checker, Visual Director, Voice & Sound, Editor, and rights/quality QA. Handoffs are typed and versioned; trend/history claims require `source_url`, `confidence`, and `observed_at`.

Defaults are offline, deterministic and zero-cost. Provider adapters are replaceable; no phone app is a dependency. Missing rights, evidence or visual continuity returns `no_go`. The spider never enables publishing: first-user review and a later explicit publish action stay outside this module.

Run: `python -m unittest tests/test_media_spider.py -v`. Streamlit page: `pages/9_Media_Spider.py`.
