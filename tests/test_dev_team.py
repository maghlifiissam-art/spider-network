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

def test_funnel_counts():
    from dev_team import measure
    rows = [mk(i, "x", 10, 1) for i in range(4)]
    for r, c in zip(rows, ["a", "a", "b", "p"]): r["channel_id"] = c
    rows[0]["pinned"] = True
    ch = {"a": "u1", "b": "u2", "p": next(iter(measure.PLATFORM_OWNERS))}
    f = measure.funnel(rows, None, ch)
    assert f["registered_accounts"] is None          # unknown, never guessed
    assert f["publishing_creators"] == 2              # u1 (one non-pinned post), u2; platform owner excluded
    assert f["viewer"]["views"] == 40

def test_funnel_report_delta():
    import tempfile
    p = Path(tempfile.mkdtemp()) / "f.jsonl"
    s = lambda c, v, r: json.dumps({"t": "x", "registered_accounts": r, "publishing_creators": c, "viewer": {"views": v}})
    p.write_text(s(1, 10, 5) + "\n" + s(3, 25, 9) + "\n")
    r = analyze.funnel_report(p)
    assert r["since_previous"] == {"registered_accounts": 4, "publishing_creators": 2, "views": 15}
    assert r["activation_rate"] == round(3 / 9, 4)

if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("ok", n)
