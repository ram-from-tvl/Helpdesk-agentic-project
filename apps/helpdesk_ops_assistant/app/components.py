import json

POLICY_KB = {
    "remote_work": "Remote work is allowed up to 3 days per week with manager approval.",
    "refund_policy": "Refunds are not allowed under any circumstances.",
    "p1_sla": "P1 incidents must be acknowledged within 15 minutes.",
    "security": "Customer secrets and credentials must never be shared in responses.",
}


def fetch_policy_context(query: str, top_k: int = 2) -> str:
    """Retrieve policy snippets relevant to the incoming support query."""
    stopwords = {"what", "is", "the", "a", "an", "of", "for", "to", "and", "policy"}
    query_terms = [t for t in query.lower().replace("?", "").split() if t not in stopwords and len(t) >= 2]
    scored = []
    for key, text in POLICY_KB.items():
        text_lower = text.lower()
        overlap = sum(1 for term in query_terms if term in text_lower)
        if overlap > 0:
            scored.append((overlap, {"id": key, "content": text}))

    scored.sort(key=lambda item: item[0], reverse=True)
    matches = [item[1] for item in scored]
    return json.dumps(matches[:top_k])


def select_best_policy(candidate_docs_json: str, query: str) -> str:
    """Rank candidate policy snippets and return the best matching one."""
    try:
        docs = json.loads(candidate_docs_json)
    except Exception:
        return "Invalid JSON input."

    if not docs:
        return "No valid policy snippets found."

    query_tokens = set(query.lower().split())
    ranked = sorted(
        docs,
        key=lambda d: len(query_tokens.intersection(set(d.get("content", "").lower().split()))),
        reverse=True,
    )
    return json.dumps(ranked[0])


def build_policy_prompt(user_query: str, policy_context: str) -> str:
    """Build the final policy-grounded prompt consumed by the response generator."""
    return (
        f"Context:\\n{policy_context}\\n\\n"
        f"Question: {user_query}\\n"
        "Answer concisely and strictly using the policy context."
    )
