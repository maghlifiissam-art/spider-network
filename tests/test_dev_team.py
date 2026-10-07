import json, tempfile
from pathlib import Path
from dev_team import analyze, guidance, platform_evolution as pe

def mk(i, title, views, likes, kind="video", hour=12):
    return dict(id=f"id{i}", kind=kind, topic="general", title=title, sponsored=False, pinned=False,
                created_at=f"2026-10-0{1+i%7}T{hour:02d}:00:00+00:00", series=False, views=views, likes=likes, comments=0, reactions=0)

def test_collecting_until_enough_data():
    r = analyze.analyze([mk(i, "عنوان؟", 20, 1) for i in range(5)])
    assert r["status"] == "collecting" and r["winners"] == []

def test_sponsored_and_pinned_excluded():
    rows = [mk(1, "x", 10, 1)]; rows[0]["pinned"] = True
    assert analyze.analyze(rows)["posts_learnable"] == 0

def test_winner_found_with_enough_data():
    rows = [mk(i, "سؤال كبير؟", 100, 20) for i in range(20)] + [mk(100+i, "جملة عادية", 100, 1) for i in range(20)]
    r = analyze.analyze(rows)
    assert r["status"] == "ready"
    assert any(w["feature"] == "title_question" and w["value"] == "question" for w in r["winners"])

def test_guidance_roundtrip_and_safe_default():
    assert guidance.load_guidance("/nonexistent.json")["prefer"] == {}
    rows = [mk(i, "سؤال؟", 100, 20) for i in range(20)] + [mk(100+i, "جملة", 100, 1) for i in range(20)]
    with tempfile.TemporaryDirectory() as d:
        analyze.write_outputs(analyze.analyze(rows), d)
        g = guidance.load_guidance(Path(d) / "latest.json")
        assert g["prefer"].get("title_question") == "question" and "question" in g["prompt_snippet"]

def test_evolution_gates_and_pick():
    assert pe.pick_next() is not None
    bad = dict(state="evaluated", impact=5, effort_inverse=5, gates={"free_tier_only": False})
    assert pe.score(bad) == -1
    assert pe.verify({}, 10, 9) == "revert" and pe.verify({}, 10, 10) == "keep"

if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("ok", n)
