"""
boss_spider.py — العقل المدبر ورئيس شبكة العناكب
========================================================================
هذا هو المكون المركزي: كيتلقى أي أمر بلغة طبيعية (من Streamlit، من واتساب،
من أي واجهة أخرى)، كيفهم شنو بغى المستخدم بالضبط، وكيوجه الطلب للوكيل
المناسب (Book / Comic / Visual / Marketing / News)، وعند الطلب كينشر
المنتج مباشرة على Gumroad.

نقطة الدخول الوحيدة اللي خاصك تستعملها من أي مكان آخر فالمشروع:

    from boss_spider import handle_command
    result = handle_command("سولي كتاب على تربية الدجاج، 6 فصول، وبيعو ب5 دولار", language="العربية")
    print(result["message"])

------------------------------------------------------------------------
كيفاش كيخدم بالضبط:
  1. classify_intent()  -> Groq كيحلل الأمر ويرجع JSON: أي وكيل + أي معطيات
  2. dispatch()          -> كيستدعي الدالة الحقيقية المطابقة (نفس الدوال
                            اللي بنيناها فـ book_spider / comic_spider / ...)
  3. النتيجة كترجع كرسالة نصية واحدة جاهزة للعرض (فـ Streamlit ولا واتساب)
"""

import os
import json
import re
from groq import Groq

from book_spider import generate_full_book
from comic_spider import generate_comic_script
from compile_comic_pdf import generate_panel_images, compile_comic_to_pdf
from visual_spider import generate_coloring_book, generate_poster, generate_logo
from compile_pdf import compile_images_to_pdf
from gumroad_publish import publish_book
from catalog import add_product, search_catalog, load_catalog
from ops_log import log_operation
from news_spider import fetch_real_news, generate_blog_post
from engineering_spider import design_part, design_project
from electronics_spider import design_circuit
from cloud_architect_spider import design_cloud_architecture

MODEL = "llama-3.1-8b-instant"

MARKETING_PROMPTS = {
    "affiliate": "You are the Affiliate Spider, an autonomous market analyst and affiliate strategist. Identify high-potential micro-niches, traffic acquisition angles, and actionable next steps.",
    "media": "You are the Media Spider, a viral growth hacker and direct-response copywriter. Generate psychological ad hooks and short-form video scripts.",
    "digital": "You are the Digital Products Spider, a digital product architect and SEO strategist. Design ebook/course blueprints, pricing, and launch funnels.",
}


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_-]+", "-", text)[:60] or "item"


# ---------------------------------------------------------------------------
# 1) فهم الأمر: أي وكيل، وأي معطيات
# ---------------------------------------------------------------------------
def classify_intent(client: Groq, command: str, language: str) -> dict:
    system_prompt = """You are the routing brain of a multi-agent content factory called \
"Spider Network". Read the user's command and decide which specialist agent should handle it.

Respond ONLY with a valid JSON object, no markdown fences:
{
  "action": "marketing" | "book" | "comic" | "coloring_book" | "poster" | "logo" | "news_blog" | "engineering_part" | "engineering_project" | "electronics_circuit" | "cloud_architecture" | "status" | "unknown",
  "publish": true or false,
  "parameters": { ... }
}

Parameters per action:
- marketing: {"agent_type": "affiliate"|"media"|"digital", "topic": "..."}
- book: {"topic": "...", "genre": "...", "chapters": <int, default 5>, "price_cents": <int, default 500>}
- comic: {"mode": "prompt"|"script", "topic": "...", "user_script": "...", "panels": <int, default 10>, "price_cents": <int, default 400>}
- coloring_book: {"theme": "...", "pages": <int, default 8>, "price_cents": <int, default 300>}
- poster: {"topic": "...", "style": "...", "price_cents": <int, default 200>}
- logo: {"brand_name": "...", "style_keywords": "...", "price_cents": <int, default 200>}
- news_blog: {"topic": "...", "language_code": "en"|"fr"}
- engineering_part: {"description": "..."} (a single simple mechanical part — bracket, plate, frame)
- engineering_project: {"description": "..."} (a full product/assembly that should be broken down into multiple parts — use this when the user describes something bigger than one simple part, e.g. "a folding table" or "a wall shelf unit")
- electronics_circuit: {"description": "..."} (LED resistor sizing, voltage divider, or battery runtime estimate)
- cloud_architecture: {"description": "..."} (designing a backend/cloud system architecture for a product or feature)
- status: {} (user is asking about existing products/catalog, not requesting new content)
- unknown: {} (command unclear — ask for clarification)

If a required field is missing, make a reasonable default. Always keep text fields in their \
original language as written by the user."""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": command},
            ],
            temperature=0.2,
            max_tokens=500,
        )
        return json.loads(response.choices[0].message.content.strip())
    except json.JSONDecodeError:
        return {"action": "unknown", "publish": False, "parameters": {}}
    except Exception as e:
        return {"action": "error", "publish": False, "parameters": {"error": str(e)}}


# ---------------------------------------------------------------------------
# 2) تنفيذ كل وكيل
# ---------------------------------------------------------------------------
def _run_marketing(client: Groq, params: dict, language: str) -> dict:
    agent_type = params.get("agent_type", "affiliate")
    topic = params.get("topic", "")
    system_prompt = MARKETING_PROMPTS.get(agent_type, MARKETING_PROMPTS["affiliate"]) + f"\nRespond in {language}."
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": topic}],
        temperature=0.75,
        max_tokens=700,
    )
    return {"success": True, "message": response.choices[0].message.content.strip()}


def _run_book(client: Groq, params: dict, language: str, publish: bool) -> dict:
    topic = params.get("topic", "")
    genre = params.get("genre", "دليل عملي / How-to")
    chapters_count = int(params.get("chapters", 5))
    price_cents = int(params.get("price_cents", 500))

    final_text, title = "", topic
    for event_type, payload in generate_full_book(client, topic, genre, language, chapters_count):
        if event_type == "outline":
            title = payload.get("title", topic)
        elif event_type == "done":
            final_text = payload

    if not publish:
        return {"success": True, "message": f"📖 الكتاب '{title}' جاهز (نص فقط، ماتنشرش):\n\n{final_text[:1500]}..."}

    path = f"generated_books/{slugify(title)}.md"
    os.makedirs("generated_books", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(final_text)

    result = publish_book(path, title, price_cents, f"<p>{title}</p>", "ebook")
    if result["success"]:
        add_product(title, result["buy_link"], price_cents, "book", topic)
        log_operation("book", "success", message=result["buy_link"], product_name=title)
        return {"success": True, "message": f"✅ الكتاب '{title}' نشر بنجاح: {result['buy_link']}"}
    log_operation("book", "failed", message=result["error"], product_name=title)
    return {"success": False, "message": f"❌ فشل النشر: {result['error']}"}


def _run_comic(client: Groq, params: dict, language: str, publish: bool) -> dict:
    mode = params.get("mode", "prompt")
    topic = params.get("topic", "")
    user_script = params.get("user_script", "")
    panels_count = int(params.get("panels", 10))
    price_cents = int(params.get("price_cents", 400))

    script = generate_comic_script(client, language, panels_count, mode, topic, user_script)
    if "error" in script:
        return {"success": False, "message": f"❌ فشل بناء السيناريو: {script['error']}"}

    title = script.get("title", topic or "قصة مصورة")
    panels = script["panels"]

    if not publish:
        return {"success": True, "message": f"🖼️ سيناريو '{title}' جاهز ({len(panels)} لوحة) — ماتولدش الصور حيت publish=false."}

    output_dir = f"generated_comics/{slugify(title)}"
    images_result = generate_panel_images(panels, output_dir)
    if not images_result["success"]:
        return {"success": False, "message": f"❌ فشل توليد الصور: {images_result['errors']}"}

    pdf_path = os.path.join(output_dir, "comic.pdf")
    pdf_result = compile_comic_to_pdf(panels, images_result["image_paths"], pdf_path, language)
    if not pdf_result["success"]:
        return {"success": False, "message": f"❌ فشل تجميع PDF: {pdf_result['error']}"}

    result = publish_book(pdf_path, title, price_cents, f"<p>{title}</p>", "digital")
    if result["success"]:
        add_product(title, result["buy_link"], price_cents, "comic", topic or user_script[:200])
        log_operation("comic", "success", message=result["buy_link"], product_name=title)
        return {"success": True, "message": f"✅ القصة المصورة '{title}' نشرات بنجاح: {result['buy_link']}"}
    log_operation("comic", "failed", message=result["error"], product_name=title)
    return {"success": False, "message": f"❌ فشل النشر: {result['error']}"}


def _run_coloring_book(params: dict, publish: bool) -> dict:
    theme = params.get("theme", "")
    pages_count = int(params.get("pages", 8))
    price_cents = int(params.get("price_cents", 300))

    output_dir = f"generated_coloring_books/{slugify(theme)}"
    book_result = generate_coloring_book(theme, pages_count, output_dir)
    if not book_result["success"]:
        return {"success": False, "message": f"❌ فشل توليد الصور: {book_result['errors']}"}

    if not publish:
        return {"success": True, "message": f"🎨 كتاب التلوين '{theme}' جاهز (الصور فـ {output_dir})، ماتنشرش."}

    image_paths = ([book_result["cover"]] if book_result["cover"] else []) + book_result["pages"]
    pdf_path = os.path.join(output_dir, "coloring_book.pdf")
    pdf_result = compile_images_to_pdf(image_paths, pdf_path)
    if not pdf_result["success"]:
        return {"success": False, "message": f"❌ فشل تجميع PDF: {pdf_result['error']}"}

    product_name = f"كتاب تلوين للأطفال: {theme}"
    result = publish_book(pdf_path, product_name, price_cents, f"<p>{theme}</p>", "digital")
    if result["success"]:
        add_product(product_name, result["buy_link"], price_cents, "coloring_book", theme)
        log_operation("coloring_book", "success", message=result["buy_link"], product_name=product_name)
        return {"success": True, "message": f"✅ كتاب التلوين '{theme}' نشر بنجاح: {result['buy_link']}"}
    log_operation("coloring_book", "failed", message=result["error"], product_name=product_name)
    return {"success": False, "message": f"❌ فشل النشر: {result['error']}"}


def _run_poster_or_logo(kind: str, params: dict, publish: bool) -> dict:
    price_cents = int(params.get("price_cents", 200))
    output_dir = "generated_visuals"
    os.makedirs(output_dir, exist_ok=True)

    if kind == "poster":
        topic = params.get("topic", "")
        style = params.get("style", "modern minimal")
        path = os.path.join(output_dir, f"{slugify(topic)}_poster.jpg")
        result = generate_poster(topic, style, path)
        name = f"ملصق رقمي: {topic}"
    else:
        brand_name = params.get("brand_name", "")
        style_keywords = params.get("style_keywords", "clean, professional")
        path = os.path.join(output_dir, f"{slugify(brand_name)}_logo.jpg")
        result = generate_logo(brand_name, style_keywords, path)
        name = f"شعار: {brand_name}"

    if not result["success"]:
        return {"success": False, "message": f"❌ فشل توليد الصورة: {result['error']}"}
    if not publish:
        return {"success": True, "message": f"🎨 '{name}' جاهز فـ {path}، ماتنشرش."}

    publish_result = publish_book(path, name, price_cents, f"<p>{name}</p>", "digital")
    if publish_result["success"]:
        add_product(name, publish_result["buy_link"], price_cents, kind)
        log_operation(kind, "success", message=publish_result["buy_link"], product_name=name)
        return {"success": True, "message": f"✅ '{name}' نشر بنجاح: {publish_result['buy_link']}"}
    log_operation(kind, "failed", message=publish_result["error"], product_name=name)
    return {"success": False, "message": f"❌ فشل النشر: {publish_result['error']}"}


def _run_news_blog(client: Groq, params: dict, language: str) -> dict:
    topic = params.get("topic", "")
    language_code = params.get("language_code", "en")
    news = fetch_real_news(topic, language_code)
    if not news["success"]:
        return {"success": False, "message": f"❌ فشل جلب الأخبار: {news['error']}"}
    post = generate_blog_post(client, topic, news["articles"], language)
    return {"success": True, "message": post}


def _run_engineering(client: Groq, params: dict, command: str) -> dict:
    description = params.get("description") or command
    result = design_part(client, description)
    if not result["success"]:
        log_operation("engineering", "failed", message=result.get("error", ""), product_name=description[:60])
        return {"success": False, "message": f"❌ فشل التصميم: {result.get('error')}"}

    log_operation("engineering", "success", message=result["stl_path"], product_name=result["spec"].get("part_name", ""))
    s = result["strength_analysis"]
    return {
        "success": True,
        "message": (
            f"⚙️ الشكل: {result['shape_type']} | القطعة: {result['spec'].get('part_name')}\n"
            f"الملف: {result['stl_path']}\n"
            f"إجهاد: {s.get('bending_stress_mpa')} MPa | معامل الأمان: {s.get('factor_of_safety')}\n"
            f"{s.get('verdict')}\n\n{result['disclaimer']}"
        ),
    }



def _run_engineering_project(client: Groq, params: dict, command: str) -> dict:
    description = params.get("description") or command
    result = design_project(client, description)
    if not result["success"] and not result["parts_results"]:
        log_operation("engineering", "failed", message=result.get("error", ""), product_name=description[:60])
        return {"success": False, "message": f"❌ فشل تفكيك المشروع: {result.get('error')}"}

    lines = [f"🏗️ المشروع: {result['project_name']} — {len(result['parts_results'])} قطعة"]
    for p in result["parts_results"]:
        if p.get("skipped"):
            lines.append(f"⏭️ {p['part_name']} ({p['function']}) — {p['reason']}")
        elif p["success"]:
            s = p.get("strength_analysis", {})
            lines.append(f"✅ {p['part_name']} ({p['function']}) — {p['stl_path']} — FoS: {s.get('factor_of_safety')}")
            log_operation("engineering", "success", message=p["stl_path"], product_name=p["part_name"])
        else:
            lines.append(f"❌ {p['part_name']} — {p.get('error')}")
            log_operation("engineering", "failed", message=p.get("error", ""), product_name=p["part_name"])

    lines.append("\n⚠️ كل القطع مسودات للدراسة — مراجعة مهندس مرخص خاصة قبل أي تصنيع حقيقي.")
    return {"success": True, "message": "\n".join(lines)}


def _run_electronics(client: Groq, params: dict, command: str) -> dict:
    description = params.get("description") or command
    result = design_circuit(client, description)
    if not result.get("success"):
        log_operation("electronics", "failed", message=result.get("error", ""), product_name=description[:60])
        return {"success": False, "message": f"❌ فشل الحساب: {result.get('error')}"}

    c = result["calculation"]
    circuit_type = result.get("circuit_type", "led")
    name = result["spec"].get("circuit_name") or result["spec"].get("device_name", "")
    log_operation("electronics", "success", message=json.dumps(c, ensure_ascii=False)[:100], product_name=name)

    if circuit_type == "voltage_divider":
        message = (
            f"🔌 مقسم الجهد: {name}\n"
            f"R1 = {c['r1_ohm']}Ω | R2 = {c['r2_ohm']}Ω\n"
            f"الجهد الفعلي: {c['actual_output_voltage_v']}V (خطأ: {c['error_percent']}%)\n"
            f"التيار الكلي: {c['total_current_ma']} mA\n"
        )
    elif circuit_type == "battery_runtime":
        message = (
            f"🔋 عمر البطارية: {name}\n"
            f"مجموع الاستهلاك: {c['total_current_draw_ma']} mA\n"
            f"العمر المقدر (أسوأ حالة): {c['estimated_runtime_hours_worst_case']} ساعة "
            f"({c['estimated_runtime_days_worst_case']} يوم)\n{c['note']}\n"
        )
    else:
        message = (
            f"🔌 الدارة: {name}\n"
            f"المقاومة المطلوبة: {c['standard_resistance_ohm']}Ω (القدرة الاسمية: {c['recommended_resistor_wattage_w']}W)\n"
            f"التيار الفعلي: {c['actual_current_ma']} mA | تبديد القدرة: {c['power_dissipation_w']} W\n"
        )
        if "estimated_battery_life_hours" in c:
            message += f"عمر البطارية المقدر: {c['estimated_battery_life_hours']} ساعة\n"

    message += f"\n{result['disclaimer']}"
    return {"success": True, "message": message}


def _run_cloud_architecture(client: Groq, params: dict, command: str) -> dict:
    description = params.get("description") or command
    result = design_cloud_architecture(client, description)
    if not result.get("success"):
        log_operation("cloud", "failed", message=result.get("error", ""), product_name=description[:60])
        return {"success": False, "message": f"❌ فشل تصميم البنية: {result.get('error')}"}

    log_operation("cloud", "success", message=result.get("architecture_name", ""), product_name=description[:60])
    components_text = "\n".join(f"- **{c['name']}** ({c['suggested_tech']}): {c['role']}" for c in result["components"])
    security_text = "\n".join(f"- {s}" for s in result.get("security_notes", []))

    message = (
        f"☁️ البنية: {result['architecture_name']}\n{result['summary']}\n\n"
        f"**المكونات:**\n{components_text}\n\n"
        f"**تدفق البيانات:** {result['data_flow']}\n\n"
        f"**الأمان:**\n{security_text}\n\n"
        f"**التوسع:** {result['scalability_notes']}\n"
        f"**تقدير التكلفة الشهرية:** {result['estimated_monthly_cost_range_usd']}\n\n"
        f"```mermaid\n{result['mermaid_diagram']}\n```\n\n{result['disclaimer']}"
    )
    return {"success": True, "message": message}


def _run_status(params: dict) -> dict:
    query = params.get("query", "")
    catalog = search_catalog(query, max_results=10) if query else load_catalog()[-10:]
    if not catalog:
        return {"success": True, "message": "ماكاينش شي منتج منشور بعد فالفهرس."}
    lines = [f"- {p['name']} ({p['price_cents']/100:.2f}$): {p['buy_link']}" for p in catalog]
    return {"success": True, "message": "آخر المنتجات:\n" + "\n".join(lines)}


# ---------------------------------------------------------------------------
# 3) نقطة الدخول الوحيدة
# ---------------------------------------------------------------------------
def handle_command(command: str, language: str = "العربية", groq_api_key: str = None) -> dict:
    client = Groq(api_key=groq_api_key or os.environ["GROQ_API_KEY"])
    intent = classify_intent(client, command, language)
    action = intent.get("action", "unknown")
    publish = intent.get("publish", False)
    params = intent.get("parameters", {})

    if action == "marketing":
        return _run_marketing(client, params, language)
    elif action == "book":
        return _run_book(client, params, language, publish)
    elif action == "comic":
        return _run_comic(client, params, language, publish)
    elif action == "coloring_book":
        return _run_coloring_book(params, publish)
    elif action in ("poster", "logo"):
        return _run_poster_or_logo(action, params, publish)
    elif action == "news_blog":
        return _run_news_blog(client, params, language)
    elif action == "engineering_part":
        return _run_engineering(client, params, command)
    elif action == "engineering_project":
        return _run_engineering_project(client, params, command)
    elif action == "electronics_circuit":
        return _run_electronics(client, params, command)
    elif action == "cloud_architecture":
        return _run_cloud_architecture(client, params, command)
    elif action == "status":
        return _run_status(params)
    elif action == "error":
        return {"success": False, "message": f"⚠️ خطأ فالفهم: {params.get('error')}"}
    else:
        return {"success": False, "message": "🤔 مافهمتش الأمر بالضبط. جرب تعاود صياغتو بشكل أوضح (مثلاً: 'سولي كتاب على...' ولا 'ولد ملصق على...')."}
