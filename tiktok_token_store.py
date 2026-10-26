"""Private, rotation-safe TikTok OAuth token store. Never place token files in Git."""
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile


def token_path():
    path = os.environ.get("TIKTOK_TOKEN_FILE", "").strip()
    if not path:
        raise RuntimeError("TIKTOK_TOKEN_FILE must point to a private persistent volume")
    target = Path(path).expanduser().resolve()
    repo_root = Path(__file__).resolve().parent
    if target == repo_root or repo_root in target.parents:
        raise RuntimeError("Token storage cannot be inside the repository")
    return target


def load_tokens():
    path = token_path()
    if not path.is_file():
        raise RuntimeError("TikTok OAuth token file has not been initialized")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not data.get("refresh_token") or not data.get("open_id"):
        raise RuntimeError("Incomplete TikTok OAuth token state")
    return data


def save_tokens(data):
    if not data.get("refresh_token") or not data.get("open_id"):
        raise ValueError("TikTok token rotation requires refresh_token and open_id")
    target = token_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent, prefix=".tiktok-", delete=False) as tmp:
        os.chmod(tmp.name, 0o600)
        json.dump(data, tmp)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = tmp.name
    os.replace(tmp_path, target)
    os.chmod(target, 0o600)
