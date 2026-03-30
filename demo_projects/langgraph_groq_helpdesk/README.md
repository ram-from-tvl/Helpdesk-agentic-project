# LangGraph + Groq Demo App (With Deliberate Defects)

This demo project is intentionally imperfect so GoZen can detect real issues during a walkthrough.

## Use Case
A helpdesk assistant that answers policy questions (refunds, remote work, urgent incident guidance).

## Deliberate Problems Included
1. Urgent trajectory defect: urgent requests skip retrieval and safety/policy check path.
2. Hallucination defect: some remote-work exception queries produce incorrect policy claims.
3. Monitoring defects: sample production logs include latency spikes and failed/tool-error runs.

## Run Locally

```bash
source venv/bin/activate
python demo_projects/langgraph_groq_helpdesk/scripts/generate_gozen_fixtures.py
python gozen_cli.py --init demo_projects/langgraph_groq_helpdesk/app/components.py
python gozen_cli.py --level 1 --test-file test_cases/demo_langgraph_level1_components.json --module demo_projects.langgraph_groq_helpdesk.app.components
python gozen_cli.py --level 2 --test-file test_cases/demo_langgraph_level2_trajectories.json
python gozen_cli.py --level 3 --test-file test_cases/demo_langgraph_level3_outcomes.json
python gozen_cli.py --level 4 --test-file test_cases/demo_langgraph_level4_monitoring.json
```

## Expected Demo Story
- L1 catches component-level regressions fast.
- L2 catches procedural/trajectory violations.
- L3 catches semantic quality problems in final outputs.
- L4 surfaces production health incidents.
