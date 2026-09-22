"""
auth_meta.py — ربط Meta (Facebook Page + Instagram) مرة وحدة
------------------------------------------------------------------
قبل ما تشغل:
  1. developers.facebook.com -> My Apps -> Create App -> نوع "Business" (مجاني)
  2. زيد المنتجات: "Facebook Login for Business" + "Instagram"
  3. من Graph API Explorer جيب short-lived user token بالصلاحيات:
     pages_show_list, pages_read_engagement, pages_manage_posts,
     instagram_basic, instagram_content_publish
  4. بدل التطبيق من Development لـ Live (الحسابات ديالنا = business we own:
     Standard Access بلا App Review)

تشغيل:  META_APP_ID=... META_APP_SECRET=... META_SHORT_TOKEN=... python scripts/auth_meta.py
النتيجة: كيزيد META_PAGE_ACCESS_TOKEN / META_PAGE_ID / META_IG_USER_ID فـ .env
  (Page token طويل الأمد — ماشي 60 يوم، ما كيخلصش)
"""
import os

import requests

GRAPH = "https://graph.facebook.com/v21.0"


def main() -> int:
    app_id = os.environ.get("META_APP_ID", "")
    app_secret = os.environ.get("META_APP_SECRET", "")
    short_token = os.environ.get("META_SHORT_TOKEN", "")
    if not (app_id and app_secret and short_token):
        print("خاص META_APP_ID و META_APP_SECRET و META_SHORT_TOKEN")
        return 1
    long_user = requests.get(f"{GRAPH}/oauth/access_token", params={
        "grant_type": "fb_exchange_token", "client_id": app_id,
        "client_secret": app_secret, "fb_exchange_token": short_token}, timeout=30).json()
    user_token = long_user.get("access_token", "")
    if not user_token:
        print(f"فشل تبديل التوكن: {long_user}")
        return 1
    pages = requests.get(f"{GRAPH}/me/accounts",
                         params={"access_token": user_token}, timeout=30).json().get("data", [])
    if not pages:
        print("ما كاينة حتى صفحة Facebook فهاد الحساب — صاوبها أولاً من التيليفون.")
        return 1
    page = pages[0]
    ig = requests.get(f"{GRAPH}/{page['id']}", params={
        "fields": "instagram_business_account", "access_token": page["access_token"]},
        timeout=30).json().get("instagram_business_account", {})
    with open(".env", "a", encoding="utf-8") as fh:
        fh.write("\n# Meta Graph API (scripts/auth_meta.py)\n")
        fh.write(f"META_PAGE_ACCESS_TOKEN={page['access_token']}\n")
        fh.write(f"META_PAGE_ID={page['id']}\n")
        if ig.get("id"):
            fh.write(f"META_IG_USER_ID={ig['id']}\n")
    print(f"تم ✅ صفحة: {page.get('name')} | IG linked: {bool(ig.get('id'))}")
    if not ig.get("id"):
        print("تنبيه: إنستغرام ماشي مربوط بالصفحة — حولو لحساب احترافي وربطو من التطبيق.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
