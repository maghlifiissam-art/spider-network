"""
gumroad_reports.py — تقارير الأرباح والاقتطاعات
------------------------------------------------------------------
كيجيب كل عمليات البيع الحقيقية من Gumroad (GET /v2/sales) ويحسب:
  - عدد العمليات المقتنصة بنجاح (sales_count)
  - الإيراد الإجمالي (gross)
  - عمولة Gumroad المقتطعة (gumroad_fee)
  - الضرائب المقتطعة (tax)
  - صافي الربح الحقيقي اللي كيوصل لحسابك (net)
  - عدد الاستردادات (refunded) والمنازعات (chargedback)

⚠️ محتاج الصلاحية view_sales عند توليد الـ Access Token.
"""

import os
import requests

API_BASE = "https://api.gumroad.com/v2"
ACCESS_TOKEN = os.environ.get("GUMROAD_ACCESS_TOKEN", "")


def fetch_all_sales(after: str = None) -> dict:
    """
    after: تاريخ ISO (مثلاً "2026-01-01") باش تجيب غير المبيعات من بعدو.
    يرجع dict: {"success": bool, "sales": list, "error": str|None}
    """
    if not ACCESS_TOKEN:
        return {"success": False, "sales": [], "error": "GUMROAD_ACCESS_TOKEN ناقص."}

    sales = []
    url = f"{API_BASE}/sales"
    params = {"access_token": ACCESS_TOKEN}
    if after:
        params["after"] = after

    try:
        while url:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if not data.get("success", True):
                return {"success": False, "sales": [], "error": data.get("message", "خطأ غير معروف.")}

            sales.extend(data.get("sales", []))
            next_page = data.get("next_page_url")
            url = f"https://api.gumroad.com{next_page}" if next_page else None
            params = {}  # الرابط next_page_url فيه access_token ومعطيات البحث بالفعل

        return {"success": True, "sales": sales, "error": None}

    except requests.exceptions.RequestException as e:
        return {"success": False, "sales": sales, "error": str(e)}


def compute_earnings_summary(sales: list) -> dict:
    """
    كيحسب ملخص شامل من لائحة المبيعات. كل المبالغ بالسنتيم.
    """
    gross = sum(s.get("price", 0) for s in sales)
    gumroad_fee = sum(s.get("gumroad_fee", 0) for s in sales)
    tax = sum(s.get("tax_cents", 0) or 0 for s in sales)
    refunded = [s for s in sales if s.get("refunded")]
    chargedback = [s for s in sales if s.get("chargedback")]
    successful = [s for s in sales if not s.get("refunded") and not s.get("chargedback")]

    net = gross - gumroad_fee - tax - sum(s.get("price", 0) for s in refunded)

    return {
        "total_operations": len(sales),
        "successful_operations": len(successful),
        "refunded_count": len(refunded),
        "chargedback_count": len(chargedback),
        "gross_cents": gross,
        "gumroad_fee_cents": gumroad_fee,
        "tax_cents": tax,
        "net_cents": net,
    }


def get_earnings_report(after: str = None) -> dict:
    """نقطة الدخول الوحيدة: كتجيب المبيعات وكترجع الملخص جاهز للعرض."""
    result = fetch_all_sales(after)
    if not result["success"]:
        return {"success": False, "error": result["error"], "summary": None, "sales": []}

    summary = compute_earnings_summary(result["sales"])
    return {"success": True, "error": None, "summary": summary, "sales": result["sales"]}
