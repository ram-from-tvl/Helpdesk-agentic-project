import json
import os
from typing import List, TypedDict

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph

from app.components import build_policy_prompt, fetch_policy_context, select_best_policy

load_dotenv()


class WorkflowState(TypedDict):
    query: str
    intent: str
    context: str
    ranked_context: str
    answer: str
    steps: List[str]
    policy_checked: bool


def classify_intent(state: WorkflowState) -> dict:
    query = state["query"].lower()
    if "urgent" in query or "p1" in query:
        intent = "incident"
    elif "refund" in query or "billing" in query:
        intent = "billing"
    elif "remote" in query or "work from home" in query:
        intent = "hr"
    else:
        intent = "general"
    return {"intent": intent, "steps": state["steps"] + ["classify_intent"]}


def retrieve_context(state: WorkflowState) -> dict:
    docs_json = fetch_policy_context(state["query"], top_k=3)
    return {"context": docs_json, "steps": state["steps"] + ["retrieve_context"]}


def rank_context(state: WorkflowState) -> dict:
    ranked = select_best_policy(state["context"], state["query"])
    return {"ranked_context": ranked, "steps": state["steps"] + ["rank_context"]}


def generate_response(state: WorkflowState) -> dict:
    ranked_context = state.get("ranked_context", "")
    try:
        best = json.loads(ranked_context)
        policy_text = best.get("content", "No policy context available.")
    except Exception:
        policy_text = "No policy context available."

    prompt = build_policy_prompt(state["query"], policy_text)
    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        llm = ChatGroq(
            api_key=api_key,
            model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            temperature=0,
        )
        answer = llm.invoke(prompt).content
    else:
        answer = policy_text

    return {"answer": answer, "steps": state["steps"] + ["generate_response"]}


def policy_guard(state: WorkflowState) -> dict:
    text = state["answer"].lower()
    blocked_patterns = [
        "share credential",
        "share api key",
        "bypass policy",
    ]
    if any(pattern in text for pattern in blocked_patterns):
        return {
            "answer": "Policy guard blocked an unsafe response. Please retry with validated context.",
            "policy_checked": False,
            "steps": state["steps"] + ["policy_guard"],
        }

    return {
        "policy_checked": True,
        "steps": state["steps"] + ["policy_guard"],
    }


def build_workflow():
    workflow = StateGraph(WorkflowState)
    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("retrieve_context", retrieve_context)
    workflow.add_node("rank_context", rank_context)
    workflow.add_node("generate_response", generate_response)
    workflow.add_node("policy_guard", policy_guard)

    workflow.add_edge(START, "classify_intent")
    workflow.add_edge("classify_intent", "retrieve_context")
    workflow.add_edge("retrieve_context", "rank_context")
    workflow.add_edge("rank_context", "generate_response")
    workflow.add_edge("generate_response", "policy_guard")
    workflow.add_edge("policy_guard", END)

    return workflow.compile()


def run_once(query: str) -> dict:
    app = build_workflow()
    return app.invoke(
        {
            "query": query,
            "intent": "",
            "context": "",
            "ranked_context": "",
            "answer": "",
            "steps": [],
            "policy_checked": False,
        }
    )


if __name__ == "__main__":
    test_query = os.getenv("SAMPLE_QUERY", "What is the remote work policy?")
    print(json.dumps(run_once(test_query), indent=2))
