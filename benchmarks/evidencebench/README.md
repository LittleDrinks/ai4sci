---
sources:
  - title: EvidenceBench
    url: https://github.com/EvidenceBench/EvidenceBench
---
# EvidenceBench literature evidence
Official commit `bf1d9633c694381c7b016fd56ee9f95f48593cc3` is extracted remotely at `/data/zsm/ai4sci-design-bench-20260809/evidencebench/source`; archive SHA-256 is `6912b6014586176b542e1f0075d12cccb9de34de7f16914fee42d83a2033fe4a`. Code is MIT. The original test set is CC-BY; train and dev are CC-BY-NC-SA. The 100k extension is not downloaded.
The original set contains 96 train, 37 dev and 293 test hypothesis-paper pairs. Every instance supplies ordered candidate sentences, evidence aspects and optimal or fixed-budget gold selections. All 1,688 non-null gold selections have in-range sentence indices and consistent optimal sizes. Eight papers lack results-only evidence, yielding 16 null results fields; exclude them only from results-specific metrics.
The official evaluator scores the 293 test gold-optimal selections at average coverage `1.0`; the artifact is under `/data/zsm/ai4sci-design-bench-20260809/evidencebench/smoke`. Its over-budget branch repeatedly randomizes truncation, so every comparison must emit at most the fixed sentence budget and stay on the deterministic branch.
Compare full-paper disclosure, admission-time evidence extraction, query-time extraction and admitted evidence plus query-time completion with the official evaluator. Hold the model, paper, query and sentence budget fixed; report aspect recall, sentence precision, disclosed tokens, latency and construction cost. Benchmark aspects remain evaluator labels, not product node types. Evidence retrieval does not establish that a hypothesis is true.
