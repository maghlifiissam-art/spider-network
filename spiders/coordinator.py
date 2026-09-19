"""Queen Spider: LangGraph coordinator for the Spider Network.

The queen analyzes an incoming task, decides which specialist spiders should
work on it, fans the work out in parallel, then collects a combined report.
"""

from __future__ import annotations

import json
import re
import os
from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from groq import Groq

from .base import BaseSpider, DEFAULT_MODEL


class SpiderState(TypedDict, total=False):
    task: str
    targets: list          # spider names chosen by the queen
    results: dict          # spider name -> SpiderResult.to_dict()
    combined: str          # final combined report


QUEEN_PROMPT = """You are the Queen Spider of the Spider Network: a task router.
Given a task, decide which specialist spiders should handle it.

Available spiders:
- affiliate: market analysis, niches, affiliate strategy, email swipes, promotions
- media: ad hooks, Reels/TikTok scripts, funnels, ad copy
- digital_products: e-books, micro-courses, pricing, SEO content strategy
- engineering: mechanical part design, dimensions, strength calculations, CAD drafts
- electronics: circuits, LED/resistor/battery calculations, component selection

Rules:
- Answer with ONLY a JSON array of spider names, e.g. ["affiliate", "media"].
- Choose all spiders that add real value (1 to 5 names).
- If unsure, choose the single most relevant one."""


class QueenCoordinator:
    """Build and run the LangGraph coordination flow."""

    def __init__(self, spider_classes: dict[str, type[BaseSpider]] | None = None,
                 model: str | None = None):
        from . import ALL_SPIDERS
        self.spider_classes = spider_classes or ALL_SPIDERS
        self.model = model or DEFAULT_MODEL
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set")
        self.client = Groq(api_key=api_key)
        self._spiders: dict[str, BaseSpider] = {}

    # ---- nodes ----
    def queen_node(self, state: SpiderState) -> dict:
        """Route: LLM picks target spiders, with a deterministic fallback."""
        task = state["task"]
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": QUEEN_PROMPT},
                    {"role": "user", "content": task},
                ],
                temperature=0.0,
                max_tokens=256,
            )
            text = (completion.choices[0].message.content or "").strip()
            match = re.search(r"\[.*?\]", text, re.S)
            targets = json.loads(match.group(0)) if match else []
            targets = [t for t in targets if t in self.spider_classes]
        except Exception:
            targets = []
        if not targets:  # fallback: run every spider that mentions keywords
            targets = self._keyword_fallback(task)
        return {"targets": targets}

    def _keyword_fallback(self, task: str) -> list[str]:
        keys = {
            "affiliate": ["أفلييت", "affiliate", "نيش", "نيتش", "niche", "ترند", "بيع",
                          "تسويق", "بريد", "email", "promo", "حملة"],
            "media": ["إعلان", "اعلان", "ad", "hook", "هوك", "ريل", "reel", "tiktok",
                      "فيديو", "funnel"],
            "digital_products": ["كتاب", "ebook", "دورة", "course", "منتج رقمي",
                                 "pricing", "تسعير", "seo", "مدونة", "blog"],
            "engineering": ["قطعة", "bracket", "هندسة", "أبعاد", "تصميم", "cad",
                             "ميكانيك", "طباعة 3d"],
            "electronics": ["دائرة", "circuit", "led", "مقاومة", "resistor", "بطارية",
                             "battery", "إلكترون", "جهد"],
        }
        low = task.lower()
        return [name for name, words in keys.items()
                if any(w.lower() in low for w in words)] or ["digital_products"]

    def _make_spider_node(self, name: str):
        def node(state: SpiderState) -> dict:
            spider = self._spiders.get(name) or self._spiders.setdefault(
                name, self.spider_classes[name]()
            )
            result = spider.run(state["task"])
            results = dict(state.get("results", {}))
            results[name] = result.to_dict()
            return {"results": results}
        node.__name__ = f"{name}_node"
        return node

    def collect_node(self, state: SpiderState) -> dict:
        parts = []
        for name, res in state.get("results", {}).items():
            if res["ok"]:
                parts.append(f"## 🕷️ {name}\n{res['output']}")
            else:
                parts.append(f"## 🕷️ {name}\n⚠️ فشل التشغيل: {res['error']}")
        combined = f"# تقرير شبكة العناكب\n\nالمهمة: {state['task']}\n\n" + "\n\n---\n\n".join(parts)
        return {"combined": combined}

    def route_from_queen(self, state: SpiderState) -> list[str]:
        return state["targets"] or list(self.spider_classes)[:1]

    # ---- graph ----
    def build(self) -> StateGraph:
        graph = StateGraph(SpiderState)
        graph.add_node("queen", self.queen_node)
        for name in self.spider_classes:
            graph.add_node(name, self._make_spider_node(name))
        graph.add_node("collect", self.collect_node)

        graph.add_edge(START, "queen")
        graph.add_conditional_edges(
            "queen", self.route_from_queen, list(self.spider_classes)
        )
        for name in self.spider_classes:
            graph.add_edge(name, "collect")
        graph.add_edge("collect", END)
        return graph.compile()

    def run(self, task: str) -> SpiderState:
        """Run a task through the full spider network."""
        app = self.build()
        return app.invoke({"task": task})
