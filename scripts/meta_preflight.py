"""GET-only credential preflight. Never imports or calls a publishing adapter."""
import json
import os
import re
import urllib.parse
import urllib.request


def get(path, token, params=None):
    # Fixed Meta host. No provider error bodies, URLs or tokens reach logs.
    request = urllib.request.Request(
        "https://graph.facebook.com/v26.0/" + path + "?" + urllib.parse.urlencode(params or {}),
        headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.load(response)


def check():
    app = os.environ["META_APP_ID"]
    user = os.environ["META_USER_ACCESS_TOKEN"]
    mapping = json.loads(os.environ["META_PAGE_TOKEN_ENV_MAP"])
    if not app.isdecimal() or not isinstance(mapping, dict) or len(mapping) != 2:
        raise ValueError("invalid explicit two-Page configuration")
    required = {"pages_show_list", "pages_read_engagement", "pages_manage_posts"}
    metadata = get("debug_token", user, {"input_token": user})["data"]
    if not metadata.get("is_valid") or metadata.get("app_id") != app or metadata.get("type") != "USER":
        raise ValueError("user token mismatch")
    grants = {s["scope"]: set(s.get("target_ids", [])) for s in metadata.get("granular_scopes", [])}
    if any(grants.get(scope) != set(mapping) for scope in required):
        raise ValueError("Page grant mismatch")
    for page, name in mapping.items():
        if not page.isdecimal() or not re.fullmatch(r"META_[A-Z0-9_]+_PAGE_TOKEN", name):
            raise ValueError("invalid explicit Page mapping")
        token = os.environ[name]
        identity = get("me", token, {"fields": "id"})
        data = get("debug_token", user, {"input_token": token})["data"]
        if identity.get("id") != page or not data.get("is_valid") or data.get("type") != "PAGE" or data.get("app_id") != app:
            raise ValueError("Page token mismatch")
    return {"verified_pages": len(mapping), "dry_run": True, "http_methods": ["GET"], "published": False}


if __name__ == "__main__":
    try:
        print(json.dumps(check()))
    except Exception:
        print("Meta preflight failed; no credentials or provider details logged")
        raise SystemExit(1) from None
