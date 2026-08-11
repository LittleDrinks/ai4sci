---
sources:
  - title: AMA-Bench
    url: https://github.com/AMA-Bench/AMA-Bench
  - title: AMA-Bench dataset
    url: https://huggingface.co/datasets/AMA-bench/AMA-bench
---
# AMA-Bench sedimentation
Official code is pinned remotely at `/data/zsm/ai4sci-design-bench-20260809/ama-bench/source`, commit `ddfd319e0be33424288c13806f1eafc63e625b59`, MIT. The dataset revision is `a5777378066f53229a94557a7b192435cd027909`; its public open-ended test object is 50451919 bytes. The first remote download remained at zero bytes and was stopped; no dataset result exists yet.
The official `MemoryQAInterface` separates `memory_construction(trajectory, task)` from question-conditioned `memory_retrieve(memory, question)`, then uses the benchmark answerer and judge. Implement the product graph only behind this interface and compare it with official `longcontext`, BM25 and embedding baselines. Report answer accuracy, disclosed characters and tokens, construction cost, retrieval cost and latency by trajectory length. AMA-Agent remains a benchmark baseline; its causal graph is not a source for product schema.
