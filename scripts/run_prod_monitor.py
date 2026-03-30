import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from gozen_cli import run_level4

ARTIFACTS = REPO_ROOT / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)


def gate(score: int, threshold: int) -> str:
    return "PASS" if score >= threshold else "FAIL"


def main():
    result = run_level4(str(REPO_ROOT / "test_cases/helpdesk_ops_level4_monitoring.json"))

    report = {
        "L4": {"score": result["score"], "status": gate(result["score"], 70)},
        "incidents": result["incidents"],
        "total": result["total"],
    }

    with open(ARTIFACTS / "prod_monitor_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print("Wrote artifacts/prod_monitor_report.json")


if __name__ == "__main__":
    main()
