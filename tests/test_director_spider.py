import unittest

import director_spider as d

SCRIPT = """EXT. DESERT - DAY
The army gathers on the dunes. A sword is raised as the battle begins.

INT. TENT - NIGHT
Sayf reads a secret letter by a lamp. Danger is near.

مشهد 3 - الواحة
فجر هادئ في الحديقة قرب البحر.
"""


class DirectorSpiderTests(unittest.TestCase):
    def test_parse_script_headings_including_arabic(self):
        scenes = d.parse_script(SCRIPT)
        self.assertEqual([s.scene_id for s in scenes], ["S01", "S02", "S03"])
        self.assertEqual(scenes[1].time_of_day, "night")
        self.assertIn("الواحة", scenes[2].heading)

    def test_parse_script_without_headings_uses_paragraphs(self):
        self.assertEqual(len(d.parse_script("one\n\ntwo")), 2)

    def test_mood_detection(self):
        self.assertEqual(d.detect_mood("the battle and the army"), "epic")
        self.assertEqual(d.detect_mood("قط مضحك"), "comedic")
        self.assertEqual(d.detect_mood("nothing special"), "calm")
        self.assertEqual(d.detect_mood("battle", explicit="sad"), "sad")

    def test_plan_is_deterministic_and_complete(self):
        a = d.build_direction_plan("Sayf", script=SCRIPT, channel="nexa_stories")
        b = d.build_direction_plan("Sayf", script=SCRIPT, channel="nexa_stories")
        self.assertEqual(a, b)
        self.assertEqual(a["scene_count"], 3)
        first = a["scenes"][0]
        self.assertEqual(first["mood"], "epic")
        self.assertIn("HOOK", first["shots"][0]["purpose"])
        self.assertLessEqual(first["shots"][0]["duration_seconds"], 3)
        self.assertTrue(first["sound"]["sfx"])
        self.assertTrue(first["vfx"])
        self.assertEqual(a["scenes"][-1]["transition_out"], "end card / fade to black")
        self.assertIn("sound bridge", first["transition_out"])
        self.assertAlmostEqual(sum(s["duration_seconds"] for s in first["shots"]), first["duration_seconds"], delta=0.1)
        self.assertFalse(a["publish_allowed"])

    def test_night_scene_cools_lighting(self):
        plan = d.build_direction_plan("x", script=SCRIPT)
        self.assertLessEqual(plan["scenes"][1]["lighting"]["color_temperature_k"], 4300)

    def test_funimal_is_faster_than_nexa(self):
        scene = [d.Scene("S01", "Cat", "a funny cat prank with a dog", duration_seconds=12)]
        fun = d.build_direction_plan("c", scenes=scene, channel="funimal")["scenes"][0]
        nexa = d.build_direction_plan("c", scenes=scene, channel="nexa_stories")["scenes"][0]
        self.assertLess(fun["average_shot_length"], nexa["average_shot_length"])
        self.assertGreater(len(fun["shots"]), len(nexa["shots"]))

    def test_rights_fail_closed(self):
        bad = d.build_direction_plan("x", script=SCRIPT, assets=[{"name": "hit song", "rights": "unknown"}])
        self.assertEqual(bad["decision"], "no_go")
        missing_src = d.rights_check([{"name": "track", "rights": "licensed"}])
        self.assertEqual(missing_src["decision"], "no_go")
        ok = d.rights_check([{"name": "score", "rights": "original"}, {"name": "rain", "rights": "public_domain", "source_url": "https://freesound.org/x"}])
        self.assertEqual(ok["decision"], "go_draft")

    def test_requires_input_and_route(self):
        with self.assertRaises(ValueError):
            d.build_direction_plan("x")
        self.assertFalse(d.route_directing({"domain": "media"})["accepted"])
        plan = d.route_directing({"domain": "directing", "title": "t", "scenes": [{"scene_id": "S01", "heading": "h", "description": "rain at night"}]})
        self.assertEqual(plan["scene_count"], 1)

    def test_media_handoff(self):
        plan = d.build_direction_plan("x", script=SCRIPT, channel="nexa_stories")
        h = d.to_media_handoff(plan, "run-1")
        self.assertEqual((h["sender"], h["recipient"], h["payload_type"]), ("visual_director", "editor", "direction_plan"))
        self.assertEqual(h["contract_version"], "media.v1")

    def test_format_plan(self):
        text = d.format_plan(d.build_direction_plan("Sayf", script=SCRIPT, channel="nexa_stories"))
        self.assertIn("# Direction plan: Sayf", text)
        self.assertIn("Lighting:", text)


if __name__ == "__main__":
    unittest.main()
