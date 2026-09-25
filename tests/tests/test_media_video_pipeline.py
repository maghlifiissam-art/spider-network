import tempfile
import unittest
from pathlib import Path
from media_video_pipeline import build_packet, validate_scenes, assess_assets, save_packet

STORY = 'كانت القرية تخفي سرا خلف الباب القديم. ' * 15

class VideoPipelineTests(unittest.TestCase):
    def test_source_and_story_required(self):
        for title, story, source, owned in [('', STORY, 'owner', True), ('t', 'قصة', 'owner', True),
                                             ('t', STORY, '', True), ('t', STORY, 'owner', False)]:
            with self.assertRaises(ValueError): build_packet(title, story, story_source=source, story_owner_confirmed=owned)
    def test_packet_private_and_not_publishing(self):
        packet = build_packet('قصتي', STORY, story_source='user-provided', story_owner_confirmed=True)
        self.assertEqual(packet['scene_count'], 10)
        self.assertIn(STORY.strip(), packet['prompt'])
        self.assertFalse(packet['publish_allowed'])
        self.assertEqual(packet['providers']['elevenlabs_free'], 'noncommercial demo only, never publish as commercial')
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'private.json'
            save_packet(packet, p)
            self.assertTrue(p.exists())
    def test_incomplete_and_free_voice_fail(self):
        with self.assertRaises(ValueError): validate_scenes([])
        scenes = [dict(scene_id=f'S{i:02d}', heading='h', story_beat='b', characters=['a'],
                       location='l', narration_ar='نص', image_prompt_en='image',
                       motion_prompt_en='motion', duration_seconds=5) for i in range(1,11)]
        self.assertIn('missing:narration', assess_assets(scenes, [])['problems'])
        assets = [dict(key=f'S{i:02d}:{k}', path='x', source='mine', license_evidence='mine',
                       commercial_use=True) for i in range(1,11) for k in ('image','clip')]
        assets += [dict(key='narration', path='x', source='mine', license_evidence='mine',
                        commercial_use=True, provider='elevenlabs_free'),
                   dict(key='final_cut', path='x', source='mine', license_evidence='mine', commercial_use=True)]
        self.assertFalse(assess_assets(scenes, assets)['draft_ready'])
        assets[-2]['provider'] = 'self_recorded_voice'
        self.assertTrue(assess_assets(scenes, assets)['draft_ready'])
        self.assertFalse(assess_assets(scenes, assets)['publish_allowed'])

if __name__ == '__main__': unittest.main()
