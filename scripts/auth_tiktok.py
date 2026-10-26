"""Retired unsafe manual bootstrap. OAuth must use a verified HTTPS callback.

The old script requested only video.upload, used localhost, asked for a code in
an interactive terminal and appended long-lived secrets to .env. That cannot
provision unattended public publishing safely. See TIKTOK_SETUP.md.
"""


def main() -> int:
    print("TikTok OAuth is not configured. See TIKTOK_SETUP.md; do not paste codes or tokens here.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
