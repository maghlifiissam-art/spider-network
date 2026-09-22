"""
auth_tiktok.py — ربط تيكتوك مرة وحدة (Content Posting API)
------------------------------------------------------------------
قبل ما تشغل:
  1. developers.tiktok.com -> حساب مطور (مجاني) -> Create app
  2. زيد المنتج "Content Posting API" وطلب سكوب video.upload (للمسودات)
     — video.publish (النشر المباشر) خاصو موافقة TikTok
  3. دير redirect URI: http://localhost:8080/callback/

تشغيل:  TIKTOK_CLIENT_KEY=... TIKTOK_CLIENT_SECRET=... python scripts/auth_tiktok.py
  1. السكريبت كيعطيك رابط — حلو فالمتصفح ووافق
  2. TikTok كيرجعك لـ localhost بكود فالرابط — لصقو هنا
النتيجة: كيزيد TIKTOK_ACCESS_TOKEN / TIKTOK_REFRESH_TOKEN فـ .env
  (access token قصير العمر؛ publishers كيجددوه بالـ refresh token)
"""
import os
import urllib.parse

import requests

API = "https://open.tiktokapis.com/v2"


def main() -> int:
    key = os.environ.get("TIKTOK_CLIENT_KEY", "")
    secret = os.environ.get("TIKTOK_CLIENT_SECRET", "")
    if not (key and secret):
        print("خاص TIKTOK_CLIENT_KEY و TIKTOK_CLIENT_SECRET")
        return 1
    params = urllib.parse.urlencode({
        "client_key": key, "response_type": "code",
        "scope": "video.upload", "redirect_uri": "http://localhost:8080/callback/"})
    print(f"حل هاد الرابط فالمتصفح ووافق:\nhttps://www.tiktok.com/v2/auth/authorize/?{params}\n")
    code = input("لصق هنا الـ code من رابط الرجوع: ").strip()
    resp = requests.post(f"{API}/oauth/token/", data={
        "client_key": key, "client_secret": secret, "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": "http://localhost:8080/callback/"}, timeout=30).json()
    data = resp.get("data", {})
    if not data.get("access_token"):
        print(f"فشل: {resp}")
        return 1
    with open(".env", "a", encoding="utf-8") as fh:
        fh.write("\n# TikTok Content Posting API (scripts/auth_tiktok.py)\n")
        fh.write(f"TIKTOK_ACCESS_TOKEN={data['access_token']}\n")
        fh.write(f"TIKTOK_REFRESH_TOKEN={data.get('refresh_token', '')}\n")
    print("تم ✅ تيكتوك مربوط — الوضع الافتراضي: مسودات (draft).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
