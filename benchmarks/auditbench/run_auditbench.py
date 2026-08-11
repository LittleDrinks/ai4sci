#!/usr/bin/env python3
"""Run AuditBench through Anti-Autoresearch's existing audit spine."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib import request


MODEL = "gpt-5.4-mini"
REMOTE_ROOT = "/data/zsm/ai4sci-design-bench-20260809/audit"
GENERATED_AT = "2026-08-09T00:00:00Z"


_SCENARIO_DATA = [
        {
            "id": "case-01-clean",
            "kind": "clean",
            "latex": r"""\documentclass{article}
\begin{document}
\section{Results}
We evaluate on a held-out set of 500 items. Our method reaches 84.8\% accuracy.
\begin{table}[t]
\caption{Held-out accuracy}
\begin{tabular}{lr}
Method & Accuracy \\
Proposed & 84.8\% \\
Baseline & 80.0\% \\
\end{tabular}
\end{table}
\end{document}
""",
            "expected_deterministic": [],
            "expected_model": [],
            "support": True,
            "support_basis": "ledger-only",
        },
        {
            "id": "case-02-delta-error",
            "kind": "numeric arithmetic",
            "latex": r"""\documentclass{article}
\begin{document}
\begin{abstract}
Our method reaches 78.0\% accuracy, a 16.0\% relative improvement from 73.1\% to 78.0\%.
\end{abstract}
\section{Results}
\begin{table}[t]
\begin{tabular}{lr}
Method & Accuracy \\
Proposed & 78.0\% \\
Baseline & 73.1\% \\
\end{tabular}
\end{table}
\end{document}
""",
            "expected_deterministic": ["HP-DELTA-ERROR"],
            "expected_model": [],
            "support": True,
            "support_basis": "ledger-only",
        },
        {
            "id": "case-03-headline-table-drift",
            "kind": "numeric table mismatch",
            "latex": r"""\documentclass{article}
\begin{document}
\begin{abstract}
Our method achieves 85.3\% accuracy on the benchmark.
\end{abstract}
\section{Results}
\begin{table}[t]
\begin{tabular}{lr}
Method & Accuracy \\
Proposed & 84.7\% \\
Baseline & 80.0\% \\
\end{tabular}
\end{table}
\end{document}
""",
            "expected_deterministic": ["HP-NUM-INFLATE"],
            "expected_model": [],
            "support": True,
            "support_basis": "ledger-only",
        },
        {
            "id": "case-04-paraphrase-duplicate",
            "kind": "paraphrase duplicate",
            "latex": r"""\documentclass{article}
\begin{document}
\section{Background}
The public MeanVote baseline averages three fixed predictors before applying a threshold.
\section{Method}
We introduce TriFuse as a new mechanism that computes the mean of the same three fixed
predictors and then applies the same threshold.
\section{Results}
The proposed method reaches 80.0\% accuracy.
\end{document}
""",
            "expected_deterministic": [],
            "expected_model": ["ADV-DUPLICATE-PUBLICATION"],
            "support": False,
            "support_basis": "external prior-work corpus",
        },
        {
            "id": "case-05-evidence-mismatch",
            "kind": "evidence mismatch",
            "latex": r"""\documentclass{article}
\begin{document}
\section{Introduction}
Smith et al. prove that self-refinement always removes correlated errors \cite{smith2020}.
\section{Evidence}
The cited Smith et al. 2020 study reports that self-refinement can preserve correlated errors.
\end{document}
""",
            "expected_deterministic": [],
            "expected_model": ["HP-CITE-CONTEXT"],
            "support": False,
            "support_basis": "external cited-paper record",
        },
        {
            "id": "case-06-missing-source",
            "kind": "missing source",
            "latex": r"""\documentclass{article}
\begin{document}
\section{Experiments}
We report results from 20 agents and five random seeds, but code, prompts, checkpoints,
and exact configurations are not released anywhere.
Our method reaches 82.0\% accuracy.
\end{document}
""",
            "expected_deterministic": [],
            "expected_model": ["HP-MISSING-REPRO-ARTIFACT"],
            "support": False,
            "support_basis": "released repository artifact set",
        },
        {
            "id": "case-07-observation-conflict",
            "kind": "observation conflict",
            "latex": r"""\documentclass{article}
\begin{document}
\section{Results}
The main results report 78.0\% accuracy for Dataset A.
\appendix
\section{Additional Results}
For the same Dataset A cell and configuration, the appendix reports 64.0\% accuracy.
\end{document}
""",
            "expected_deterministic": [],
            "expected_model": ["HP-APPENDIX-CONTRA"],
            "support": True,
            "support_basis": "ledger-only",
        },
        {
            "id": "case-08-reproduction-drift",
            "kind": "reproduction drift",
            "latex": r"""\documentclass{article}
\begin{document}
\section{Results}
The paper reports 86.1\% accuracy for configuration A.
The released result artifact results/config-a.txt reports 81.4\% accuracy for the same configuration.
\end{document}
""",
            "results": "configuration A accuracy: 81.4%\n",
            "expected_deterministic": [],
            "expected_model": ["HP-RESULT-ARTIFACT-MISMATCH"],
            "support": True,
            "support_basis": "included result artifact text",
        },
        {
            "id": "case-09-severe-fact-error",
            "kind": "severe fact error",
            "latex": r"""\documentclass{article}
\begin{document}
\section{Data}
We use ImageNet-1k, which contains 100 classes and exactly 1,000 training images.
\section{Results}
The method reaches 81.0\% top-1 accuracy.
\end{document}
""",
            "expected_deterministic": [],
            "expected_model": ["HP-RESOURCE-IDENTITY-MISMATCH"],
            "support": False,
            "support_basis": "public resource registry",
        },
        {
            "id": "case-10-pseudo-innovation",
            "kind": "pseudo innovation",
            "latex": r"""\documentclass{article}
\begin{document}
\section{Method}
We introduce a novel method by combining standard TF-IDF, a standard two-layer MLP,
and majority voting without changing any component or their interaction.
\section{Results}
The combined pipeline reaches 79.0\% accuracy.
\end{document}
""",
            "expected_deterministic": [],
            "expected_model": ["ADV-TRIVIAL-COMBINATION"],
            "support": False,
            "support_basis": "external prior-work corpus",
        },
]


def scenario_data():
    return json.loads(json.dumps(_SCENARIO_DATA))


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--anti-root", default="/home/q2635/wsl-workspace/music/Anti-Autoresearch")
    parser.add_argument("--remote-root", default=REMOTE_ROOT)
    parser.add_argument("--run-id", default="")
    return parser.parse_args()


def read_env(path):
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def run_command(args, cwd, log_path):
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    log_path.write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"command failed: {' '.join(args)}")
    return result.stdout


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def anti_catalog(anti_root):
    schema = json.loads((anti_root / "schemas/finding.schema.json").read_text())
    skills = set(schema["properties"]["skill"]["enum"])
    taxonomy = (anti_root / "references/hack-pattern-taxonomy.md").read_text()
    patterns = set(re.findall(r"\b(?:HP|ADV|AIS)-[A-Z0-9-]+\b", taxonomy))
    hints = {}
    for line in taxonomy.splitlines():
        match = re.match(r"###\s+(`?((?:HP|ADV|AIS)-[A-Z0-9-]+)`?)\s+[-—]\s*(.*)", line)
        if match:
            hints[match.group(2)] = match.group(3)[:240]
    return skills, patterns, hints


def validate_expected(cases, patterns):
    expected = {p for c in cases for p in c["expected_deterministic"] + c["expected_model"]}
    unknown = sorted(expected - patterns)
    if unknown:
        raise SystemExit(f"benchmark expected patterns absent from Anti taxonomy: {unknown}")


def build_case(case, root, anti_root):
    case_dir = root / case["id"]
    case_dir.mkdir()
    (case_dir / "main.tex").write_text(prepare_latex(case["latex"]), encoding="utf-8")
    if case.get("results"):
        (case_dir / "results.txt").write_text(case["results"], encoding="utf-8")
    ledger = case_dir / "claims.json"
    args = [sys.executable, str(anti_root / "tools/build_claim_ledger.py"),
            "--paper-id", case["id"], "--latex", "main.tex",
            "--observability-level", "2", "--generated-at", GENERATED_AT,
            "--out", "claims.json"]
    if case.get("results"):
        args += ["--pdf-text", "results.txt"]
    run_command(args, case_dir, case_dir / "ledger.log")
    return case_dir, ledger


def prepare_latex(text):
    structural = ("\\begin{abstract}", "\\end{abstract}", "\\section",
                  "\\appendix", "\\begin{table", "\\end{table}")
    lines = []
    for line in text.splitlines():
        if line.strip().startswith(structural) and lines and lines[-1] != "":
            lines.append("")
        lines.append(line)
    return "\n".join(lines) + "\n"


def run_deterministic(case_dir, anti_root):
    outputs = []
    tools = [
        ("numeric", "check_numeric_consistency.py"),
        ("stat", "check_stat_consistency.py"),
        ("presentation", "check_presentation.py"),
    ]
    for label, tool in tools:
        out = f"{label}.findings.json"
        args = [sys.executable, str(anti_root / "tools" / tool),
                "--ledger", "claims.json", "--out", out]
        run_command(args, case_dir, case_dir / f"{label}.log")
        outputs.append(case_dir / out)
    return outputs


def ledger_payload(ledger_path):
    ledger = json.loads(ledger_path.read_text())
    return {"paper_id": ledger["paper_id"], "observability_level": ledger["observability_level"],
            "claims": ledger["claims"]}


def model_prompt(cases, patterns, skills, hints):
    payload = [{"case_id": c["id"], "ledger": ledger_payload(c["ledger"])} for c in cases]
    return ("Audit only the evidence ledgers below using the existing Anti-Autoresearch "
        "finding contract. Do not invent a taxonomy. Review every case independently. "
        "Propose at most one finding per case and omit clean cases. Use only a pattern "
        "from the supplied catalog and a domain audit skill from the supplied schema; "
        "evidence-ledger is the extractor and must not be used for an audit finding. Every evidence "
        "span must be verbatim from that case's claim and cite its claim_id. Report a "
        "discrepancy for a human to check, never misconduct or an authorship verdict. "
        "Advisory ADV patterns are allowed and remain zero verdict weight. Return only "
        "a JSON array of objects shaped as {case_id, finding}; no markdown. The finding "
        "must contain finding_id, skill, pattern_id, title, description, severity, "
        "evidence, verdict_local, observability_level_required, false_positive_risk, "
        "and recommended_reviewer_action. Use severity critical/major/minor/info and "
        "verdict_local fail/warn/clean/needs_external_check.\n\n"
        f"SKILLS={json.dumps(sorted(skills))}\nPATTERNS={json.dumps(sorted(patterns))}\n"
        f"PATTERN_DEFINITIONS={json.dumps(hints, ensure_ascii=False)}\n"
        f"CASES={json.dumps(payload, ensure_ascii=False)}"
    )


def call_model(prompt, env):
    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Return only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        "max_completion_tokens": 7000,
    }).encode()
    url = env["baseurl"].rstrip("/") + "/chat/completions"
    req = request.Request(url, data=body, headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {env['apikey']}"
    })
    with request.urlopen(req, timeout=180) as response:
        return json.loads(response.read().decode())


def response_content(response):
    content = response["choices"][0]["message"]["content"]
    if isinstance(content, list):
        return "".join(part.get("text", "") for part in content if isinstance(part, dict))
    return content


def parse_model_json(content):
    match = re.search(r"\[[\s\S]*\]", content)
    if not match:
        raise ValueError("model response did not contain a JSON array")
    value = json.loads(match.group(0))
    return value if isinstance(value, list) else []


def valid_anchor(finding, ledger):
    claims = {c["claim_id"]: c.get("text_span", "") for c in ledger["claims"]}
    for evidence in finding.get("evidence", []):
        claim = claims.get(evidence.get("claim_id"))
        span = " ".join(str(evidence.get("span", "")).split())
        if claim and span and span in " ".join(claim.split()):
            return True
    return False


def normalize_aliases(finding):
    if "pattern_id" not in finding and finding.get("pattern"):
        finding["pattern_id"] = finding.pop("pattern")
    if "description" not in finding and finding.get("discrepancy"):
        finding["description"] = finding.pop("discrepancy")
    for evidence in finding.get("evidence", []):
        if "span" not in evidence and evidence.get("text_span"):
            evidence["span"] = evidence.pop("text_span")


def default_finding_fields(finding, index):
    finding.setdefault("finding_id", f"MODEL{index:03d}")
    finding.setdefault("title", finding["pattern_id"])
    finding.setdefault("severity", "info")
    finding.setdefault("verdict_local", "needs_external_check")
    finding.setdefault("observability_level_required", 0)
    finding.setdefault("false_positive_risk", "high")
    finding.setdefault("recommended_reviewer_action", "Ask a human reviewer to verify the anchored discrepancy.")


def normalize_item(index, item, by_id, skills, patterns):
    case_id = item.get("case_id") if isinstance(item, dict) else None
    finding = item.get("finding") if isinstance(item, dict) else None
    if case_id not in by_id or not isinstance(finding, dict):
        return None, {"index": index, "reason": "missing case or finding"}
    normalize_aliases(finding)
    if finding.get("skill") not in skills or finding.get("pattern_id") not in patterns:
        return None, {"index": index, "reason": "unknown skill or pattern"}
    ledger = json.loads(by_id[case_id]["ledger"].read_text())
    if not valid_anchor(finding, ledger):
        return None, {"index": index, "reason": "evidence is not anchored"}
    default_finding_fields(finding, index)
    required = ("title", "description", "severity", "evidence", "verdict_local")
    if any(key not in finding for key in required):
        return None, {"index": index, "reason": "missing finding field"}
    finding.setdefault("reviewer", {"model": MODEL})
    return (case_id, finding), None


def normalize_model_findings(items, cases, skills, patterns):
    by_id = {case["id"]: case for case in cases}
    grouped = {case["id"]: [] for case in cases}
    invalid = []
    for index, item in enumerate(items, 1):
        result, error = normalize_item(index, item, by_id, skills, patterns)
        if error:
            invalid.append(error)
            continue
        case_id, finding = result
        grouped[case_id].append(finding)
    return grouped, invalid


def adjudicate(case_dir, deterministic, model_findings, anti_root, paper_id):
    model_path = case_dir / "model.findings.json"
    write_json(model_path, model_findings)
    args = [sys.executable, str(anti_root / "tools/adjudicate_findings.py"),
            "--findings", *[str(p.name) for p in deterministic], str(model_path.name),
            "--ledger", "claims.json", "--paper-id", paper_id,
            "--observability-level", "2", "--generated-at", GENERATED_AT,
            "--out", "report.json", "--md", "REPORT.md"]
    run_command(args, case_dir, case_dir / "adjudicator.log")
    return json.loads((case_dir / "report.json").read_text())


def pattern_ids(findings):
    return sorted({f.get("pattern_id") for f in findings if f.get("pattern_id")})


def case_result(case, deterministic_paths, model_findings, report):
    det = []
    for path in deterministic_paths:
        det += json.loads(path.read_text())
    proposed = pattern_ids(det)
    model = pattern_ids(model_findings)
    shown = pattern_ids([f for f in report["findings"] if f.get("_severity_final") != "info"])
    expected_det = case["expected_deterministic"]
    expected_model = case["expected_model"]
    return {
        "id": case["id"], "kind": case["kind"], "supported": case["support"],
        "support_basis": case["support_basis"],
        "expected_deterministic": expected_det, "deterministic_proposed": proposed,
        "expected_model": expected_model, "model_proposed": model,
        "model_survived_above_info": sorted(set(model) & set(shown)),
        "report_verdict": report["overall_verdict"], "counts": report["counts"],
        "deterministic_expected_hit": all(p in proposed for p in expected_det),
        "model_expected_hit": all(p in model for p in expected_model),
    }


def aggregate(results):
    det_expected = [p for r in results for p in r["expected_deterministic"]]
    det_hits = [p for r in results for p in r["expected_deterministic"] if p in r["deterministic_proposed"]]
    supported = [r for r in results if r["supported"]]
    model_expected = [p for r in supported for p in r["expected_model"]]
    model_hits = [p for r in supported for p in r["expected_model"] if p in r["model_proposed"]]
    unsupported = [{"id": r["id"], "expected": r["expected_model"],
                    "basis": r["support_basis"]} for r in results if not r["supported"]]
    clean = [r for r in results if r["kind"] == "clean"]
    return {
        "deterministic_recall": len(det_hits) / len(det_expected) if det_expected else 1.0,
        "model_proposal_recall": len(model_hits) / len(model_expected) if model_expected else 1.0,
        "clean_false_positive_patterns": sorted({p for r in clean for p in r["deterministic_proposed"] + r["model_proposed"]}),
        "deterministic_expected": len(det_expected), "deterministic_hits": len(det_hits),
        "model_expected": len(model_expected), "model_hits": len(model_hits),
        "unsupported_cases": unsupported,
    }


def upload(run_dir, remote_root):
    remote_dir = remote_path(remote_root, run_dir.name)
    parent = str(Path(remote_dir).parent)
    subprocess.run(["ssh", "smYuHangLab2", "mkdir", "-p", parent], check=True)
    subprocess.run(["scp", "-r", str(run_dir), f"smYuHangLab2:{parent}/"], check=True)
    return f"smYuHangLab2:{remote_dir}"


def remote_path(remote_root, run_id):
    return remote_root.split(":", 1)[-1].rstrip("/") + "/" + run_id


def run_antitests(anti_root, run_dir):
    commands = ("eval/run_eval.py", "tests/test_adjudicator.py", "tests/test_countercheck.py")
    logs = ("anti-eval.log", "anti-adjudicator-tests.log", "anti-countercheck-tests.log")
    for command, log in zip(commands, logs):
        run_command([sys.executable, str(anti_root / command)], anti_root, run_dir / log)


def prepare_cases(cases, run_dir, anti_root):
    prepared = []
    for case in cases:
        case_dir, ledger = build_case(case, run_dir, anti_root)
        case.update({"ledger": ledger, "dir": case_dir, "deterministic": run_deterministic(case_dir, anti_root)})
        prepared.append(case)
    return prepared


def model_findings(prepared, patterns, skills, hints, env, run_dir):
    prompt = model_prompt(prepared, patterns, skills, hints)
    response = call_model(prompt, env)
    (run_dir / "model.response.json").write_text(json.dumps(response, indent=2), encoding="utf-8")
    items = parse_model_json(response_content(response))
    return normalize_model_findings(items, prepared, skills, patterns)


def evaluate_cases(prepared, grouped, anti_root):
    results = []
    for case in prepared:
        findings = grouped[case["id"]]
        report = adjudicate(case["dir"], case["deterministic"], findings, anti_root, case["id"])
        results.append(case_result(case, case["deterministic"], findings, report))
    return results


def write_run_files(run_dir, summary, run_id, cases, anti_root, remote_dir):
    summary["remote_dir"] = remote_dir
    write_json(run_dir / "summary.json", summary)
    shutil.copy2(Path(__file__), run_dir / "run_auditbench.py")
    manifest = {"run_id": run_id, "generated_at": GENERATED_AT, "model": MODEL,
                "anti_autoresearch_root": str(anti_root), "anti_autoresearch_commit": anti_commit(anti_root),
                "benchmark_script_sha256": sha256_file(Path(__file__)), "case_count": len(cases),
                "summary": "summary.json", "anti_eval_fixture_root": str(anti_root / "eval/fixtures"),
                "anti_eval_reused_verbatim": True, "remote_dir": remote_dir,
                "deterministic_tools": ["build_claim_ledger.py", "check_numeric_consistency.py", "check_stat_consistency.py", "check_presentation.py", "adjudicate_findings.py"]}
    write_json(run_dir / "manifest.json", manifest)


def execute_run(args, run_id, anti_root, env, cases, patterns, skills, hints):
    with tempfile.TemporaryDirectory(prefix="auditbench-") as temp:
        run_dir = Path(temp) / run_id
        run_dir.mkdir()
        run_antitests(anti_root, run_dir)
        prepared = prepare_cases(cases, run_dir, anti_root)
        grouped, invalid = model_findings(prepared, patterns, skills, hints, env, run_dir)
        results = evaluate_cases(prepared, grouped, anti_root)
        summary = {"run_id": run_id, "model": MODEL, "results": results,
                   "metrics": aggregate(results), "invalid_model_items": invalid}
        remote_dir = f"smYuHangLab2:{remote_path(args.remote_root, run_id)}"
        write_run_files(run_dir, summary, run_id, cases, anti_root, remote_dir)
        uploaded_dir = upload(run_dir, args.remote_root)
        if uploaded_dir != remote_dir:
            raise RuntimeError(f"remote upload mismatch: {uploaded_dir} != {remote_dir}")
        print(json.dumps(summary, indent=2, ensure_ascii=False))


def main():
    args = parse_args()
    anti_root = Path(args.anti_root).resolve()
    if not (anti_root / "tools/adjudicate_findings.py").exists():
        raise SystemExit(f"Anti-Autoresearch not found: {anti_root}")
    run_id = args.run_id or dt.datetime.now(dt.timezone.utc).strftime("audit-%Y%m%dT%H%M%SZ")
    env = read_env(Path(__file__).parents[2] / ".env")
    if not env.get("baseurl") or not env.get("apikey"):
        raise SystemExit(".env must provide baseurl and apikey")
    skills, patterns, hints = anti_catalog(anti_root)
    cases = scenario_data()
    validate_expected(cases, patterns)
    execute_run(args, run_id, anti_root, env, cases, patterns, skills, hints)


def anti_commit(anti_root):
    try:
        return subprocess.check_output(["git", "-C", str(anti_root), "rev-parse", "HEAD"], text=True).strip()
    except subprocess.CalledProcessError:
        return "unknown"


if __name__ == "__main__":
    main()
