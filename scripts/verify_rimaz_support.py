"""Read-only pre-send gate. Never replies, updates tickets, or invokes an LLM."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from anti_hallucination_spider import Source, receipt_json, verify_support


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--draft-file', required=True)
    p.add_argument('--ticket-id', required=True)
    p.add_argument('--language', required=True)
    p.add_argument('--category', required=True)
    p.add_argument('--faq-id', default='report_problem')
    args = p.parse_args()
    registry = json.loads((Path(__file__).resolve().parents[1] / 'config/rimaz_support_evidence.json').read_text())
    draft = Path(args.draft_file).read_text(encoding='utf-8')
    try:
        with urlopen(registry['source_url'], timeout=15) as response:
            if response.geturl() != registry['source_url']:
                raise ValueError('source redirect not allowed')
            raw = response.read(1_000_001)
            if len(raw) > 1_000_000:
                raise ValueError('source too large')
            content = raw.decode('utf-8')
        now = datetime.now(timezone.utc)
        source = Source(registry['source_url'], registry['revision'], content, now, {})
        result = verify_support(draft, args.ticket_id, args.language, args.faq_id,
                                args.category, source, registry, now)
    except Exception:
        result = {'schema': 'verification.v1', 'decision': 'blocked',
                  'release_allowed': False, 'issues': ['live_source_unavailable'],
                  'authorization_granted': False}
    print(receipt_json(result))
    return 0 if result['release_allowed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
