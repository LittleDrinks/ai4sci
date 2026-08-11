---
sources:
  - title: ResearchClawBench code and task format
    url: https://github.com/InternScience/ResearchClawBench
  - title: ResearchClawBench dataset mirror
    url: https://huggingface.co/datasets/InternScience/ResearchClawBench
  - title: ResearchHarness
    url: https://github.com/InternScience/ResearchHarness
  - title: PaperBench code
    url: https://github.com/openai/preparedness/tree/main/project/paperbench
  - title: ScienceAgentBench code and artifacts
    url: https://github.com/OSU-NLP-Group/ScienceAgentBench
  - title: ResearchGym code
    url: https://github.com/Anikethh/ResearchGym
  - title: Science-Gym code
    url: https://github.com/pibborn/science-gym
  - title: AstaBench code
    url: https://github.com/allenai/asta-bench
  - title: CORE-Bench code
    url: https://github.com/siegelz/core-bench
  - title: MLE-bench code
    url: https://github.com/openai/mle-bench
  - title: RE-Bench code
    url: https://github.com/METR/RE-Bench
  - title: LongMemEval-V2 code
    url: https://github.com/xiaowu0162/LongMemEval-V2
  - title: AMA-Bench code
    url: https://github.com/AMA-Bench/AMA-Bench
  - title: STATE-Bench code
    url: https://github.com/microsoft/STATE-Bench
  - title: HypoBench code
    url: https://github.com/ChicagoHAI/hypothesis-generation
  - title: HypoBench datasets
    url: https://github.com/ChicagoHAI/HypoBench-datasets
  - title: EvidenceBench
    url: https://github.com/EvidenceBench/EvidenceBench
  - title: RINoBench
    url: https://github.com/TimSchopf/RINoBench
  - title: ProjectionBench
    url: https://arxiv.org/abs/2605.30284
  - title: TELBench and DRIFT
    url: https://github.com/NJU-LINK/DRIFT
  - title: AgentRx
    url: https://github.com/microsoft/AgentRx
  - title: Auto Benchmark Audit
    url: https://github.com/IsThatYou/auto-bench-audit
---
# Reuse inventory
## Directly reused
| Resource | Reusable unit | License/cost | SearchBench decision |
| --- | --- | --- | --- |
| ResearchClawBench | `tasks/<TaskID>/task_info.json` plus `data/`, `related_work/`, and hidden `target_study/` layout; official 40-task corpus | GitHub repository MIT; task data is public and downloaded per file; model/API and GPU costs are external | Directly reused `Astronomy_000` task description and two posterior files at commit `595f318e`; target paper, checklist, figures, and related papers stay out of the agent workspace. Its task text prescribes the target Bayesian mechanism, so it is suitable for reproduction and Harness integration, not method-space search |
| ResearchHarness | Python `create_agent`, OpenAI-compatible client, explicit workspace root, `max_rounds`, role prompt, and flat JSONL trace with LLM usage | MIT; self-hosted; API/model calls are paid by the configured provider | Direct runtime. The runner does not implement an agent loop or token parser; it uses the public API and retains the trace path/hash outside graph events |
## Reusable with an adapter
| Resource | Reusable unit | License/cost | Boundary for this design |
| --- | --- | --- | --- |
| PaperBench | paper + hierarchical rubric; rollout, fresh-container reproduction, and judge stages | OpenAI code/data repository is public; compute requires isolated containers and often GPU; model/API cost is external | Reuse its separation of rollout and fresh reproduction plus hierarchical rubric for a future SearchBench execution score. Its 8,316 rubric items and 20 ML papers are too large for the instrumentation run |
| ScienceAgentBench | 102 expert-validated data-driven science tasks, each targeting a self-contained Python program; execution/cost metrics and containerized evaluator | Repository MIT; verified split and password-protected benchmark artifacts must be downloaded, and the README forbids redistributing the unzipped data; execution cost depends on generated programs | Reuse task-to-program contract and evaluator separation for candidate-action executability. It evaluates code outputs, not graph disclosure or session rotation, so it cannot replace the SearchBench policy factor |
| ResearchGym | closed-loop AI-research environments and standardized research metrics | Public repository and task descriptions; no repository license is asserted in the README, so treat it as source-available until checked; default run budget is $10 plus model/API and optional Docker costs | Reuse its closed-loop experiment abstraction when adding a real executor. It is closer to process evaluation than a static report benchmark, but task integration is more involved than the current RCB file contract |
| Science-Gym | Gym-compatible simulations where an agent collects data, designs experiments, and discovers equations | Article is CC BY 4.0; local simulation cost is low and the library does not require an external LLM API; confirm code-repository terms before redistribution | Reuse as a cheap controlled benchmark for stop-condition and feedback ablations after the real-task instrumentation. It tests discovery in synthetic environments, not literature-grounded method families |
| AstaBench | Inspect AI runner, standardized tools and environments, more than 2,400 examples across 11 scientific-research benchmarks | Apache-2.0; model, retrieval and execution costs remain external | Evaluate first as the common benchmark runner. It may replace custom orchestration while ResearchHarness remains the system-under-test agent runtime |
| CORE-Bench | 270 computational-reproduction tasks from 90 papers, question grader and isolated Docker/Azure harness | MIT; capsules are downloaded on demand; Docker execution can be expensive | Reuse for reproduction and artifact-audit nodes. It does not evaluate open-ended mechanism search |
| MLE-bench | Kaggle task construction, isolated agent runtime and submission grader | MIT; competition data and GPU/API costs vary | Reuse a small task subset for low-cost CS experiment execution and budget accounting, not for scientific novelty |
| RE-Bench | METR Task Standard, AI R&D tasks, Vivaria-compatible evaluation | MIT; task execution and model costs vary | Reuse its task contract and time-budgeted evaluation when comparing agent SDKs |
| LongMemEval-V2 | 451 curated questions over multimodal agent trajectories, compact-evidence interface, accuracy and latency scoring | Apache-2.0; small and medium public tiers; reader and optional retrieval-model cost | Reuse to compare graph sedimentation against raw slices and trajectory notes. Its state, workflow, gotcha and premise-awareness abilities match condition-loss risk without inventing a custom memory corpus |
| AMA-Bench | Real agent trajectories with expert QA, scalable synthetic trajectories with rule-based QA, `memory_construction`/`memory_retrieve` interface and judge | MIT code and dataset; public test object is 50.45 MB; answer and judge model costs are external | Reuse after LongMemEval to test objective, causal and state retention across machine-generated trajectories. Compare the product graph through the official memory interface; do not reuse AMA-Agent's causal graph as product schema |
| STATE-Bench | Agent Learning Track with 100 train trajectories and 50 held-out tasks per domain, read-only `retrieve_learnings` hook, stateful tools, deterministic assertions and five-run reliability | MIT; locked simulator and judge require GPT-5.4; agent model and learning artifact are configurable | Reuse to compare no history, full-history summary, scoped graph retrieval and isolated rejected history. It tests whether disclosed experience improves held-out execution, not whether scientific mechanisms are novel |
| HypoBench | Seven real tasks, controlled synthetic tasks, fixed train/test/OOD splits, hypothesis generation and inference pipeline, accuracy and F1 | MIT code and datasets; model calls are external | Reuse to test whether admitted candidate hypotheses improve unseen and shifted-data prediction as noise, distractors and rule depth grow. It does not validate causal mechanisms, experimental evidence or novelty; its hypothesis bank is not product schema |
| EvidenceBench | 426 biomedical hypothesis-paper pairs with sentence-level evidence aspects, optimal and fixed-budget retrieval gold, embedding and generation evaluators | MIT code; original test is CC-BY, train/dev are CC-BY-NC-SA; 100k extension is CC-BY-NC | Reuse the original set to compare whole-paper storage, graph evidence and query-time extraction. It evaluates evidence retrieval, not whether the hypothesis is true; aspect labels stay inside the benchmark adapter |
| TELBench / DRIFT | 1,000 expert-verified deep-research trajectories, harmful error-span gold labels, bare and claim-centric baselines | Dataset card Apache-2.0; code repository has no explicit license; model cost external | Reuse TELBench as the error-localization dataset. Run DRIFT unchanged only as an internal baseline; do not vendor its code or treat its claim graph as the product schema |
| AgentRx | 73 public trajectories with critical failure-step ground truth across Magentic-One and τ-bench; invariant and judge pipeline | MIT; paper reports 115 cases but Flash data is not in the repository; pipeline clients target Azure/TRAPI | Reuse trajectories and critical-step labels. Ignore the ten-category taxonomy as product schema; its distinction between chronological failure and critical root cause is the benchmark signal |
| Auto Benchmark Audit | benchmark/task manifest collector plus instruction, environment and evaluator audits | Public source; Python 3.12+; repository has no root license covering the CLI | Run unchanged as an internal quality gate before trusting a reused benchmark. Do not vendor it, treat its rubric as product schema, or count its findings as system capability |
## Evaluator reuse
| Source | What can be lifted | What remains missing |
| --- | --- | --- |
| ResearchClawBench checklist/judge | weighted text/image checklist, separate report scoring | It is hidden-target scoring and does not judge whether two actions share a mechanism; a method-family pairwise adjudicator is still needed |
| PaperBench rubric/judge | hierarchical decomposable requirements and independent judge benchmark | It grades replication artifacts, not graph admission, isolation, or disclosure policy |
| ScienceAgentBench evaluator | program execution plus output/cost measurements | It assumes a complete Python program, while SearchBench first scores candidate actions before selecting representatives |
| AstaBench / Inspect AI | common agent, task, scorer and sandbox interface across existing science benchmarks | It standardizes execution but does not supply our admission, context-rotation or mechanism-equivalence judgments |
| CORE-Bench / MLE-bench | executable artifact graders with hidden or external ground truth | They can score execution outcomes after an action is selected; they cannot score whether the search policy escaped an existing method family |
| RINoBench | 1,381 expert novelty scores, related works and grounded rationales can calibrate novelty judges | Public repository has no stated license and covers ICLR/ML ideas; do not vendor it or treat its five-point rubric as a global mechanism taxonomy |
## Constraints
- Do not copy all public task data into this repository; pin a commit and fetch only the selected task files into the remote experiment directory.
- Keep hidden target artifacts outside every planning workspace. They may be used later by an evaluator process, never by the planning agent.
- Preserve original Harness traces as evaluation trajectories; only structured events and hashes enter the SearchBench result stream.
- Report API/model cost separately from candidate quality. The public benchmark repositories do not provide a free model endpoint.
## Scouted but not adopted
| Resource | Reason |
| --- | --- |
| RINoBench | Expert novelty scores and related works are useful for judge calibration, but commit `d94cd7b3` has no repository license and covers ICLR/ML ideas. Do not download or turn its five-point rubric into a product taxonomy |
| ProjectionBench | Progressive disclosure over 45 recent materials papers closely matches the product question, but only the paper is public; no runnable code or dataset was found. Revisit only when the authors publish artifacts |
