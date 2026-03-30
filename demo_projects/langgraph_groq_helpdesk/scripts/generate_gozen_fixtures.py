import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.graph import run_once  # noqa: E402


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)


def build_level2():
    scenarios = [
        {
            "trace_id": "LG_DEMO_1",
            "query": "What is the refund policy?",
            "expected_pattern": ["classify_intent", "retrieve_context", "draft_answer", "policy_check"],
        },
        {
            "trace_id": "LG_DEMO_2",
            "query": "urgent p1: remote-work exception for this week",
            "expected_pattern": ["classify_intent", "retrieve_context", "draft_answer", "policy_check"],
        },
        {
            "trace_id": "LG_DEMO_3",
            "query": "remote work exception",
            "expected_pattern": ["classify_intent", "retrieve_context", "draft_answer", "policy_check"],
        },
    ]

    rows = []
    for s in scenarios:
        result = run_once(s["query"])
        rows.append(
            {
                "trace_id": s["trace_id"],
                "expected_pattern": s["expected_pattern"],
                "actual_steps": result.get("steps", []),
                "agent_output": result.get("answer", ""),
            }
        )
    return rows


def build_level3(level2_rows):
    goldens = {
        "LG_DEMO_1": "Refunds are allowed within 14 days for eligible purchases.",
        "LG_DEMO_2": "Urgent tickets still require policy-compliant handling and validated guidance.",
        "LG_DEMO_3": "Remote work is allowed up to 3 days per week with manager approval.",
    }

    rows = []
    for i, row in enumerate(level2_rows, start=1):
        rows.append(
            {
                "case_id": f"LG_OUT_{i}",
                "query": "Support policy question",
                "agent_output": row["agent_output"],
                "golden_label": goldens[row["trace_id"]],
            }
        )
    return rows


def build_level4():
    return [
        {
            "request_id": "LG_REQ_1",
            "success": True,
            "latency_ms": 1100,
            "total_tokens": 420,
            "tool_errors": 0,
        },
        {
            "request_id": "LG_REQ_2",
            "success": True,
            "latency_ms": 6400,
            "total_tokens": 800,
            "tool_errors": 0,
        },
        {
            "request_id": "LG_REQ_3",
            "success": False,
            "latency_ms": 2100,
            "total_tokens": 650,
            "tool_errors": 2,
        },
    ]


def main():
    level2 = build_level2()
    level3 = build_level3(level2)
    level4 = build_level4()

    write_json(ROOT / "test_cases/demo_langgraph_level2_trajectories.json", level2)
    write_json(ROOT / "test_cases/demo_langgraph_level3_outcomes.json", level3)
    write_json(ROOT / "test_cases/demo_langgraph_level4_monitoring.json", level4)

    print("Generated:")
    print("- test_cases/demo_langgraph_level2_trajectories.json")
    print("- test_cases/demo_langgraph_level3_outcomes.json")
    print("- test_cases/demo_langgraph_level4_monitoring.json")


if __name__ == "__main__":
    main()
