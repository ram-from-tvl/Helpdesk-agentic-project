import json

KNOWLEDGE_BASE = {
    "remote_work": "Remote work is allowed up to 3 days per week with manager approval.",
    "refund_policy": "Refunds are allowed within 14 days for eligible purchases.",
    "sla": "P1 tickets are acknowledged within 15 minutes.",
    "security": "Never share customer secrets or API keys in chat replies.",
}


def fetch_knowledge(query: str, top_k: int = 2) -> str:
    """Keyword retrieval used by the graph and by Level 1 tests."""
    query_lower = query.lower()
    results = []
    for key, text in KNOWLEDGE_BASE.items():
        if any(token in text.lower() for token in query_lower.split()):
            results.append({"id": key, "content": text})
    return json.dumps(results[:top_k])


def rank_candidate_answers(candidates_json: str, query: str) -> str:
    """Simple ranker that picks the most overlapping candidate with the query."""
    try:
        candidates = json.loads(candidates_json)
    except Exception:
        return "Invalid JSON input."

    if not candidates:
        return "No valid candidates found."

    q_tokens = set(query.lower().split())
    ranked = sorted(
        candidates,
        key=lambda c: len(q_tokens.intersection(set(c.get("content", "").lower().split()))),
        reverse=True,
    )
    return json.dumps(ranked[0])


def build_support_response(query: str, policy_text: str) -> str:
    """Prompt/template builder function used for deterministic Level 1 checks."""
    return (
        f"Context:\\n{policy_text}\\n\\n"
        f"Question: {query}\\n"
        "Answer with policy-grounded guidance only."
    )
