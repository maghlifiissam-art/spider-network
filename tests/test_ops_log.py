from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import ops_log


class OpsLogTests(TestCase):
    def test_log_stats_and_recent(self):
        with TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "ops.json")
            with patch.object(ops_log, "LOG_PATH", path):
                ops_log.log_operation("book", "success", "ok", "Guide")
                ops_log.log_operation("book", "failed", "bad")
                stats = ops_log.get_stats()
                self.assertEqual(stats["book"], {"success": 1, "failed": 1, "total": 2})
                recent = ops_log.get_recent(1)
                self.assertEqual(recent[0]["status"], "failed")
