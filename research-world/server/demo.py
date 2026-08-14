from __future__ import annotations

import json
from pathlib import Path

from .config import ROOT, load_settings
from .project_profile import initialize_project


QUESTION_IDS = (1, 2, 13, 17, 49, 55, 88, 95)


def seed(world) -> list[dict]:
    questions = json.loads((ROOT.parent / "docs" / "questions.json").read_text(encoding="utf-8-sig"))
    selected = [item for item in questions if item["id"] in QUESTION_IDS]
    return [_create_project(world, item) for item in selected]


def _create_project(world, question: dict) -> dict:
    name = f"Q{question['id']:03d} · {question['title']}"
    try:
        return world.project_by_name(name)
    except KeyError:
        root = load_settings().projects_root / f"question-{question['id']:03d}"
        if not root.exists():
            initialize_project(root)
        return world.create_project(name, root, question["full_text"])


def curated_directions(question_id: int) -> list[dict]:
    return CURATED[question_id]


def direction(title: str, workflow: str, rationale: str, completion: str, remaining: str) -> dict:
    return {"title": title, "workflow": workflow, "rationale": rationale, "completion_test": completion, "remaining": remaining}


CURATED = {
    1: [direction("Primes as multiplicative atoms", "proof_boundary", "Separate definition, irreducibility, and unique factorization.", "A bounded proof map states every obligation and domain.", "Generalization beyond the integers."), direction("Prime distribution at finite scales", "computation", "Measure density and gaps without turning samples into universal laws.", "A replayed finite-range analysis with explicit bounds.", "Asymptotic and open conjectures."), direction("Primality versus factorization", "evidence_synthesis", "Explain why testing primality and finding factors are different computational tasks.", "Complexity claims are tied to authoritative sources.", "Implementation-specific performance."), direction("What cryptography actually needs", "evidence_synthesis", "Distinguish primes, trapdoor constructions, and hardness assumptions.", "The explanation does not claim all cryptography depends on primes.", "Post-quantum alternatives.")],
    2: [direction("Proof status and obligations", "proof_boundary", "Map the exact theorem, equivalent statements, and why finite checks are not proof.", "A proof-boundary dossier with no solved claim.", "A valid proof or disproof."), direction("Finite zero verification", "computation", "Reproduce a small numerical check while labeling its logical limit.", "A replayed finite verification receipt.", "The infinite proposition."), direction("Consequences for prime counting", "evidence_synthesis", "Trace conditional consequences and unconditional results.", "Every consequence is labeled conditional or unconditional.", "Sharper error bounds."), direction("Competing analytic approaches", "open_world_search", "Compare current method families without predicting a winner.", "A source-backed landscape and unresolved bottlenecks.", "Novel proof machinery.")],
    13: [direction("Outbreak risk backtest", "forecast", "Turn prediction into a horizon, target, baseline, and retrospective score.", "A replayed baseline backtest reports calibration limits.", "Prospective validation."), direction("Zoonotic spillover surveillance", "open_world_search", "Map observable precursors and detection coverage.", "A coverage matrix separates observed signals from blind spots.", "Unknown pathogens and reporting delay."), direction("Health-system surge readiness", "engineering_design", "Optimize preparedness under capacity and cost constraints.", "A requirements and tradeoff dossier.", "Local operational validation."), direction("Prediction versus preparedness", "conceptual_discrimination", "Separate forecasting claims from robust decision policies.", "Competing objectives and decision thresholds are explicit.", "Value judgments and policy choice.")],
    17: [direction("Human immune-cell perturbation platform", "wet_lab_proposal", "Specify a manipulative human-cell study instead of pretending Docker supplies observations.", "An executable protocol, controls, endpoints, and manual result slots.", "Ethics approval, samples, and wet-lab execution."), direction("Feedback control across immune compartments", "evidence_synthesis", "Map regulatory loops and timescales.", "Claims are scoped to cell type and perturbation.", "Cross-tissue causal validation."), direction("Patient heterogeneity", "open_world_search", "Characterize variability and confounding in human cohorts.", "A stratification and missing-data plan.", "Prospective cohort data."), direction("Rebalancing interventions", "engineering_design", "Frame immune modulation as constrained control.", "Candidate interventions include failure modes and safety gates.", "Clinical testing.")],
    49: [direction("Conservative orbit simulation", "simulation", "Test the premise in an ideal Sun-Earth two-body model and measure energy and semi-major-axis drift.", "A replayed SciPy integration reports conservation error and drift.", "Tides, stellar evolution, and N-body perturbations."), direction("Dissipative mechanisms", "evidence_synthesis", "Separate tidal decay, drag, radiation, and stellar mass loss by regime.", "Each mechanism has a signed effect and applicability range.", "System-specific parameters."), direction("Long-term Solar System stability", "open_world_search", "Distinguish orbital decay from chaotic instability.", "The search coverage and uncertainty are explicit.", "Billion-year empirical confirmation."), direction("Premise correction", "proof_boundary", "Explain why gravity alone does not cause spiraling in a conservative two-body system.", "The energy and angular-momentum argument is complete.", "Non-conservative real-world effects.")],
    55: [direction("Technosignature search coverage", "open_world_search", "Translate non-detection into surveyed parameter space and sensitivity.", "A coverage statement never infers nonexistence.", "Unsearched frequencies, distances, and signal classes."), direction("Atmospheric biosignature ambiguity", "evidence_synthesis", "Compare biological and abiotic explanations.", "Each signature includes false positives and required follow-up.", "Direct samples or convergent observations."), direction("Target prioritization", "engineering_design", "Rank observations under telescope-time constraints.", "A multi-objective selection dossier.", "Mission allocation decisions."), direction("Operational definitions of life", "conceptual_discrimination", "Expose how conclusions depend on definitions and detection thresholds.", "Alternative definitions yield discriminating observations.", "Consensus and new life forms.")],
    88: [direction("Regolith construction trade study", "engineering_design", "Compare processing routes under energy, mass, strength, and maintenance constraints.", "A requirements matrix and bounded candidate comparison.", "Mars material tests and prototypes."), direction("ISRU process simulation", "simulation", "Model a small mass-energy balance for one manufacturing chain.", "A replayed balance with sensitivity ranges.", "Pilot-plant validation."), direction("Autonomous maintenance", "engineering_design", "Design repair and spares strategies for communication delay.", "Failure modes, redundancy, and intervention thresholds.", "Hardware reliability data."), direction("Environmental qualification", "open_world_search", "Map temperature, dust, radiation, and gravity evidence to requirements.", "Every requirement has a source and uncertainty.", "Site-specific measurements.")],
    95: [direction("Competing theory predictions", "conceptual_discrimination", "Freeze operational definitions and compare discriminating predictions.", "At least two theories produce distinct measurable outcomes.", "Decisive experiments and conceptual consensus."), direction("Perturbational complexity", "evidence_synthesis", "Assess what neural perturbation studies can and cannot localize.", "Claims separate correlation, necessity, and sufficiency.", "Cross-method causal evidence."), direction("Reportability and subjective experience", "engineering_design", "Design measurements that expose proxy assumptions.", "A measurement dossier lists construct validity failures.", "Access to first-person ground truth."), direction("Quantum microtubule claims", "open_world_search", "Audit evidential support without treating controversy as refutation.", "Claims and counterclaims have source-backed observability limits.", "Replicated discriminating evidence.")],
}
