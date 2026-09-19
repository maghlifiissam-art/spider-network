"""Base class shared by every spider in the Spider Network.

Every spider is a specialized agent with:
  - a dedicated persona and system prompt
  - robust Groq API calls (retries with exponential backoff)
  - structured, comparable results (SpiderResult) that can be logged/mailed
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from groq import Groq

DEFAULT_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


@dataclass
class SpiderResult:
    """Comparable result of one spider run."""

    spider: str
    task: str
    output: str
    ok: bool
    error: str = ""
    elapsed_seconds: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    def to_dict(self) -> dict:
        return {
            "spider": self.spider,
            "task": self.task,
            "ok": self.ok,
            "error": self.error,
            "elapsed_seconds": self.elapsed_seconds,
            "timestamp": self.timestamp,
            "output": self.output,
        }


class BaseSpider:
    """A single specialized spider agent."""

    name: str = "base"
    title: str = "Base Spider"
    persona: str = ""
    instructions: str = ""
    output_format: str = ""

    def __init__(self, client=None, model=None, temperature=0.7, max_tokens=4096):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to your environment, "
                "Streamlit secrets, or GitHub Actions secrets."
            )
        self.client = client or Groq(api_key=api_key)
        self.model = model or DEFAULT_MODEL
        self.temperature = temperature
        self.max_tokens = max_tokens

    @property
    def system_prompt(self) -> str:
        return "\n\n".join(
            part for part in (self.persona, self.instructions, self.output_format) if part
        ).strip()

    def run(self, task: str, retries: int = 2) -> SpiderResult:
        """Run the spider on a task, retrying transient Groq failures."""
        last_error = None
        for attempt in range(retries + 1):
            try:
                start = time.time()
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": task},
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                text = (completion.choices[0].message.content or "").strip()
                elapsed = round(time.time() - start, 2)
                if not text:
                    raise RuntimeError("Empty response from model")
                return SpiderResult(
                    spider=self.name, task=task, output=text, ok=True,
                    elapsed_seconds=elapsed,
                )
            except Exception as exc:  # transient API/network errors
                last_error = exc
                if attempt < retries:
                    time.sleep(2 ** attempt)
        return SpiderResult(
            spider=self.name, task=task, output="", ok=False, error=str(last_error)
        )
