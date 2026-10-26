"""Own-app Meta credential setup, with explicit Page IDs and private output.

No publishing, no Live-mode change, no Instagram access, no Page-order fallback.
Supply secrets through private files, never command-line literal values. Output
must be outside the checkout. User and Page tokens remain revocable even when
Meta reports no scheduled expiry. See README_META_SETUP.md.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import requests

GRAPH = "https://graph.facebook.com/v26.0"


def require_result(response):
    try:
        data = response.json()
    except ValueError:
        raise ValueError("Meta returned unreadable response") from None
    if not response.ok or "error" in data:
        error = data.get("error", {})
        raise ValueError("Meta rejected request (code=%s, subcode=%s)" %
                         (error.get("code"), error.get("error_subcode")))
    return data


def select_pages(pages, expected_ids):
    """Require the exact configured assets with content capability."""
    selected = {p["id"]: p for p in pages if p.get("id") in expected_ids}
    if set(selected) != set(expected_ids):
        raise ValueError("one or more selected Pages unavailable")
    for page in selected.values():
        if "CREATE_CONTENT" not in page.get("tasks", []):
            raise ValueError("selected Page lacks CREATE_CONTENT")
        if not page.get("access_token"):
            raise ValueError("selected Page token unavailable")
    return selected


def private_json(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump(data, fh)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-id", required=True)
    parser.add_argument("--app-secret-file", required=True, type=Path)
    parser.add_argument("--user-token-file", required=True, type=Path)
    parser.add_argument("--page-id", action="append", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    out = args.output_dir.resolve()
    if out == root or root in out.parents:
        parser.error("credential output must be outside checkout")
    expected = set(args.page_id)
    if len(expected) != len(args.page_id) or not all(x.isdecimal() for x in expected):
        parser.error("Page IDs must be unique decimal identifiers")
    secret = args.app_secret_file.read_text().strip()
    short = args.user_token_file.read_text().strip()
    if not secret or not short or short.startswith(("https:", "http:")):
        parser.error("secret/token inputs invalid")
    try:
        user = require_result(requests.get(GRAPH + "/oauth/access_token", params={
            "grant_type": "fb_exchange_token", "client_id": args.app_id,
            "client_secret": secret, "fb_exchange_token": short}, timeout=30))
        token = user.get("access_token")
        if not token:
            raise ValueError("exchange returned no token")
        auth = {"Authorization": "Bearer " + token}
        metadata = require_result(requests.get(GRAPH + "/debug_token", params={
            "input_token": token}, headers=auth, timeout=30)).get("data", {})
        if not metadata.get("is_valid") or str(metadata.get("app_id")) != args.app_id:
            raise ValueError("token app/validity mismatch")
        required = {"pages_show_list", "pages_read_engagement", "pages_manage_posts"}
        if not required <= set(metadata.get("scopes", [])):
            raise ValueError("required Pages scopes missing")
        granular = {x["scope"]: set(x.get("target_ids", []))
                    for x in metadata.get("granular_scopes", [])}
        if any(granular.get(scope) != expected for scope in required):
            raise ValueError("granular Page grant differs from explicit destinations")
        data = require_result(requests.get(GRAPH + "/me/accounts", params={
            "fields": "id,name,tasks,access_token", "limit": 100}, headers=auth, timeout=30))
        pages = select_pages(data.get("data", []), expected)
        # Verify every derived Page token before writing any credential files.
        page_metadata = {}
        for page_id, page in pages.items():
            page_auth = {"Authorization": "Bearer " + page["access_token"]}
            identity = require_result(requests.get(GRAPH + "/me", params={
                "fields": "id,name"}, headers=page_auth, timeout=30))
            if identity.get("id") != page_id:
                raise ValueError("derived token Page identity mismatch")
            inspected = require_result(requests.get(GRAPH + "/debug_token", params={
                "input_token": page["access_token"]}, headers=auth, timeout=30)).get("data", {})
            if not inspected.get("is_valid") or str(inspected.get("app_id")) != args.app_id:
                raise ValueError("derived Page token app/validity mismatch")
            if inspected.get("type") != "PAGE":
                raise ValueError("derived token is not a Page token")
            page_metadata[page_id] = {k: inspected.get(k) for k in
                                     ["type", "expires_at", "data_access_expires_at"]}
        out.mkdir(mode=0o700, parents=True, exist_ok=False)
        os.chmod(out, 0o700)
        private_json(out / "credentials.json", {
            "user_access_token": token,
            "page_access_tokens": {pid: p["access_token"] for pid, p in pages.items()}})
        private_json(out / "metadata.json", {"app_id": args.app_id,
            "expires_at": metadata.get("expires_at"),
            "data_access_expires_at": metadata.get("data_access_expires_at"),
            "page_ids": sorted(pages), "page_token_metadata": page_metadata, "dry_run": True})
        print("Verified explicit Page credentials saved privately; dry-run remains required.")
        return 0
    except ValueError as exc:
        print(str(exc))  # only controlled messages above, never provider bodies
    except Exception:
        print("Meta setup failed; no secret-bearing exception details logged")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
