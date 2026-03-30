import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.graph import run_once  # noqa: E402


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)


def build_level1():
    return [
        {
            "id": "OPS_L1_1",
            "module": "apps.helpdesk_ops_assistant.app.components",
            "component": "fetch_policy_context",
            "input": {"query": "remote work policy", "top_k": 1},
            "expected_output": "remote work",
        },
        {
            "id": "OPS_L1_2",
            "module": "apps.helpdesk_ops_assistant.app.components",
            "component": "fetch_policy_context",
            "input": {"query": "refund policy", "top_k": 1},
            "expected_output": "refunds are allowed",
        },
        {
            "id": "OPS_L1_3",
            "module": "apps.helpdesk_ops_assistant.app.components",
            "component": "select_best_policy",
            "input": {
                "candidate_docs_json": "[{\"id\":\"r1\",\"content\":\"Refunds are allowed within 14 days for eligible purchases.\"}]",
                "query": "refunds within 14 days",
            },
            "expected_output": "refunds are allowed",
        },
        {
            "id": "OPS_L1_4",
            "module": "apps.helpdesk_ops_assistant.app.components",
            "component": "build_policy_prompt",
            "input": {
                "user_query": "Can I work remotely?",
                "policy_context": "Remote work is allowed up to 3 days per week with manager approval.",
            },
            "expected_output": "Question: Can I work remotely?",
        },
        {
            "id": "OPS_L1_5",
            "module": "apps.helpdesk_ops_assistant.app.components",
            "component": "select_best_policy",
            "input": {"candidate_docs_json": "not-json", "query": "refund"},
            "expected_output": "Invalid JSON",
        },
    ]


def build_level2():
    scenarios = [
        {
            "trace_id": "OPS_L2_1",
            "query": "What is the refund policy?",
            "expected_pattern": [
                "classify_intent",
                "retrieve_context",
                "rank_context",
                "generate_response",
                "policy_guard",
            ],
        },
        {
            "trace_id": "OPS_L2_2",
            "query": "urgent p1 issue: what should we do first?",
            "expected_pattern": [
                "classify_intent",
                "retrieve_context",
                "rank_context",
                "generate_response",
                "policy_guard",
            ],
        },
    ]

    rows = []
    for scenario in scenarios:
        result = run_once(scenario["query"])
        rows.append(
            {
                "trace_id": scenario["trace_id"],
                "expected_pattern": scenario["expected_pattern"],
                "actual_steps": result.get("steps", []),
                "agent_output": result.get("answer", ""),
            }
        )
    return rows


def build_level3(level2_rows):
    goldens = {
        "OPS_L2_1": "Refunds are allowed within 14 days for eligible purchases.",
        "OPS_L2_2": "P1 incidents must be acknowledged within 15 minutes.",
    }

    rows = []
    for i, row in enumerate(level2_rows, start=1):
        rows.append(
            {
                "case_id": f"OPS_L3_{i}",
                "query": "Policy support question",
                "agent_output": row["agent_output"],
                "golden_label": goldens[row["trace_id"]],
            }
        )
    return rows


def build_level4():
    return [
        {
            "request_id": "OPS_REQ_1",
            "success": True,
            "latency_ms": 900,
            "total_tokens": 390,
            "tool_errors": 0,
        },
        {
            "request_id": "OPS_REQ_2",
            "success": True,
            "latency_ms": 6200,
            "total_tokens": 880,
            "tool_errors": 0,
        },
        {
            "request_id": "OPS_REQ_3",
            "success": False,
            "latency_ms": 1800,
            "total_tokens": 610,
            "tool_errors": 1,
        },
    ]


def main():
    level1 = build_level1()
    level2 = build_level2()
    level3 = build_level3(level2)
    level4 = build_level4()

    write_json(REPO_ROOT / "test_cases/helpdesk_ops_level1_components.json", level1)
    write_json(REPO_ROOT / "test_cases/helpdesk_ops_level2_trajectories.json", level2)
    write_json(REPO_ROOT / "test_cases/helpdesk_ops_level3_outcomes.json", level3)
    write_json(REPO_ROOT / "test_cases/helpdesk_ops_level4_monitoring.json", level4)

    print("Generated GoZen fixtures for Helpdesk Ops Assistant:")
    print("- test_cases/helpdesk_ops_level1_components.json")
    print("- test_cases/helpdesk_ops_level2_trajectories.json")
    print("- test_cases/helpdesk_ops_level3_outcomes.json")
    print("- test_cases/helpdesk_ops_level4_monitoring.json")


if __name__ == "__main__":
    main()
