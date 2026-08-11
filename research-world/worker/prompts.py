from __future__ import annotations


SUBMISSION_SCHEMA = """Write submission.json with exactly these top-level fields:
{
  "kind": "KIND",
  "title": "specific result title",
  "summary": "concise evidence-grounded summary",
  "content": {},
  "dependencies": ["input node ids used by this result"]
}
Use valid JSON. Put findings, evidence, methods, and limitations inside content."""

SUBMISSION_KINDS = {"plan": "action", "research": "result", "html_report": "report"}


PLAN_PROMPT = f"""Read context.json and plan the next step for the supplied scientific subject.
Plan exactly one concrete, testable scientific action. Do not execute the action, run experiments, or claim results.
{SUBMISSION_SCHEMA.replace('KIND', 'action')}
In content include prompt with the exact action an executor should perform.
Do not create report.html or any planning files.
Do not finish until submission.json exists at the workspace root."""

RESEARCH_PROMPT = f"""Read context.json, then complete job.prompt for the supplied scientific subject.
Base claims on concrete evidence. Record source URLs or workspace paths and state limitations. Never invent results.
{SUBMISSION_SCHEMA.replace('KIND', 'result')}
Do not finish until submission.json exists at the workspace root."""

HTML_PROMPT = f"""Read context.json, then create a polished static detail page for the supplied scientific subject.
First write submission.json. Then write report.html. Do not create planning or memory files.
Use semantic, responsive HTML with embedded CSS, no external assets, scripts, forms, or remote resources. Show concrete data, evidence sources, provenance, and limitations from the supplied context. Do not invent facts.
{SUBMISSION_SCHEMA.replace('KIND', 'report')}
In content include report_file set to report.html and a short sections list.
Do not finish until both report.html and submission.json exist at the workspace root."""

AUDIT_PROMPT = """Read context.json and audit the pending subject against only its admitted dependencies.
The job prompt identifies the producer job and revision. Do not seek or reconstruct the producer conversation.
Write audit.json with exactly these top-level fields:
{
  "decision": "approve | revise | restart",
  "feedback": "minimal actionable feedback; may be empty only for approve",
  "checks": ["concrete check and outcome derived from this candidate"]
}
Use valid JSON. Do not use a fixed defect taxonomy. Do not create submission.json or report.html.
Do not finish until audit.json exists at the workspace root."""


REVISION_FILES = {
    "plan": "Rewrite submission.json with one revised action before finishing.",
    "research": "Rewrite submission.json before finishing.",
    "html_report": "First rewrite submission.json, then rewrite report.html before finishing.",
}


def revision_prompt(job: dict) -> str:
    scope = job["review_scope"]
    if scope not in {"node", "artifact"}:
        raise ValueError(f"unsupported review scope: {scope}")
    constraint = "Preserve the scientific submission." if scope == "artifact" else "Revise the rejected scientific submission."
    opening = "Continue the same session" if job["review_mode"] == "continue" else "Start a fresh attempt"
    return f"""{opening} and address the review rejection below.
Rejected object: {scope}
Reviewer feedback: {job['review_feedback']}
{constraint} Keep accepted work unchanged.
{REVISION_FILES[job['kind']]}"""


def task_prompt(job: dict) -> str:
    kind = job["kind"]
    prompts = {"plan": PLAN_PROMPT, "research": RESEARCH_PROMPT,
               "html_report": HTML_PROMPT, "audit": AUDIT_PROMPT}
    if kind == "audit":
        return prompts[kind]
    if kind not in prompts or kind not in REVISION_FILES:
        raise ValueError(f"unsupported job kind: {kind}")
    return revision_prompt(job) if job["revision"] > 0 else prompts[kind]
