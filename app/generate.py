"""Grounded generation. Answers only from retrieved context, with [n] citations.

Provider is switchable (anthropic | openai), mirroring a real multi-provider
setup: cheap default model, abstracted behind one call site.
"""

from .config import get_settings
from .retrieval import Hit

_SYSTEM = (
    "You answer questions using ONLY the provided context passages. "
    "Cite the passages you use with bracketed numbers like [1], [2]. "
    "If the answer is not in the context, say you don't know rather than guessing. "
    "Be concise and concrete."
)


def _format_context(hits: list[Hit]) -> str:
    blocks = []
    for i, h in enumerate(hits, start=1):
        blocks.append(f"[{i}] source: {h.source}\n{h.content}")
    return "\n\n".join(blocks)


def _user_prompt(query: str, hits: list[Hit]) -> str:
    return f"Context passages:\n\n{_format_context(hits)}\n\nQuestion: {query}\n\nAnswer with citations:"


def _answer_anthropic(prompt: str) -> str:
    from anthropic import Anthropic

    s = get_settings()
    client = Anthropic(api_key=s.anthropic_api_key)
    msg = client.messages.create(
        model=s.anthropic_model,
        max_tokens=700,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in msg.content if block.type == "text")


def _answer_openai(prompt: str) -> str:
    from openai import OpenAI

    s = get_settings()
    client = OpenAI(api_key=s.openai_api_key)
    resp = client.chat.completions.create(
        model=s.openai_model,
        max_tokens=700,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": prompt},
        ],
    )
    return resp.choices[0].message.content or ""


def generate_answer(query: str, hits: list[Hit]) -> str:
    if not hits:
        return "I don't have any indexed context to answer that."
    prompt = _user_prompt(query, hits)
    provider = get_settings().gen_provider.lower()
    if provider == "openai":
        return _answer_openai(prompt)
    return _answer_anthropic(prompt)
