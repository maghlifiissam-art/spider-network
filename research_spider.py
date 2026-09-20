"""
research_spider.py — وكيل هجين للبحث والتخصص العلمي
========================================================================
"هجين" لأنه كيجمع بين مصدرين حقيقيين مختلفين حسب التخصص:
  - Semantic Scholar (200 مليون+ ورقة، كل التخصصات، مجاني بلا مفتاح)
  - arXiv (أحدث الأبحاث/Preprints فالفيزياء/الحاسوب/الرياضيات، مجاني بالكامل)

نفس مبدأ news_spider.py: التلخيص كيُبنى **فقط** على الأوراق الحقيقية
اللي تجابو، بلا اختلاق نتائج أو استنتاجات ماكانتش فالمصدر. كل ملخص
كيرفق بقائمة مصادر حقيقية (عنوان + رابط + سنة).

⚠️ هذا أداة تسريع للبحث الأولي/الاستكشاف — ماشي بديل عن قراءة الأوراق
الأصلية بالكامل قبل الاعتماد عليها فقرار علمي أو أكاديمي مهم.
"""

import requests
import xml.etree.ElementTree as ET
from groq import Groq

MODEL = "llama-3.1-8b-instant"
SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
ARXIV_URL = "http://export.arxiv.org/api/query"


# ---------------------------------------------------------------------------
# 1) تصنيف التخصص باش نقرر أي مصدر نستعملو (هذا هو الجانب "الهجين")
# ---------------------------------------------------------------------------
def classify_research_domain(client: Groq, query: str) -> str:
    system_prompt = """Classify the research query into exactly one category:
"physics_cs_math" (physics, computer science, mathematics, engineering — arXiv is a strong source)
"general" (any other field: biology, medicine, social science, economics, etc.)
Respond with ONLY the single word: physics_cs_math or general"""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": query}],
            temperature=0,
            max_tokens=10,
        )
        answer = response.choices[0].message.content.strip().lower()
        return "physics_cs_math" if "physics" in answer or "cs_math" in answer else "general"
    except Exception:
        return "general"


# ---------------------------------------------------------------------------
# 2أ) Semantic Scholar — المصدر العام (كل التخصصات)
# ---------------------------------------------------------------------------
def search_semantic_scholar(query: str, max_results: int = 5) -> dict:
    try:
        resp = requests.get(
            SEMANTIC_SCHOLAR_URL,
            params={
                "query": query,
                "limit": max_results,
                "fields": "title,abstract,year,authors,venue,url,citationCount,openAccessPdf",
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        papers = [
            {
                "title": p.get("title", ""),
                "abstract": (p.get("abstract") or "")[:500],
                "year": p.get("year"),
                "authors": ", ".join(a.get("name", "") for a in (p.get("authors") or [])[:3]),
                "venue": p.get("venue", ""),
                "citation_count": p.get("citationCount", 0),
                "url": p.get("url", ""),
                "source": "Semantic Scholar",
            }
            for p in data.get("data", [])
        ]
        return {"success": True, "papers": papers, "error": None}
    except requests.exceptions.RequestException as e:
        return {"success": False, "papers": [], "error": str(e)}


# ---------------------------------------------------------------------------
# 2ب) arXiv — مصدر متخصص (فيزياء/حاسوب/رياضيات)، أحدث الـ preprints
# ---------------------------------------------------------------------------
def search_arxiv(query: str, max_results: int = 5) -> dict:
    try:
        resp = requests.get(
            ARXIV_URL,
            params={"search_query": f"all:{query}", "start": 0, "max_results": max_results, "sortBy": "relevance"},
            timeout=20,
        )
        resp.raise_for_status()
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(resp.content)

        papers = []
        for entry in root.findall("atom:entry", ns):
            title = entry.find("atom:title", ns)
            summary = entry.find("atom:summary", ns)
            published = entry.find("atom:published", ns)
            link = entry.find("atom:id", ns)
            authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)]

            papers.append({
                "title": (title.text or "").strip().replace("\n", " "),
                "abstract": (summary.text or "").strip().replace("\n", " ")[:500],
                "year": published.text[:4] if published is not None else None,
                "authors": ", ".join(authors[:3]),
                "venue": "arXiv (preprint)",
                "citation_count": None,
                "url": link.text if link is not None else "",
                "source": "arXiv",
            })
        return {"success": True, "papers": papers, "error": None}
    except (requests.exceptions.RequestException, ET.ParseError) as e:
        return {"success": False, "papers": [], "error": str(e)}


# ---------------------------------------------------------------------------
# 3) البحث الهجين: يقرر المصدر (أو الاثنين) حسب التخصص
# ---------------------------------------------------------------------------
def hybrid_search(client: Groq, query: str, max_results: int = 5) -> dict:
    domain = classify_research_domain(client, query)
    all_papers = []
    errors = []

    s2_result = search_semantic_scholar(query, max_results)
    if s2_result["success"]:
        all_papers.extend(s2_result["papers"])
    else:
        errors.append(f"Semantic Scholar: {s2_result['error']}")

    if domain == "physics_cs_math":
        arxiv_result = search_arxiv(query, max_results)
        if arxiv_result["success"]:
            all_papers.extend(arxiv_result["papers"])
        else:
            errors.append(f"arXiv: {arxiv_result['error']}")

    return {"success": len(all_papers) > 0, "domain": domain, "papers": all_papers, "errors": errors}


# ---------------------------------------------------------------------------
# 4) تلخيص مبني على الأوراق الحقيقية فقط (بلا اختلاق)
# ---------------------------------------------------------------------------
def summarize_research(client: Groq, query: str, papers: list, language: str) -> str:
    if not papers:
        return "⚠️ ماكاينش أوراق علمية حقيقية باش نبنيو عليها ملخص."

    papers_text = "\n\n".join(
        f"[{i+1}] {p['title']} ({p.get('year', '?')}) — {p['authors']} — {p['source']}\n{p['abstract']}"
        for i, p in enumerate(papers)
    )

    system_prompt = f"""You are a careful research assistant. Write a summary in {language} about \
"{query}", based STRICTLY and ONLY on the paper abstracts provided below. Do not invent findings, \
numbers, or conclusions not present in these abstracts. If the abstracts disagree or cover \
different angles, mention that.

Structure: a short overview paragraph, then key findings per relevant paper, then a \
"المصادر / Sources" section listing each paper's title, authors, year, and source (Semantic \
Scholar/arXiv) exactly as given — do not include fabricated DOIs or links you weren't given."""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Papers found:\n\n{papers_text}"},
            ],
            temperature=0.4,
            max_tokens=1200,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ خطأ فالتلخيص: {e}"


# ---------------------------------------------------------------------------
# 5) نقطة الدخول الشاملة
# ---------------------------------------------------------------------------
def research_topic(client: Groq, query: str, language: str = "العربية", max_results: int = 5) -> dict:
    search_result = hybrid_search(client, query, max_results)
    if not search_result["success"]:
        return {"success": False, "error": "؛ ".join(search_result["errors"]) or "ماكاينش نتائج."}

    summary = summarize_research(client, query, search_result["papers"], language)
    return {
        "success": True,
        "domain": search_result["domain"],
        "papers": search_result["papers"],
        "summary": summary,
        "disclaimer": "⚠️ ملخص أولي مبني على ملخصات (abstracts) حقيقية — راجع الأوراق الأصلية كاملة قبل الاعتماد عليها فقرار علمي/أكاديمي مهم.",
    }
