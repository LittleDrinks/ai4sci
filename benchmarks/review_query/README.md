# ReviewScaling-v3
Inspect AI drives one sample per question and scale. The only model-visible state is the deterministic JSON returned by `aggregate`, `get`, `impact`, and `subgraph`; all state is folded from `benchmarks/review_scaling/source.py` windows and event records. Inspect owns the agent loop, tool execution, structured `.eval` log, token accounting, and scorer lifecycle.

Remote run:
```sh
python3 run.py --source-root /data/zsm/ai4sci-design-bench-20260809/search/full-run1 --output /data/zsm/ai4sci-design-bench-20260809/review-query/real9 --env-file .env.run --model openai/gpt-5.4-mini
```

`real9/` is the completed remote run: 8 samples, scales 12 and 36, all four questions, accuracy 1.0, 9 tool events, and Inspect model usage recorded in the `.eval` log. The report records 5853 input, 349 output, and 38970 total tokens; the raw Inspect log records 14240 input, 527 output, 81327 total, including 66560 cache-read tokens. The run used `openai/gpt-5.4-mini` through the project OpenAI-compatible endpoint with concurrency 2. `real5/run_error.json` preserves the initial missing-`OPENAI_API_KEY` diagnostic from a command that omitted `--env-file`; no credential value is recorded.
