import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from gozen_cli import run_level1, run_level2, run_level3

ARTIFACTS = REPO_ROOT / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)


def gate(score: int, threshold: int) -> str:
    return "PASS" if score >= threshold else "FAIL"


def main():
    results = {}
    results["L1"] = run_level1(
        str(REPO_ROOT / "test_cases/helpdesk_ops_level1_components.json"),
        module_override="apps.helpdesk_ops_assistant.app.components",
    )
    results["L2"] = run_level2(str(REPO_ROOT / "test_cases/helpdesk_ops_level2_trajectories.json"))
    results["L3"] = run_level3(str(REPO_ROOT / "test_cases/helpdesk_ops_level3_outcomes.json"))

    report = {
        "L1": {"score": results["L1"]["score"], "status": gate(results["L1"]["score"], 80)},
        "L2": {"score": results["L2"]["score"], "status": gate(results["L2"]["score"], 80)},
        "L3": {"score": results["L3"]["score"], "status": gate(results["L3"]["score"], 60)},
    }

    with open(ARTIFACTS / "pr_quality_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print("Wrote artifacts/pr_quality_report.json")


if __name__ == "__main__":
    main()
