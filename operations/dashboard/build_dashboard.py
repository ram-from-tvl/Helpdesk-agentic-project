import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = REPO_ROOT / "artifacts"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def read_json(path: Path):
    if not path.exists():
        return None
    with open(path, "r") as f:
        return json.load(f)


def card(title: str, score: int, status: str) -> str:
    color = "#0f9d58" if status == "PASS" else "#d93025"
    return f"""
    <div class='card'>
      <h3>{title}</h3>
      <p class='score'>{score}%</p>
      <p class='status' style='color:{color}'>{status}</p>
    </div>
    """


def main():
    pr_data = read_json(ARTIFACT_DIR / "pr_quality_report.json") or {}
    prod_data = read_json(ARTIFACT_DIR / "prod_monitor_report.json") or {}

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    l1 = pr_data.get("L1", {"score": 0, "status": "N/A"})
    l2 = pr_data.get("L2", {"score": 0, "status": "N/A"})
    l3 = pr_data.get("L3", {"score": 0, "status": "N/A"})
    l4 = prod_data.get("L4", {"score": 0, "status": "N/A"})

    html = f"""
<!DOCTYPE html>
<html lang='en'>
<head>
  <meta charset='UTF-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1.0' />
  <title>GoZen Operations Dashboard</title>
  <style>
    :root {{
      --bg: #f6f8fb;
      --ink: #1f2937;
      --card: #ffffff;
      --line: #e5e7eb;
      --muted: #6b7280;
      --accent: #0b57d0;
    }}
    body {{
      margin: 0;
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      color: var(--ink);
      background: radial-gradient(circle at 20% 20%, #e9f1ff 0%, var(--bg) 45%, #eef6f1 100%);
    }}
    .wrap {{ max-width: 1100px; margin: 32px auto; padding: 0 16px; }}
    .hero {{ background: linear-gradient(120deg, #0b57d0, #2563eb); color: #fff; padding: 24px; border-radius: 14px; }}
    .hero h1 {{ margin: 0 0 6px; font-size: 28px; }}
    .hero p {{ margin: 0; opacity: 0.95; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-top: 18px; }}
    .card {{ background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 16px; box-shadow: 0 8px 22px rgba(0,0,0,0.04); }}
    .card h3 {{ margin: 0 0 8px; font-size: 16px; color: var(--muted); }}
    .score {{ margin: 0; font-size: 34px; font-weight: 700; }}
    .status {{ margin: 8px 0 0; font-weight: 700; }}
    .section {{ margin-top: 22px; }}
    .panel {{ background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 16px; }}
    code {{ background: #f3f4f6; padding: 2px 6px; border-radius: 6px; }}
  </style>
</head>
<body>
  <div class='wrap'>
    <section class='hero'>
      <h1>GoZen Operations Dashboard</h1>
      <p>Quality gates for pull requests (L1-L3) and production monitoring (L4)</p>
      <p>Generated at {generated_at}</p>
    </section>

    <section class='section'>
      <h2>Quality & Reliability Scores</h2>
      <div class='grid'>
        {card('Level 1 - Component Quality', int(l1.get('score', 0)), l1.get('status', 'N/A'))}
        {card('Level 2 - Trajectory Integrity', int(l2.get('score', 0)), l2.get('status', 'N/A'))}
        {card('Level 3 - Outcome Quality', int(l3.get('score', 0)), l3.get('status', 'N/A'))}
        {card('Level 4 - Production Health', int(l4.get('score', 0)), l4.get('status', 'N/A'))}
      </div>
    </section>

    <section class='section'>
      <h2>How To Use</h2>
      <div class='panel'>
        <p>1. Run PR checks (L1-L3) and save report to <code>artifacts/pr_quality_report.json</code>.</p>
        <p>2. Run production monitor (L4) and save report to <code>artifacts/prod_monitor_report.json</code>.</p>
        <p>3. Rebuild this dashboard file to visualize current state.</p>
      </div>
    </section>
  </div>
</body>
</html>
"""

    output = ARTIFACT_DIR / "dashboard.html"
    output.write_text(html)
    print(f"Dashboard written to {output}")


if __name__ == "__main__":
    main()
