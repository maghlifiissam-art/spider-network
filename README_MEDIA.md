# Media Spider - Nexa Stories

`media.v1` is an offline, fail-closed story/film subnetwork. Its seven stages are Trend Scout, Story Writer, Continuity/Fact Checker, Visual Director, Voice & Sound, Editor, and Rights QA. Publishing remains disabled in this module. The original offline pilot and Director Spider remain available.

Run: `python3 -m unittest tests/test_media_spider.py tests/test_media_video_pipeline.py -v`.

## Ten-scene video production packet (`media.video.v1`)

`media_video_pipeline.py` prepares a private Arabic ten-scene script-generation mega-prompt from a **complete user-owned story**. Call `build_packet(title, full_story, story_source=..., story_owner_confirmed=True)` and save the packet **outside the public repository**. A mere premise is refused. Compare model output against the original: it must not invent an ending. `validate_scenes()` checks ordered S01-S10 cards; `assess_assets()` checks image, clip, narration and final-cut evidence, fails closed on missing commercial rights, and never enables publishing. The module does not call external providers or generate a final video.

### Phone-first handoff

1. Copy the prompt to an available AI chat on Android, save the ten-scene JSON privately, and compare all events, characters and ending with the original story.
2. In Google Flow on the phone browser, **if the account, region, model and free credits allow**, generate fixed character/place references before scene images; save the images on the phone. Flow's web/mobile feature sets may differ.
3. Animate images one by one in a commercially licensed tool available on the phone and save clips locally. Meta Vibes and the third-party Vibes Automation extension have unverified commercial rights and account/security impact here, so are not automated. A browser extension is **not required**. Do not rely on Kiwi: its project was archived in January 2025.
4. Record the creator's original Arabic narration with the phone recorder or use a verified commercially licensed free voice. ElevenLabs Free is noncommercial, so it is demo-only, not for monetized Nexa Stories.
5. Import clips and narration into CapCut Android. Use original/approved sounds only; check each template, stock asset and music license. Export a review cut and inspect actual frames, Arabic text, character continuity and ending before any separate publish action.

Tutorial claims are not provider terms: Google Flow says 50 free credits/day with no subscription (not unlimited), with model-specific costs. ElevenLabs says Free has 10,000 characters/month and no commercial license, not the tutorial's 100,000. CapCut's asset licenses vary. No Meta Vibes commercial grant was established. Check these again against the actual user account and output before a real clip or publication. Nothing here requires a Windows laptop, but mobile access to particular Flow models has not been verified.

Sources: https://support.google.com/flow/answer/16526234 ; https://labs.google/fx/faq ; https://elevenlabs.io/docs/eleven-creative/quickstart ; https://elevenlabs.io/docs/help-center/legal/can-i-publish-the-content-i-generate-on-the-platform ; https://www.capcut.com/clause/material-license-agreement?lang=en ; https://github.com/kiwibrowser/src.next ; https://chromewebstore.google.com/detail/vibes-automation-auto-met/mikmoieklgpbgikeemkfffncmcmnhhab .
