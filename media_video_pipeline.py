"""Offline ten-scene Media Spider production packet.

No provider is invoked, no credits consumed and publishing stays disabled.
"""
from __future__ import annotations
import json
from pathlib import Path

SCENES = 10
PROMPT = """أنت كاتب ومخرج لقناة Nexa Stories. استخدم القصة الأصلية التالية فقط.
لا تغير أسماء الشخصيات أو أحداثها الجوهرية أو نهايتها. إذا نقصت معلومة، ضعها في
source_gaps ولا تخترعها. حافظ على هوية المكان والدارجة حيث استعملها الكاتب.

العنوان: {title}
القصة الأصلية: {story}

أخرج JSON صالحا: title, logline, source_gaps, character_bible (هيئة وملابس ثابتة
لكل شخصية), location_bible, continuity_rules, scenes. أخرج عشر مشاهد S01-S10.
لكل مشهد: scene_id, heading, story_beat, characters, location, duration_seconds,
narration_ar, dialogue_ar, image_prompt_en, motion_prompt_en, camera, sound_cues,
continuity_from_previous. image_prompt_en يصف صورة 16:9 صالحة للاقتطاع 9:16
من دون نص داخل الصورة؛ motion_prompt_en يصف حركة كاميرا وشخصيات بسيطة بلا تغيير
الوجوه والملابس. التعليق الصوتي بالعربية، النهاية تطابق الأصل، لا تدع أنها وقائع
حقيقية، ولا تستعمل أصواتا أو موسيقى أو شخصيات محمية بلا ترخيص.
"""
PROVIDERS = {
    "script": "manual AI chat or existing provider adapter",
    "flow": "manual Android browser, verify free credits/model/region/account",
    "vibes": "manual Android browser only; commercial rights unverified",
    "elevenlabs_free": "noncommercial demo only, never publish as commercial",
    "voice": "original phone recording or verified commercially licensed voice",
    "editor": "CapCut Android with licensed assets only",
}

def build_packet(title: str, story: str, *, story_source: str, story_owner_confirmed: bool = False) -> dict:
    if not title.strip() or not story_source.strip() or len(story.strip()) < 300 or not story_owner_confirmed:
        raise ValueError("Complete original user-owned story, title, and provenance required")
    return {"contract_version": "media.video.v1", "title": title.strip(),
            "story_source": story_source.strip(), "scene_count": SCENES,
            "prompt": PROMPT.format(title=title.strip(), story=story.strip()),
            "providers": PROVIDERS, "rights_status": "unreviewed", "publish_allowed": False}

def validate_scenes(scenes: list[dict]) -> None:
    fields = ("heading", "story_beat", "characters", "location", "duration_seconds",
              "narration_ar", "image_prompt_en", "motion_prompt_en")
    if len(scenes) != SCENES:
        raise ValueError("Exactly ten scenes required")
    for i, scene in enumerate(scenes, 1):
        if scene.get("scene_id") != f"S{i:02d}" or any(not scene.get(x) for x in fields):
            raise ValueError(f"Missing or out-of-order scene {i}")
        if not isinstance(scene["duration_seconds"], (int, float)) or scene["duration_seconds"] <= 0:
            raise ValueError(f"Invalid duration in scene {i}")

def assess_assets(scenes: list[dict], assets: list[dict]) -> dict:
    validate_scenes(scenes)
    needed = {f"S{i:02d}:{kind}" for i in range(1,11) for kind in ("image", "clip")}
    needed |= {"narration", "final_cut"}
    seen, problems = set(), []
    for item in assets:
        key = item.get("key", "")
        if key in seen: problems.append(f"duplicate:{key}")
        seen.add(key)
        if not all(item.get(k) for k in ("path", "source", "license_evidence")):
            problems.append(f"missing_evidence:{key}")
        if item.get("commercial_use") is not True or item.get("provider") == "elevenlabs_free":
            problems.append(f"commercial_rights_unverified:{key}")
    problems += [f"missing:{key}" for key in sorted(needed-seen)]
    return {"draft_ready": not problems, "publish_allowed": False, "problems": problems}

def save_packet(packet: dict, path: str | Path) -> None:
    # Save privately, never in the public GitHub repository.
    Path(path).write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
