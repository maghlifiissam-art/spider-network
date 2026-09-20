"""
cloud_architect_spider.py — وكيل البنية السحابية
------------------------------------------------------------------
هذا مجال مختلف عن الميكانيك/الإلكترونيات: البنية السحابية هي فعلاً
"برمجة/معمارية أنظمة" — الـ LLM هنا كفؤ فعلاً (ماشي بحال حساب قوة مادة)،
لأن المعرفة بأنماط الأنظمة (microservices, API gateway, auth...) هي
معرفة نصية/مفاهيمية موثقة بزاف، ماشي فيزياء تتطلب حساب دقيق.

⚠️ رغم هذا: الأرقام التقديرية (التكلفة الشهرية، السعة) هي **تقديرات
عامة تقريبية**، ماشي عرض أسعار حقيقي — الأسعار الفعلية كتختلف حسب
المزود (AWS/GCP/Azure) والاستعمال الفعلي، وخاصها تتحقق من موقع المزود
مباشرة قبل أي قرار مالي.
"""

import json
from groq import Groq

MODEL = "llama-3.1-8b-instant"


def design_cloud_architecture(client: Groq, product_description: str) -> dict:
    system_prompt = """You are a senior cloud solutions architect. Read the product/feature \
description and design a realistic, production-grade cloud architecture for it, using \
well-established patterns (API Gateway, load balancer, microservices or monolith as \
appropriate, managed database, caching, CDN, authentication, monitoring).

Respond ONLY with valid JSON, no markdown fences:
{
  "architecture_name": "...",
  "summary": "2-3 sentences explaining the overall approach and why",
  "components": [
    {"name": "...", "role": "what it does", "suggested_tech": "e.g. AWS API Gateway / PostgreSQL / Redis / Cloudflare CDN"}
  ],
  "data_flow": "a short paragraph describing how a request flows through the system, step by step",
  "security_notes": ["short bullet points on auth, encryption, data privacy"],
  "scalability_notes": "how this architecture handles growth",
  "estimated_monthly_cost_range_usd": "a rough range like '$50-300/month for early stage', clearly marked as a rough estimate",
  "mermaid_diagram": "a valid Mermaid flowchart (graph TD) showing the components and data flow, as a single string with \\n for newlines"
}"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": product_description},
            ],
            temperature=0.4,
            max_tokens=1500,
        )
        result = json.loads(response.choices[0].message.content.strip())
        result["success"] = True
        result["disclaimer"] = (
            "⚠️ هذه بنية مقترحة بناءً على أنماط هندسية معروفة وموثقة، صالحة كنقطة انطلاق. "
            "التكلفة والسعة تقديرات تقريبية فقط — تحقق دائماً من حاسبة التسعير الرسمية لمزود "
            "السحابة (AWS/GCP/Azure) قبل أي التزام، وراجع مهندس DevOps/أمان قبل الإنتاج الفعلي."
        )
        return result
    except json.JSONDecodeError:
        return {"success": False, "error": "فشل النموذج فإرجاع معمارية صالحة (JSON)."}
    except Exception as e:
        return {"success": False, "error": str(e)}
