"""Director Spider (directing.v1): professional film/video direction plans, offline and zero-cost.

Turns a script or a list of scenes into a shooting/edit plan a human or a generation
pipeline can follow:

* scene breakdown (from a script with ``SCENE``/``INT.``/``EXT.``/``مشهد`` headings, or explicit scenes)
* per-scene shot list: shot size, camera angle, lens, movement, duration
* rhythm: average shot length and cut density matched to mood, genre and channel
* lighting plan: key style, contrast ratio, colour temperature, motivation
* transitions between scenes, VFX cues and sound design (SFX, ambience, music cue)
* continuity rules (180-degree line, eyeline, screen direction, character look)

Channel profiles cover Nexa Stories (cinematic Arabic storytelling) and Funimal
(short animal comedy). The plan is deterministic: the same input gives the same plan.
It never publishes, never calls paid services and never pulls copyrighted assets:
every sound/music cue must be original, licensed or public domain, or the plan is
marked ``no_go`` for that cue. Output can be handed to Media Spider as a
``media.v1`` handoff from ``visual_director`` to ``editor``.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from typing import Iterable

from media_contracts import MediaHandoff

CONTRACT_VERSION = "directing.v1"
ALLOWED_RIGHTS = ("original", "licensed", "public_domain", "generated_owned")

# ---------------------------------------------------------------- channel profiles
CHANNEL_PROFILES: dict[str, dict] = {
    "nexa_stories": {
        "label": "Nexa Stories - cinematic Arabic storytelling",
        "aspect_ratio": "9:16 (vertical master) with 16:9-safe framing",
        "fps": 24,
        "pace_factor": 1.0,
        "look": "filmic, warm earth tones, soft contrast, natural textures",
        "hook_seconds": 3,
        "language": "ar",
        "caption_style": "burned-in Arabic subtitles, lower third, RTL-safe margins",
    },
    "funimal": {
        "label": "Funimal - short animal comedy",
        "aspect_ratio": "9:16 vertical",
        "fps": 30,
        "pace_factor": 0.6,
        "look": "bright, saturated, high key, clean backgrounds",
        "hook_seconds": 1.5,
        "language": "ar",
        "caption_style": "bold pop captions with emoji-free text, centre-upper safe zone",
    },
    "default": {
        "label": "Generic short film",
        "aspect_ratio": "16:9",
        "fps": 24,
        "pace_factor": 1.0,
        "look": "neutral cinematic",
        "hook_seconds": 5,
        "language": "en",
        "caption_style": "optional subtitles",
    },
}

# ---------------------------------------------------------------- mood grammar
# Average shot length (seconds) before the channel pace factor, and the visual grammar per mood.
MOOD_GRAMMAR: dict[str, dict] = {
    "epic": {"asl": 4.0, "sizes": ["EWS", "WS", "MS", "LOW-ANGLE MCU"], "angle": "low angle", "lens": "24mm wide / 85mm hero close-ups",
             "movement": ["slow crane up", "dolly in", "static"], "lighting": ("hard key, backlit rim, haze", "8:1", 5600, "sun / fire"),
             "transition": "match cut", "music": "orchestral swell, low drums", "ambience": "wind, distant crowd"},
    "tense": {"asl": 2.2, "sizes": ["MCU", "CU", "ECU", "OTS"], "angle": "slight dutch / eye level", "lens": "50mm-85mm, shallow depth",
              "movement": ["slow push in", "handheld", "static"], "lighting": ("low key, single hard source, deep shadows", "16:1", 4300, "practical lamp / moonlight"),
              "transition": "hard cut", "music": "pulsing low strings, heartbeat rhythm", "ambience": "room tone, clock, breathing"},
    "sad": {"asl": 5.0, "sizes": ["WS", "MS", "CU"], "angle": "eye level / slightly high", "lens": "50mm, soft background",
            "movement": ["static", "slow dolly out"], "lighting": ("soft window key, cool fill", "4:1", 6500, "overcast window"),
            "transition": "slow dissolve", "music": "solo oud or piano, sparse", "ambience": "rain, soft wind"},
    "joyful": {"asl": 2.8, "sizes": ["WS", "MS", "MCU", "insert"], "angle": "eye level", "lens": "35mm",
               "movement": ["steadicam follow", "whip pan", "static"], "lighting": ("high key, soft large source", "2:1", 5000, "daylight"),
               "transition": "whip pan / J-cut", "music": "upbeat percussion, hand claps", "ambience": "market chatter, birds"},
    "comedic": {"asl": 1.6, "sizes": ["MS", "CU", "reaction CU", "insert"], "angle": "eye level (subject height)", "lens": "24mm-35mm for exaggeration",
                "movement": ["snap zoom", "static", "quick pan"], "lighting": ("high key, even", "2:1", 5600, "daylight"),
                "transition": "smash cut", "music": "playful pizzicato stings", "ambience": "light room tone"},
    "mysterious": {"asl": 3.6, "sizes": ["WS silhouette", "MS", "CU", "insert detail"], "angle": "high angle / through foreground", "lens": "35mm with foreground framing",
                   "movement": ["slow track sideways", "slow tilt", "static"], "lighting": ("low key, top light, volumetric haze", "12:1", 3800, "torch / lantern"),
                   "transition": "fade through black", "music": "drone, ney flute", "ambience": "wind in corridors, dripping water"},
    "calm": {"asl": 4.5, "sizes": ["EWS", "WS", "MS"], "angle": "eye level", "lens": "35mm",
             "movement": ["slow pan", "static"], "lighting": ("soft natural, golden hour", "2:1", 3500, "low sun"),
             "transition": "cross dissolve", "music": "soft pads, light strings", "ambience": "nature bed"},
    "action": {"asl": 1.3, "sizes": ["WS", "MS", "CU", "POV", "insert"], "angle": "varied low/high", "lens": "18-35mm wide, fast shutter",
               "movement": ["handheld", "tracking", "whip pan"], "lighting": ("contrasty, motivated hard light", "8:1", 5600, "sun / fire / practicals"),
               "transition": "cut on action", "music": "driving percussion", "ambience": "impacts, footsteps, crowd"},
}
MOOD_KEYWORDS = {
    "epic": ("battle", "army", "kingdom", "victory", "سيف", "جيش", "معركة", "انتصار", "ملك"),
    "tense": ("chase", "danger", "threat", "secret", "خطر", "مطاردة", "تهديد", "توتر"),
    "sad": ("death", "loss", "goodbye", "cry", "tears", "حزن", "موت", "فراق", "بكاء", "دموع"),
    "joyful": ("wedding", "celebrate", "party", "festival", "عرس", "فرح", "احتفال", "عيد"),
    "comedic": ("funny", "cat", "dog", "prank", "oops", "مضحك", "قط", "كلب", "مقلب"),
    "mysterious": ("night", "shadow", "cave", "unknown", "mystery", "ليل", "ظل", "كهف", "غموض", "لغز"),
    "action": ("fight", "run", "jump", "explosion", "قتال", "يجري", "قفز", "انفجار"),
    "calm": ("dawn", "garden", "sea", "sunrise", "فجر", "حديقة", "بحر", "هدوء"),
}
VFX_KEYWORDS = {
    ("fire", "flame", "نار", "حريق"): "fire/ember particles composited over plate; keep light interaction on faces",
    ("rain", "مطر", "storm", "عاصفة"): "rain layer + wet-surface grade; lightning flash synced to thunder SFX",
    ("sand", "desert", "رمل", "صحراء"): "blowing sand particles, heat-haze distortion on horizon",
    ("night", "ليل", "moon", "قمر"): "day-for-night grade (cool, -1.5 stops), moon glow",
    ("magic", "سحر", "jinn", "جن", "dream", "حلم"): "soft glow bloom, light-wrap, subtle chromatic aberration",
    ("battle", "army", "معركة", "جيش"): "crowd multiplication, dust hits, arrow/volley elements",
    ("sea", "بحر", "ship", "سفينة"): "sea spray, horizon stabilisation, sky replacement if needed",
}
SFX_KEYWORDS = {
    ("sword", "سيف"): "sword unsheathe + metal clash", ("horse", "حصان", "خيل"): "hoof beats, horse snort",
    ("door", "باب"): "heavy wooden door creak", ("fire", "نار"): "fire crackle", ("rain", "مطر"): "rain on stone, thunder",
    ("cat", "قط"): "cat meow / paw steps", ("dog", "كلب"): "dog bark / collar jingle", ("market", "سوق"): "market walla",
    ("sea", "بحر"): "waves, gulls", ("wind", "ريح"): "wind gusts", ("run", "يجري"): "running footsteps, breath",
}


@dataclass(frozen=True)
class Scene:
    scene_id: str
    heading: str
    description: str
    duration_seconds: float | None = None
    mood: str | None = None
    characters: tuple[str, ...] = ()
    location: str = ""
    time_of_day: str = ""


@dataclass
class Shot:
    shot_id: str
    size: str
    angle: str
    lens: str
    movement: str
    duration_seconds: float
    purpose: str


@dataclass
class SceneDirection:
    scene_id: str
    heading: str
    mood: str
    duration_seconds: float
    average_shot_length: float
    cuts_per_minute: float
    shots: list[Shot]
    lighting: dict
    transition_out: str
    vfx: list[str]
    sound: dict
    continuity: list[str]
    notes: list[str] = field(default_factory=list)


def _norm(text: str) -> str:
    return text.lower()


def detect_mood(text: str, explicit: str | None = None) -> str:
    if explicit and explicit in MOOD_GRAMMAR:
        return explicit
    low = _norm(text)
    scores = {mood: sum(low.count(k) for k in keys) for mood, keys in MOOD_KEYWORDS.items()}
    best = max(scores, key=lambda m: (scores[m], m == "calm"))
    return best if scores[best] > 0 else "calm"


HEADING_RE = re.compile(r"^\s*(?:scene\s*\d*|int\.|ext\.|int/ext\.|مشهد\s*\S*)[\s:.\-]*(.*)$", re.IGNORECASE)


def parse_script(script: str) -> list[Scene]:
    """Split a script on scene headings; without headings, each paragraph is a scene."""
    lines = script.strip().splitlines()
    blocks: list[tuple[str, list[str]]] = []
    for line in lines:
        m = HEADING_RE.match(line)
        if m and line.strip():
            blocks.append((line.strip(), []))
        elif blocks:
            blocks[-1][1].append(line)
    if not blocks:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", script.strip()) if p.strip()]
        blocks = [(f"Scene {i}", [p]) for i, p in enumerate(paragraphs, 1)]
    scenes = []
    for i, (heading, body) in enumerate(blocks, 1):
        text = " ".join(x.strip() for x in body if x.strip())
        upper = heading.upper()
        tod = "night" if ("NIGHT" in upper or "ليل" in heading) else "day" if ("DAY" in upper or "نهار" in heading) else ""
        scenes.append(Scene(scene_id=f"S{i:02d}", heading=heading, description=text or heading, time_of_day=tod,
                            location=heading.split("-")[0].strip()))
    return scenes


def _pick(options: list[str], seed: str, index: int) -> str:
    digest = int(hashlib.sha256(f"{seed}:{index}".encode()).hexdigest(), 16)
    return options[digest % len(options)]


def _keyword_hits(text: str, table: dict) -> list[str]:
    low = _norm(text)
    return [value for keys, value in table.items() if any(k in low for k in keys)]


def direct_scene(scene: Scene, channel: str = "default", next_scene: Scene | None = None, is_first: bool = False) -> SceneDirection:
    profile = CHANNEL_PROFILES.get(channel, CHANNEL_PROFILES["default"])
    text = f"{scene.heading} {scene.description}"
    mood = detect_mood(text, scene.mood)
    g = MOOD_GRAMMAR[mood]
    duration = float(scene.duration_seconds or max(8.0, min(60.0, len(scene.description.split()) * 0.6)))
    asl = round(max(0.8, g["asl"] * profile["pace_factor"]), 2)
    count = max(2, round(duration / asl))
    shot_len = round(duration / count, 2)
    shots = []
    for i in range(count):
        if i == 0:
            size, purpose = g["sizes"][0], "establish place, time and scale"
        elif i == count - 1:
            size, purpose = g["sizes"][-1], "button the beat / lead into transition"
        else:
            size = g["sizes"][1 + (i - 1) % max(1, len(g["sizes"]) - 1)] if len(g["sizes"]) > 1 else g["sizes"][0]
            purpose = "coverage: action and reaction" if i % 2 else "emotion / detail"
        shots.append(Shot(f"{scene.scene_id}-{i + 1:02d}", size, g["angle"], g["lens"], _pick(g["movement"], scene.scene_id, i), shot_len, purpose))
    if is_first:
        shots[0].purpose = f"HOOK in first {profile['hook_seconds']}s: strongest image first, then establish"
        hook = min(shots[0].duration_seconds, float(profile["hook_seconds"]))
        spare = round(shots[0].duration_seconds - hook, 2)
        shots[0].duration_seconds = hook
        if spare > 0:  # keep the scene length: give the trimmed time to the next shot
            shots[1].duration_seconds = round(shots[1].duration_seconds + spare, 2)
    style, ratio, kelvin, motivation = g["lighting"]
    if scene.time_of_day == "night" and kelvin > 4500:
        kelvin, notes_light = 4000, "night scene: cooler ambient, warm practicals"
    else:
        notes_light = ""
    lighting = {"style": style, "contrast_ratio": ratio, "color_temperature_k": kelvin, "motivation": motivation,
                "grade": profile["look"], **({"note": notes_light} if notes_light else {})}
    transition = "end card / fade to black" if next_scene is None else g["transition"]
    if next_scene is not None and detect_mood(f"{next_scene.heading} {next_scene.description}", next_scene.mood) != mood:
        transition += " + sound bridge (pre-lap next scene audio 0.5-1s)"
    sfx = _keyword_hits(text, SFX_KEYWORDS)
    sound = {"music_cue": g["music"], "ambience": g["ambience"], "sfx": sfx,
             "mix": "dialogue -12 LUFS short-term priority; music ducked 6-8 dB under voice",
             "rights_required": "original, licensed or public domain only - list each asset in the rights manifest"}
    continuity = [
        "keep the 180-degree line for every dialogue/confrontation; cross only on a visible move",
        "match eyelines between singles; keep screen direction of travel consistent",
        "lock character look (costume, hair, props) per scene reference frame",
    ]
    if scene.characters:
        continuity.append(f"character reference sheet required for: {', '.join(scene.characters)}")
    notes = [f"aspect ratio {profile['aspect_ratio']}, {profile['fps']} fps", f"captions: {profile['caption_style']}"]
    return SceneDirection(scene.scene_id, scene.heading, mood, round(duration, 2), asl, round(60 / asl, 1), shots, lighting,
                          transition, _keyword_hits(text, VFX_KEYWORDS), sound, continuity, notes)


def rights_check(assets: Iterable[dict]) -> dict:
    """Every music/SFX/footage asset needs rights in ALLOWED_RIGHTS and a source. Fail closed."""
    problems = []
    for a in assets:
        if a.get("rights") not in ALLOWED_RIGHTS:
            problems.append(f"{a.get('name', '?')}: rights '{a.get('rights')}' not allowed")
        elif a.get("rights") in ("licensed", "public_domain") and not str(a.get("source_url", "")).startswith(("https://", "http://")):
            problems.append(f"{a.get('name', '?')}: source_url required for {a.get('rights')} asset")
    return {"decision": "go_draft" if not problems else "no_go", "problems": problems}


def build_direction_plan(title: str, scenes: list[Scene] | None = None, script: str | None = None,
                         channel: str = "default", assets: Iterable[dict] = ()) -> dict:
    if not scenes and not script:
        raise ValueError("scenes or script required")
    scenes = list(scenes or parse_script(script or ""))
    directions = [direct_scene(s, channel, scenes[i + 1] if i + 1 < len(scenes) else None, i == 0) for i, s in enumerate(scenes)]
    rights = rights_check(assets)
    total = round(sum(d.duration_seconds for d in directions), 2)
    return {
        "contract_version": CONTRACT_VERSION,
        "title": title,
        "channel": channel if channel in CHANNEL_PROFILES else "default",
        "channel_profile": CHANNEL_PROFILES.get(channel, CHANNEL_PROFILES["default"]),
        "total_duration_seconds": total,
        "scene_count": len(directions),
        "shot_count": sum(len(d.shots) for d in directions),
        "scenes": [asdict(d) for d in directions],
        "rights": rights,
        "decision": rights["decision"],
        "publish_allowed": False,
        "zero_cost": True,
    }


def to_media_handoff(plan: dict, run_id: str) -> dict:
    """Package the plan for Media Spider (visual_director -> editor)."""
    return MediaHandoff(run_id=run_id, sender="visual_director", recipient="editor",
                        payload_type="direction_plan", payload=plan).to_dict()


def format_plan(plan: dict) -> str:
    lines = [f"# Direction plan: {plan['title']}", f"Channel: {plan['channel_profile']['label']} | "
             f"{plan['scene_count']} scenes, {plan['shot_count']} shots, {plan['total_duration_seconds']}s | decision: {plan['decision']}", ""]
    for s in plan["scenes"]:
        lines.append(f"## {s['scene_id']} {s['heading']} - {s['mood']} ({s['duration_seconds']}s, ASL {s['average_shot_length']}s)")
        for shot in s["shots"]:
            lines.append(f"- {shot['shot_id']}: {shot['size']}, {shot['angle']}, {shot['lens']}, {shot['movement']}, {shot['duration_seconds']}s - {shot['purpose']}")
        L = s["lighting"]
        lines.append(f"- Lighting: {L['style']} | {L['contrast_ratio']} | {L['color_temperature_k']}K | motivated by {L['motivation']}")
        if s["vfx"]:
            lines.append(f"- VFX: {'; '.join(s['vfx'])}")
        lines.append(f"- Sound: music {s['sound']['music_cue']} | ambience {s['sound']['ambience']}" + (f" | SFX {', '.join(s['sound']['sfx'])}" if s['sound']['sfx'] else ""))
        lines.append(f"- Transition out: {s['transition_out']}")
        lines.append("")
    if plan["rights"]["problems"]:
        lines.extend(["## Rights problems", *[f"- {p}" for p in plan["rights"]["problems"]]])
    return "\n".join(lines)


def route_directing(command: dict) -> dict:
    if command.get("domain") != "directing":
        return {"accepted": False, "reason": "wrong_route"}
    scenes = [Scene(**s) if isinstance(s, dict) else s for s in command.get("scenes", [])] or None
    return build_direction_plan(command.get("title", "Untitled"), scenes, command.get("script"),
                                command.get("channel", "default"), command.get("assets", []))


if __name__ == "__main__":
    import argparse, json, sys
    p = argparse.ArgumentParser(description="Director Spider: direction plan from a script (stdin or file)")
    p.add_argument("script_file", nargs="?", help="Script text file; stdin when omitted")
    p.add_argument("--title", default="Untitled")
    p.add_argument("--channel", default="default", choices=sorted(CHANNEL_PROFILES))
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    text = open(a.script_file, encoding="utf-8").read() if a.script_file else sys.stdin.read()
    plan = build_direction_plan(a.title, script=text, channel=a.channel)
    print(json.dumps(plan, ensure_ascii=False, indent=2) if a.json else format_plan(plan))
