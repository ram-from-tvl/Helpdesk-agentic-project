"""
GoZen — 4-Layer QA & Operations Harness for Agentic Workflows
Evaluator: Lyzr ADK (GitAgent Standard)
Target App: Any framework, any language
"""
import os
import json
import yaml
import sys
import ast
import argparse
import importlib
from datetime import datetime
from termcolor import colored
from dotenv import load_dotenv
from lyzr import Studio

load_dotenv()

# ─── GitAgent Loader ──────────────────────────────────────────────────────────

def load_evaluator_agent(agent_dir: str):
    """Load a GitAgent-standard evaluator from agent.yaml + SOUL.md."""
    with open(os.path.join(agent_dir, "agent.yaml"), "r") as f:
        config = yaml.safe_load(f)
    with open(os.path.join(agent_dir, "SOUL.md"), "r") as f:
        instructions = f.read()

    api_key = os.getenv("LYZR_API_KEY")
    if not api_key:
        print(colored("ERROR: LYZR_API_KEY not set. Add it to your .env file.", "red"))
        sys.exit(1)

    studio = Studio(api_key=api_key)
    agent = studio.create_agent(
        name=config.get("name", "EvaluatorAgent"),
        provider="openai/gpt-4o",
        role="Evaluator Judge",
        goal="Ensure QA rules are respected.",
        instructions=instructions
    )
    return agent

def parse_agent_json(raw: str) -> dict | list:
    """Safely parse JSON from agent response, stripping markdown fences."""
    cleaned = raw.strip()
    # Strip markdown code fences
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first line (```json or ```) and last line (```)
        inner = lines[1:] if lines[0].startswith("```") else lines
        if inner and inner[-1].strip() == "```":
            inner = inner[:-1]
        cleaned = "\n".join(inner).strip()
    # Try direct parse first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to extract the first complete JSON object or array
        import re
        # Find outermost JSON structure
        for start_char, end_char in [('{', '}'), ('[', ']')]:
            start = cleaned.find(start_char)
            if start == -1:
                continue
            # Walk to find matching close
            depth = 0
            in_str = False
            escape = False
            for i, ch in enumerate(cleaned[start:], start):
                if escape:
                    escape = False
                    continue
                if ch == '\\' and in_str:
                    escape = True
                    continue
                if ch == '"' and not escape:
                    in_str = not in_str
                if not in_str:
                    if ch == start_char:
                        depth += 1
                    elif ch == end_char:
                        depth -= 1
                        if depth == 0:
                            return json.loads(cleaned[start:i+1])
        raise ValueError(f"Could not extract valid JSON from response: {cleaned[:200]}")

# ─── Level 1: Component Evaluation ───────────────────────────────────────────

def infer_module_from_file(target_file: str) -> str | None:
    """Infer importable module path from a target file within this repository."""
    repo_root = os.path.abspath(os.path.dirname(__file__))
    abs_target = os.path.abspath(target_file)
    if not abs_target.startswith(repo_root):
        return None
    rel = os.path.relpath(abs_target, repo_root)
    if not rel.endswith(".py"):
        return None
    return rel[:-3].replace(os.sep, ".")


def run_level1(test_cases_file: str, module_override: str | None = None) -> dict:
    print(colored("\n━━━ Level 1: Component Evaluation (Deterministic) ━━━", "cyan", attrs=["bold"]))
    with open(test_cases_file, "r") as f:
        cases = json.load(f)

    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

    default_module = module_override
    if not default_module and cases:
        default_module = cases[0].get("module")
    if not default_module:
        default_module = "target_app.rag_components"

    print(f"  Using component module: {colored(default_module, 'yellow')}")
    module_cache = {}

    def get_module(module_name: str):
        if module_name not in module_cache:
            module_cache[module_name] = importlib.import_module(module_name)
        return module_cache[module_name]

    passed, failed = 0, 0
    for case in cases:
        try:
            case_module = case.get("module", default_module)
            components = get_module(case_module)
            func = getattr(components, case["component"])
            output = func(**case["input"])
            ok = case["expected_output"].lower() in output.lower()
            if ok:
                passed += 1
            else:
                failed += 1
            status = colored("PASS", "green") if ok else colored("FAIL", "red")
            print(f"  [{case['id']}] {case['component']}(): {status}")
        except Exception as e:
            failed += 1
            print(f"  [{case['id']}] ERROR: {colored(str(e), 'red')}")

    score = round((passed / len(cases)) * 100) if cases else 0
    print(f"\n  Result: {passed}/{len(cases)} passed  ({score}%)\n")
    return {"passed": passed, "total": len(cases), "score": score}

# ─── Level 2: Trajectory Evaluation ──────────────────────────────────────────

def run_level2(test_cases_file: str) -> dict:
    print(colored("━━━ Level 2: Trajectory Evaluation (TrajectoryJudge + ExplainerAgent) ━━━", "cyan", attrs=["bold"]))
    with open(test_cases_file, "r") as f:
        cases = json.load(f)

    trajectory_judge = load_evaluator_agent("harness/evaluators/trajectory_judge")
    explainer = load_evaluator_agent("harness/evaluators/explainer_agent")

    valid_count, total = 0, len(cases)
    for case in cases:
        prompt = f"Verify trace: {json.dumps(case)}"
        raw = trajectory_judge.run(prompt).response
        try:
            res = parse_agent_json(raw)
            valid = res.get("trajectory_valid", False)
            if valid:
                valid_count += 1
                print(f"  [{case['trace_id']}] Trajectory: {colored('VALID', 'green')}")
            else:
                # Plain English failure explanation via ExplainerAgent
                explain_payload = {
                    "expected_steps": case.get("expected_pattern", []),
                    "actual_steps": case.get("actual_steps", []),
                    "missing_steps": res.get("missing_steps", []),
                    "agent_output": case.get("agent_output", "")
                }
                exp_raw = explainer.run(json.dumps(explain_payload)).response
                try:
                    exp = parse_agent_json(exp_raw)
                    risk_color = {"Low": "green", "Medium": "yellow", "High": "red", "Critical": "magenta"}.get(exp.get("risk_level", "Medium"), "yellow")
                    print(f"  [{case['trace_id']}] Trajectory: {colored('INVALID', 'red')}")
                    print(f"    ↳ {exp.get('explanation', '')}")
                    print(f"    ↳ Risk: {colored(exp.get('risk_level', 'Unknown'), risk_color)}")
                except Exception:
                    print(f"  [{case['trace_id']}] Trajectory: {colored('INVALID', 'red')} | {res.get('reasoning', '')}")
        except Exception:
            print(f"  [{case['trace_id']}] {colored('EVAL ERROR', 'yellow')}")

    score = round((valid_count / total) * 100) if total else 0
    print(f"\n  Result: {valid_count}/{total} valid trajectories  ({score}%)\n")
    return {"valid": valid_count, "total": total, "score": score}

# ─── Level 3: Outcome Evaluation ─────────────────────────────────────────────

def run_level3(test_cases_file: str) -> dict:
    print(colored("━━━ Level 3: Outcome Evaluation (OutcomeJudge) ━━━", "cyan", attrs=["bold"]))
    with open(test_cases_file, "r") as f:
        cases = json.load(f)

    judge = load_evaluator_agent("harness/evaluators/outcome_judge")
    total_correctness, total = 0, len(cases)

    for case in cases:
        raw = judge.run(json.dumps(case)).response
        try:
            res = parse_agent_json(raw)
            score = res.get("correctness", 0)
            total_correctness += score
            color = "green" if score >= 4 else ("yellow" if score >= 2 else "red")
            print(f"  [{case['case_id']}] Correctness: {colored(str(score)+'/5', color)} | "
                  f"Completeness: {res.get('completeness')}/5 | "
                  f"Safety: {res.get('safety', 'N/A')}/5")
            print(f"    ↳ {res.get('reasoning', '')}")
        except Exception:
            print(f"  [{case['case_id']}] {colored('JUDGE PARSE ERROR', 'yellow')}")

    avg = round(total_correctness / total, 2) if total else 0
    score_pct = round((avg / 5) * 100)
    print(f"\n  Result: Avg Correctness {avg}/5.0  ({score_pct}%)\n")
    return {"avg_correctness": avg, "total": total, "score": score_pct}

# ─── Level 4: Production Monitoring ──────────────────────────────────────────

def run_level4(test_cases_file: str) -> dict:
    print(colored("━━━ Level 4: Production Monitoring (Deterministic) ━━━", "cyan", attrs=["bold"]))
    with open(test_cases_file, "r") as f:
        cases = json.load(f)

    incidents, total = 0, len(cases)
    for case in cases:
        alerts = []
        if case["latency_ms"] > 5000:
            alerts.append(colored("HIGH LATENCY", "red"))
        if not case["success"]:
            alerts.append(colored("FAILED RUN", "red"))
        if case["tool_errors"] > 0:
            alerts.append(colored("TOOL ERROR", "yellow"))

        if alerts:
            incidents += 1
        status = " | ".join(alerts) if alerts else colored("HEALTHY", "green")
        print(f"  [{case['request_id']}] {case['latency_ms']}ms | {case['total_tokens']} tokens → {status}")

    health_pct = round(((total - incidents) / total) * 100) if total else 0
    print(f"\n  Result: {incidents} incidents / {total} requests  ({health_pct}% healthy)\n")
    return {"incidents": incidents, "total": total, "score": health_pct}

# ─── agentscope init: Discovery + Test Generation ────────────────────────────

def run_init(target_file: str):
    """
    Zero-config onboarding:
    1. DiscoveryAgent scans the target source file
    2. TestGenAgent generates Level 1 test cases automatically
    3. Writes to test_cases/generated/level1_components.json
    """
    print(colored("\n━━━ GoZen Init: Discovery + Test Generation ━━━", "magenta", attrs=["bold"]))

    if not os.path.exists(target_file):
        print(colored(f"ERROR: File not found: {target_file}", "red"))
        sys.exit(1)

    with open(target_file, "r") as f:
        source_code = f.read()

    print(f"  Scanning: {colored(target_file, 'cyan')}")

    # Step 1: DiscoveryAgent
    print("  [1/2] Running DiscoveryAgent...")
    discovery_agent = load_evaluator_agent("harness/evaluators/discovery_agent")
    raw = discovery_agent.run(f"Scan this source code and identify all agentic components:\n\n{source_code}").response
    try:
        discovery = parse_agent_json(raw)
    except Exception as e:
        print(colored(f"  Discovery parse error: {e}\n  Raw: {raw[:300]}", "red"))
        sys.exit(1)

    components = discovery.get("components", [])
    framework = discovery.get("framework_detected", "unknown")
    print(f"  Found {colored(str(len(components)), 'green')} components | Framework: {colored(framework, 'yellow')}")
    for c in components:
        print(f"    • {colored(c['name'], 'cyan')} ({c['type']}) — {c['description']}")

    # Step 2: TestGenAgent — generate per component and merge
    print("\n  [2/2] Running TestGenAgent — generating test cases...")
    test_gen_agent = load_evaluator_agent("harness/evaluators/test_gen_agent")
    all_test_cases = []

    # Extract actual function signatures from source for grounding
    import ast as _ast
    sig_map = {}
    try:
        tree = _ast.parse(source_code)
        for node in _ast.walk(tree):
            if isinstance(node, _ast.FunctionDef):
                params = {}
                for arg in node.args.args:
                    ann = ""
                    if arg.annotation:
                        ann = _ast.unparse(arg.annotation)
                    params[arg.arg] = ann or "str"
                # Get defaults
                defaults = node.args.defaults
                default_offset = len(node.args.args) - len(defaults)
                for i, default in enumerate(defaults):
                    param_name = node.args.args[default_offset + i].arg
                    params[param_name] = f"{params.get(param_name, 'str')} (default={_ast.unparse(default)})"
                sig_map[node.name] = params
    except Exception:
        pass

    for idx, comp in enumerate(components):
        sig_info = sig_map.get(comp["name"], {})
        payload = {**comp, "actual_signature": sig_info}
        raw2 = test_gen_agent.run(
            f"Generate 2 test cases for this component:\n{json.dumps(payload)}"
        ).response
        try:
            cases = parse_agent_json(raw2)
            if isinstance(cases, dict):
                cases = [cases]
            for case in cases:
                case["id"] = f"L1_GEN_{len(all_test_cases) + 1}"
            all_test_cases.extend(cases)
        except Exception as e:
            print(colored(f"  Warning: could not parse tests for {comp['name']}: {e}", "yellow"))

    test_cases = all_test_cases

    inferred_module = infer_module_from_file(target_file)
    if inferred_module:
        for case in test_cases:
            case["module"] = inferred_module

    os.makedirs("test_cases/generated", exist_ok=True)
    out_path = "test_cases/generated/level1_components.json"
    with open(out_path, "w") as f:
        json.dump(test_cases, f, indent=2)

    print(f"\n  {colored('✓', 'green')} Generated {len(test_cases)} test cases → {colored(out_path, 'cyan')}")
    print(colored("\n  Run them now: python gozen_cli.py --level 1 --test-file test_cases/generated/level1_components.json\n", "magenta"))

# ─── Report Card ─────────────────────────────────────────────────────────────

def print_report_card(results: dict):
    """Print a structured PASS/FAIL report card after all levels run."""
    print(colored("\n" + "═" * 60, "white"))
    print(colored("  GoZen — QA Report Card", "white", attrs=["bold"]))
    print(colored("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "white"))
    print(colored("═" * 60, "white"))

    overall_pass = True
    thresholds = {"L1": 80, "L2": 80, "L3": 60, "L4": 70}

    for level, label in [("L1", "Component Tests"), ("L2", "Trajectory"), ("L3", "Outcome Quality"), ("L4", "Prod Health")]:
        if level not in results:
            continue
        score = results[level]["score"]
        threshold = thresholds[level]
        passed = score >= threshold
        if not passed:
            overall_pass = False
        badge = colored("PASS", "green", attrs=["bold"]) if passed else colored("FAIL", "red", attrs=["bold"])
        bar_filled = int(score / 5)
        bar = colored("█" * bar_filled, "green" if passed else "red") + colored("░" * (20 - bar_filled), "white")
        print(f"  {level} {label:<22} [{bar}] {score:>3}%  {badge}")

    print(colored("─" * 60, "white"))
    gate = colored("✅  GATE: PASS — Safe to merge", "green", attrs=["bold"]) if overall_pass else colored("❌  GATE: FAIL — Do not merge", "red", attrs=["bold"])
    print(f"  {gate}")
    print(colored("═" * 60 + "\n", "white"))

# ─── Entry Point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="GoZen — 4-Layer QA Harness for Agentic Workflows",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--level", type=int, choices=[1, 2, 3, 4], help="Run a specific evaluation level")
    parser.add_argument("--all", action="store_true", help="Run all 4 levels and print report card")
    parser.add_argument("--init", metavar="FILE", help="Run Discovery + TestGen on a source file (zero-config onboarding)")
    parser.add_argument("--test-file", metavar="FILE", help="Override default test cases file for --level")
    parser.add_argument("--module", metavar="MODULE", help="Python module path for Level 1 components (e.g., target_app.rag_components)")
    args = parser.parse_args()

    if args.init:
        run_init(args.init)
        sys.exit(0)

    results = {}

    default_files = {
        1: "test_cases/level1_components.json",
        2: "test_cases/level2_trajectories.json",
        3: "test_cases/level3_outcomes.json",
        4: "test_cases/level4_monitoring.json",
    }

    def get_file(level):
        return args.test_file if args.test_file else default_files[level]

    if args.all or args.level == 1:
        results["L1"] = run_level1(get_file(1), module_override=args.module)
    if args.all or args.level == 2:
        results["L2"] = run_level2(get_file(2))
    if args.all or args.level == 3:
        results["L3"] = run_level3(get_file(3))
    if args.all or args.level == 4:
        results["L4"] = run_level4(get_file(4))

    if args.all and results:
        print_report_card(results)
