"""
auth_youtube.py — ربط يوتيوب مرة وحدة (كيعطي refresh token)
------------------------------------------------------------------
قبل ما تشغل:
  1. console.cloud.google.com -> مشروع جديد (مجاني) بالحساب maghlifiissam@gmail.com
  2. فعل "YouTube Data API v3"
  3. OAuth consent screen: External، عمر المعلومات، و**بدل الحالة لـ "In production"**
     (مهم: إلا بقى "Testing" الـ refresh token كيموت كل 7 أيام!)
  4. Credentials -> Create OAuth client ID -> Desktop app -> نزل client_secrets.json
  5. حط client_secrets.json هنا فالريبو (محلي فقط — ممنوع commit)

تشغيل:  python scripts/auth_youtube.py
النتيجة: كيزيد YOUTUBE_CLIENT_ID/SECRET/REFRESH_TOKEN فـ .env (محلي، ماشي فـ git)

و: قدم طلب الـ API compliance audit (مجاني) باش الفيديوهات يخرجو public:
  https://support.google.com/youtube/contact/yt_api_form
"""
import json
import os
import sys

ENV_KEYS = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")


def main() -> int:
    secrets_path = sys.argv[1] if len(sys.argv) > 1 else "client_secrets.json"
    if not os.path.exists(secrets_path):
        print(f"client secrets ما لقيتش: {secrets_path}")
        return 1
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("نقص: pip install google-auth-oauthlib")
        return 1
    flow = InstalledAppFlow.from_client_secrets_file(
        secrets_path, scopes=["https://www.googleapis.com/auth/youtube.upload"])
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
    if not creds.refresh_token:
        print("Google ما عطاش refresh token — جرب بـ prompt=consent و access_type=offline")
        return 1
    with open(secrets_path, encoding="utf-8") as fh:
        client = json.load(fh)["installed"]
    lines = [
        f"YOUTUBE_CLIENT_ID={client['client_id']}",
        f"YOUTUBE_CLIENT_SECRET={client['client_secret']}",
        f"YOUTUBE_REFRESH_TOKEN={creds.refresh_token}",
    ]
    with open(".env", "a", encoding="utf-8") as fh:
        fh.write("\n# YouTube Data API (scripts/auth_youtube.py)\n" + "\n".join(lines) + "\n")
    print("تم ✅ تزادو المفاتيح فـ .env — ماتشاركش هاد الملف مع حد.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
