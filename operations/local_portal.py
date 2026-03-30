from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = REPO_ROOT / "artifacts"
PORTAL_HTML = REPO_ROOT / "operations" / "portal" / "index.html"

DATASET_MAP = {
    "l1": REPO_ROOT / "test_cases" / "helpdesk_ops_level1_components.json",
    "l2": REPO_ROOT / "test_cases" / "helpdesk_ops_level2_trajectories.json",
    "l3": REPO_ROOT / "test_cases" / "helpdesk_ops_level3_outcomes.json",
    "l4": REPO_ROOT / "test_cases" / "helpdesk_ops_level4_monitoring.json",
}

RUN_COMMANDS = {
    "fixtures": ["python", "apps/helpdesk_ops_assistant/scripts/generate_gozen_fixtures.py"],
    "pr": ["python", "scripts/run_pr_quality_gate.py"],
    "prod": ["python", "scripts/run_prod_monitor.py"],
    "dashboard": ["python", "operations/dashboard/build_dashboard.py"],
    "all": [
        "bash",
        "-lc",
        "python apps/helpdesk_ops_assistant/scripts/generate_gozen_fixtures.py && "
        "python scripts/run_pr_quality_gate.py && "
        "python scripts/run_prod_monitor.py && "
        "python operations/dashboard/build_dashboard.py",
    ],
}


class DatasetPayload(BaseModel):
    data: list[dict[str, Any]]


app = FastAPI(title="GoZen Local Portal")
app.mount("/artifacts", StaticFiles(directory=ARTIFACTS_DIR), name="artifacts")


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    with open(path, "r") as f:
        return json.load(f)


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    if not PORTAL_HTML.exists():
        raise HTTPException(status_code=404, detail="Portal UI file is missing")
    return HTMLResponse(PORTAL_HTML.read_text())


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse({"ok": True, "service": "gozen-local-portal"})


@app.get("/api/summary")
def summary() -> JSONResponse:
    payload = {
        "pr": _read_json(ARTIFACTS_DIR / "pr_quality_report.json") or {},
        "prod": _read_json(ARTIFACTS_DIR / "prod_monitor_report.json") or {},
        "dashboard_exists": (ARTIFACTS_DIR / "dashboard.html").exists(),
    }
    return JSONResponse(payload)


@app.get("/api/datasets")
def list_datasets() -> JSONResponse:
    rows = {}
    for key, path in DATASET_MAP.items():
        rows[key] = {
            "path": str(path.relative_to(REPO_ROOT)),
            "records": len(_read_json(path) or []),
        }
    return JSONResponse(rows)


@app.get("/api/datasets/{dataset_key}")
def get_dataset(dataset_key: str) -> JSONResponse:
    path = DATASET_MAP.get(dataset_key)
    if not path:
        raise HTTPException(status_code=404, detail="Unknown dataset key")
    data = _read_json(path)
    if data is None:
        raise HTTPException(status_code=404, detail="Dataset file not found")
    return JSONResponse({"dataset": dataset_key, "path": str(path.relative_to(REPO_ROOT)), "data": data})


@app.post("/api/datasets/{dataset_key}")
def save_dataset(dataset_key: str, payload: DatasetPayload) -> JSONResponse:
    path = DATASET_MAP.get(dataset_key)
    if not path:
        raise HTTPException(status_code=404, detail="Unknown dataset key")

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(payload.data, f, indent=2)

    return JSONResponse({"ok": True, "saved_to": str(path.relative_to(REPO_ROOT)), "records": len(payload.data)})


@app.post("/api/run/{run_key}")
def run_pipeline(run_key: str) -> JSONResponse:
    cmd = RUN_COMMANDS.get(run_key)
    if not cmd:
        raise HTTPException(status_code=404, detail="Unknown run target")

    try:
        proc = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Execution failed: {exc}")

    return JSONResponse(
        {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-12000:],
            "stderr": proc.stderr[-12000:],
        }
    )
