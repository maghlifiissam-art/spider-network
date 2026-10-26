"""Deterministic Media Spider orchestrator. Adapters are injected and replaceable."""
from __future__ import annotations
import json
from pathlib import Path
from media_contracts import EvidenceClaim, MediaHandoff, QAGate
from media_video_pipeline import build_packet

STAGES = ("trend_scout","story_writer","fact_checker","visual_director","voice_sound","editor","rights_qa")

class OfflineAdapter:
    name = "offline_fixture"
    zero_cost = True
    def __init__(self, fixture_dir: str | Path = "fixtures"): self.fixture_dir = Path(fixture_dir)
    def load(self, name: str) -> dict: return json.loads((self.fixture_dir / name).read_text())

class MediaSpider:
    route = "media"
    def __init__(self, adapter=None, state_dir: str | Path = "state/media"):
        self.adapter = adapter or OfflineAdapter()
        self.state_dir = Path(state_dir)
    def plan_video(self, title: str, story: str, *, story_source: str,
                   story_owner_confirmed: bool = False) -> dict:
        """Prepare a private ten-scene packet; never write source stories to public code."""
        return build_packet(title, story, story_source=story_source,
                            story_owner_confirmed=story_owner_confirmed)
    def run_pilot(self, fixture="sayf_pilot.json") -> dict:
        spec = self.adapter.load(fixture)
        claims = [EvidenceClaim(**c) for c in spec["claims"]]
        for c in claims: c.validate()
        gate = QAGate(**spec["qa"])
        result = {"contract_version":"media.v1", "route":self.route, "adapter":self.adapter.name,
          "zero_cost":bool(self.adapter.zero_cost), "stages":list(STAGES), "pilot":spec["pilot"],
          "deliverables":spec["deliverables"], "qa_decision":gate.decision(),
          "publish_allowed":False, "claims":[c.__dict__ for c in claims]}
        self.state_dir.mkdir(parents=True, exist_ok=True)
        (self.state_dir / f'{spec["pilot"]["id"]}.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
        return result

def route_media(command: dict, adapter=None) -> dict:
    if command.get("domain") != "media": return {"accepted":False,"reason":"wrong_route"}
    spider = MediaSpider(adapter=adapter)
    if command.get("action") == "plan_video":
        return spider.plan_video(command.get("title", ""), command.get("story", ""),
                                 story_source=command.get("story_source", ""),
                                 story_owner_confirmed=command.get("story_owner_confirmed", False))
    return spider.run_pilot(command.get("fixture", "sayf_pilot.json"))
