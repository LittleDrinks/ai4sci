---
sources:
  - title: HypoBench code
    url: https://github.com/ChicagoHAI/hypothesis-generation
  - title: HypoBench datasets
    url: https://github.com/ChicagoHAI/HypoBench-datasets
---
# HypoBench candidate utility
Official code commit `bd37a3129a2f98ee586f545a57b10b59496eedad` and dataset commit `7e4bbc341ee90b7efaa607f67a81543cd68cdf2e` are extracted remotely under `/data/zsm/ai4sci-design-bench-20260809/hypobench`; both are MIT. Archive SHA-256 values are `4296a5fc0f9871cb5928fa6a50616a1a0bea5ddc03a34fb82dcbb70c00193d1f` and `90b8714a8f189f02305937d60d766164debc0e04a62a6bddaf7c058af7765b3e`. The dataset contains 16 real and 181 synthetic `config.yaml` files; code compilation passes.
All 197 configs were checked against their declared train, test, validation and OOD paths. Eighteen references in `synthetic/election/level0..5` use stale filenames without the `_levelN` suffix; every other referenced file exists and all JSON columns have equal length. Run only configs that pass this preflight and report the upstream defect unchanged.
Compare no hypotheses, unreviewed hypotheses, graph-admitted relevant hypotheses and literature-assisted admitted hypotheses with the same model, split, seed, sample count and hypothesis budget. Reuse the official generation/inference pipeline and report accuracy, F1, OOD change, Token and latency by task, rule depth, noise and distractor level. The graph adapter may select and disclose candidates but cannot read test labels.
This measures whether candidate rules help prediction on unseen or shifted data. It does not establish causality, experimental validity or novelty. The official hypothesis bank and task taxonomy stay inside the benchmark adapter and do not define product nodes.
