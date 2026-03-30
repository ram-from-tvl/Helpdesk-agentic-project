# GoZen 🔬

A 4-Layer QA & Operations harness for testing **any** agentic workflow — LangGraph, CrewAI, LangChain, custom scripts, or anything else.

**Evaluator engine:** Lyzr ADK + GitAgent Standard  
**Target app:** Any framework, any language — GoZen only needs your source code and trace logs.

---

## The 4 Evaluation Layers

| Level | Name | Method | When to Run |
|-------|------|--------|-------------|
| L1 | Component Evaluation | Deterministic unit tests | CI — every PR |
| L2 | Trajectory Evaluation | TrajectoryJudge (GitAgent) + plain English explainer | CI — every PR |
| L3 | Outcome Evaluation | OutcomeJudge (GitAgent) semantic scoring | CI — every PR |
| L4 | Production Monitoring | Deterministic incident detection | CD — cron every 10 min |

### L1 — Component Tests
Directly calls atomic Python functions and checks output. No LLM. Fast, cheap, deterministic.

### L2 — Trajectory Evaluation
`TrajectoryJudge` (Lyzr ADK GitAgent) reads execution traces and validates the agent followed the correct step sequence. When a trajectory fails, `ExplainerAgent` generates a plain English explanation + risk level so developers immediately understand what went wrong and why it matters.

### L3 — Outcome Evaluation
`OutcomeJudge` (Lyzr ADK GitAgent) semantically scores the agent's final answer against a golden label across Correctness, Completeness, and Safety (1–5 scale).

### L4 — Production Monitoring
Scans production request logs and flags: latency spikes (>5000ms), failed runs, and tool errors. No LLM required.

---

## Zero-Config Onboarding: `--init`

Point GoZen at any source file and it auto-discovers components and generates test cases:

```bash
python gozen_cli.py --init target_app/rag_components.py
```

What happens:
1. `DiscoveryAgent` (GitAgent) scans the file and identifies all agentic components — fetchers, processors, generators, tools — regardless of framework
2. `TestGenAgent` (GitAgent) generates 3 test cases per component automatically
3. Test cases are written to `test_cases/generated/level1_components.json`
4. Run them immediately with `--level 1 --test-file test_cases/generated/level1_components.json`

---

## Quick Start

```bash
# 1. Activate venv
source venv/bin/activate

# 2. Set your API key (never commit this)
cp .env.example .env
# Edit .env and add: LYZR_API_KEY=your-key-here

# 3. Generate fixtures for the reference app
python apps/helpdesk_ops_assistant/scripts/generate_gozen_fixtures.py

# 4. Run PR quality gate (L1-L3)
python scripts/run_pr_quality_gate.py

# 5. Run production monitoring (L4)
python scripts/run_prod_monitor.py

# 6. Build local dashboard
python operations/dashboard/build_dashboard.py
```

---

## GitAgent Standard

All evaluator agents follow the GitAgent Standard — each is defined by two files:

```
harness/evaluators/<agent_name>/
  agent.yaml   ← model config (name, provider, model)
  SOUL.md      ← system prompt / evaluation rules
```

This makes evaluators version-controllable, portable, and swappable without touching application code.

Current agents:
- `trajectory_judge` — validates step sequences
- `outcome_judge` — scores final answers semantically
- `explainer_agent` — translates failures into plain English + risk level
- `discovery_agent` — scans source code to find agentic components
- `test_gen_agent` — generates test cases from discovered components

---

## CI/CD Integration

Workflows are split by stage:

- PR quality gate (L1-L3): `.github/workflows/gozen-pr.yml`
- Production monitoring (L4): `.github/workflows/gozen-prod-monitor.yml`

Each workflow publishes artifacts under `artifacts/` including:
- `pr_quality_report.json`
- `prod_monitor_report.json`
- `dashboard.html`

Open `artifacts/dashboard.html` locally, or download it from GitHub Actions artifacts.

## Reference Application

GoZen is integrated with a production-style LangGraph application:

- App: `apps/helpdesk_ops_assistant/`
- Orchestration: LangGraph workflow in `apps/helpdesk_ops_assistant/app/graph.py`
- LLM provider: Groq via `langchain-groq`
- GoZen fixtures: `test_cases/helpdesk_ops_level*.json`

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your key. Never commit `.env`.

```bash
LYZR_API_KEY=your-lyzr-api-key-here
```
