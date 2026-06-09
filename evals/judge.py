"""LLM-as-judge for answer quality (reference-free).

Scores a generated answer against the retrieved context on two axes:
  - faithfulness:     are the answer's claims supported by the context?
  - answer_relevance: does the answer actually address the question?

Uses the same provider/model as generation (default Claude Haiku). Costs
tokens, so it runs only behind `run_eval --judge`.
"""

import json
import re

from app.config import get_settings

_RUBRIC = (
    "You are a strict evaluator of a retrieval-augmented answer. "
    "Score two axes, each an integer 1-5:\n"
    "- faithfulness: are ALL claims in the answer supported by the context passages? "
    "5 = fully grounded, 1 = mostly unsupported/hallucinated.\n"
    "- answer_relevance: does the answer directly address the question? "
    "5 = directly and completely, 1 = off-topic.\n"
    'Respond with ONLY a JSON object: {"faithfulness": int, "answer_relevance": int, "rationale": "one sentence"}'
)


def _parse(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return {"faithfulness": None, "answer_relevance": None, "rationale": text[:200]}


def judge_answer(question: str, answer: str, contexts: list[str]) -> dict:
    s = get_settings()
    ctx = "\n\n".join(f"[{i + 1}] {c}" for i, c in enumerate(contexts))
    prompt = f"Question: {question}\n\nAnswer: {answer}\n\nContext passages:\n{ctx}"

    if s.gen_provider.lower() == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=s.openai_api_key)
        resp = client.chat.completions.create(
            model=s.openai_model,
            max_tokens=300,
            messages=[
                {"role": "system", "content": _RUBRIC},
                {"role": "user", "content": prompt},
            ],
        )
        return _parse(resp.choices[0].message.content or "")

    from anthropic import Anthropic

    client = Anthropic(api_key=s.anthropic_api_key)
    msg = client.messages.create(
        model=s.anthropic_model,
        max_tokens=300,
        system=_RUBRIC,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse("".join(b.text for b in msg.content if b.type == "text"))
