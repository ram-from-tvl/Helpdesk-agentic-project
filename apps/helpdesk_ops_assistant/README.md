# Helpdesk Ops Assistant

A production-style policy support assistant built with LangGraph orchestration and Groq as the LLM provider.

## What This Application Does
- Routes support queries by intent.
- Retrieves policy snippets from a knowledge base.
- Ranks best context and generates final response.
- Applies a policy guard before final output.

## Runtime Stack
- LangGraph for workflow orchestration
- Groq via ChatGroq for response generation
- GoZen for PR quality gates (L1-L3) and production monitoring (L4)

## Local Execution

```bash
source venv/bin/activate
python apps/helpdesk_ops_assistant/scripts/generate_gozen_fixtures.py
python scripts/run_pr_quality_gate.py
python scripts/run_prod_monitor.py
python operations/dashboard/build_dashboard.py
```

Open the generated dashboard:
- artifacts/dashboard.html

Start local control center:

```bash
uvicorn operations.local_portal:app --reload --port 8080
```

Open:
- http://localhost:8080

## GoZen Integration
- Level 1: test_cases/helpdesk_ops_level1_components.json
- Level 2: test_cases/helpdesk_ops_level2_trajectories.json
- Level 3: test_cases/helpdesk_ops_level3_outcomes.json
- Level 4: test_cases/helpdesk_ops_level4_monitoring.json
