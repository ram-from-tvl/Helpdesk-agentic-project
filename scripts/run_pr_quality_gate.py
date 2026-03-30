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

    thresholds = {"L1": 100, "L2": 100, "L3": 100}
    report = {
        "L1": {"score": results["L1"]["score"], "status": gate(results["L1"]["score"], thresholds["L1"]), "threshold": thresholds["L1"]},
        "L2": {"score": results["L2"]["score"], "status": gate(results["L2"]["score"], thresholds["L2"]), "threshold": thresholds["L2"]},
        "L3": {"score": results["L3"]["score"], "status": gate(results["L3"]["score"], thresholds["L3"]), "threshold": thresholds["L3"]},
    }

    with open(ARTIFACTS / "pr_quality_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print("Wrote artifacts/pr_quality_report.json")

    failed_levels = [level for level, data in report.items() if data["status"] == "FAIL"]
    if failed_levels:
        print(f"QUALITY GATE FAILED: {', '.join(failed_levels)} below threshold")
        sys.exit(1)

    print("QUALITY GATE PASSED")


if __name__ == "__main__":
    main()
