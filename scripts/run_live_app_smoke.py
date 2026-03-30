import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "apps" / "helpdesk_ops_assistant"
sys.path.insert(0, str(APP_ROOT))

from app.graph import run_once


def main():
    result = run_once("Can I work from home on Fridays?")
    steps = result.get("steps", [])
    answer = (result.get("answer") or "").strip()

    if not steps or "generate_response" not in steps:
        raise RuntimeError("Live app smoke failed: missing workflow execution steps.")
    if not answer:
        raise RuntimeError("Live app smoke failed: empty answer.")

    print(json.dumps({"ok": True, "steps": steps, "answer_preview": answer[:180]}, indent=2))


if __name__ == "__main__":
    main()
