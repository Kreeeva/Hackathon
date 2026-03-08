from __future__ import annotations

import json
import os
from typing import List, Tuple

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from .models import EvidenceItem


LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(model=LLM_MODEL, temperature=0.1)
    return _llm

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a fraud analyst generating short and long explanations for alerts.\n"
                "You MUST obey these rules:\n"
                "- Use ONLY the structured evidence provided.\n"
                "- Do NOT invent accounts, devices, IPs, or amounts.\n"
                "- Do NOT guess or state probabilities.\n"
                "- Mention pattern names when present (star_pattern, circular_flow, flagged_association).\n"
                "- Be clear and concise.\n"
            ),
        ),
        (
            "user",
            (
                "Risk score: {risk_score}\n"
                "Severity: {severity}\n"
                "Evidence (JSON): {evidence_json}\n\n"
                "Return a JSON object with keys 'short' (one sentence) and 'long' "
                "(a concise analyst-style explanation of a few sentences)."
            ),
        ),
    ]
)


def _evidence_to_dict(e: EvidenceItem) -> dict:
    return e.model_dump() if hasattr(e, "model_dump") else e.dict()


async def generate_explanations(
    evidence: List[EvidenceItem],
    risk_score: int,
    severity: str,
) -> Tuple[str, str]:
    evidence_json = json.dumps([_evidence_to_dict(e) for e in evidence], default=str)
    chain = prompt | _get_llm()
    resp = await chain.ainvoke(
        {
            "risk_score": risk_score,
            "severity": severity,
            "evidence_json": evidence_json,
        }
    )

    text = resp.content
    short = ""
    long = ""
    try:
        data = json.loads(text)
        short = str(data.get("short", "")).strip()
        long = str(data.get("long", "")).strip()
    except Exception:
        # Fallback: treat the full text as the long explanation.
        long = text.strip()
        if "\n" in long:
            short = long.split("\n", 1)[0]
        else:
            short = long

    return short, long

