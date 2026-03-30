import os
import json
from typing import TypedDict, List

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import START, END, StateGraph

from app.components import fetch_knowledge, build_support_response

load_dotenv()


class HelpdeskState(TypedDict):
    query: str
    intent: str
    context: str
    answer: str
    steps: List[str]
    policy_checked: bool


def classify_intent(state: HelpdeskState) -> dict:
    query = state["query"].lower()
    intent = "general"
    if "urgent" in query or "p1" in query:
        intent = "urgent"
    elif "refund" in query:
        intent = "billing"
    elif "remote" in query or "work from home" in query:
        intent = "hr"

    return {"intent": intent, "steps": state["steps"] + ["classify_intent"]}


def retrieve_context(state: HelpdeskState) -> dict:
    docs_json = fetch_knowledge(state["query"], top_k=2)
    docs = json.loads(docs_json)
    context = docs[0]["content"] if docs else "No relevant policy found."
    return {"context": context, "steps": state["steps"] + ["retrieve_context"]}


def draft_answer(state: HelpdeskState) -> dict:
    # Deliberate problem #1: urgent route may draft an answer with no grounded context.
    # Deliberate problem #2: an HR fallback can hallucinate an incorrect policy claim.
    query = state["query"].lower()
    context = state.get("context", "")

    if state.get("intent") == "urgent" and not context:
        answer = "I escalated this. You can bypass policy while urgent issues are open."
    elif "remote" in query and "exception" in query:
        answer = "Employees can work remotely 5 days a week without manager approval."
    else:
        template = build_support_response(state["query"], context or "No policy context")
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            llm = ChatGroq(
                api_key=api_key,
                model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
                temperature=0,
            )
            prompt = (
                "You are a policy assistant. Respond using only the given context.\n\n"
                f"{template}"
            )
            answer = llm.invoke(prompt).content
        else:
            answer = f"Based on policy, here is guidance.\\n{template}"

    return {"answer": answer, "steps": state["steps"] + ["draft_answer"]}


def policy_check(state: HelpdeskState) -> dict:
    answer = state["answer"].lower()
    forbidden = [
        "bypass policy",
        "5 days a week without manager approval",
    ]
    flagged = any(item in answer for item in forbidden)

    if flagged:
        patched = (
            "Policy check failed: response contained unsafe or incorrect policy guidance. "
            "Please re-run with validated context."
        )
        return {
            "answer": patched,
            "policy_checked": False,
            "steps": state["steps"] + ["policy_check"],
        }

    return {
        "policy_checked": True,
        "steps": state["steps"] + ["policy_check"],
    }


def route_after_intent(state: HelpdeskState) -> str:
    # Deliberate trajectory defect: urgent requests skip retrieve_context + policy_check.
    if state.get("intent") == "urgent":
        return "draft_answer"
    return "retrieve_context"


def build_graph():
    graph = StateGraph(HelpdeskState)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("draft_answer", draft_answer)
    graph.add_node("policy_check", policy_check)

    graph.add_edge(START, "classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        route_after_intent,
        {
            "retrieve_context": "retrieve_context",
            "draft_answer": "draft_answer",
        },
    )
    graph.add_edge("retrieve_context", "draft_answer")
    graph.add_edge("draft_answer", "policy_check")
    graph.add_edge("policy_check", END)

    return graph.compile()


def run_once(query: str) -> dict:
    app = build_graph()
    return app.invoke(
        {
            "query": query,
            "intent": "",
            "context": "",
            "answer": "",
            "steps": [],
            "policy_checked": False,
        }
    )


if __name__ == "__main__":
    sample_query = os.getenv("SAMPLE_QUERY", "urgent: customer asks remote-work exception")
    result = run_once(sample_query)
    print(json.dumps(result, indent=2))
