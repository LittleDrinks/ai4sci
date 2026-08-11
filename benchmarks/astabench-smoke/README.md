---
sources:
  - title: AstaBench source
    url: https://github.com/allenai/asta-bench
  - title: AstaBench README
    url: https://github.com/allenai/asta-bench/blob/main/README.md
  - title: AstaBench license
    url: https://github.com/allenai/asta-bench/blob/main/LICENSE
  - title: Inspect AI documentation
    url: https://inspect.aisi.org.uk/
---
# AstaBench and Inspect AI smoke
## Result
Official AstaBench and Inspect AI run on `smYuHangLab2` under `/data/zsm/ai4sci-design-bench-20260809/astabench-smoke`. Inspect listed four public demo tasks, and `arithmetic_demo` completed a one-sample `mockllm/model` evaluation with exit code 0. The AstaBench wrapper generated a validation `eval_config.json` and expanded its 11 configured validation tasks with exit code 0.
## Versions and licenses
- AstaBench `0.5.4`, source commit `8fbdbbb68a73fe4a47af4ebcf1819b90b608bd36`, Apache-2.0; `NOTICE.txt` records linked third-party licenses.
- Inspect AI `0.3.233`, MIT License.
- Smoke host: Python `3.10.12`; AstaBench declares Python `>=3.11`, so the smoke installed its wheel with `--ignore-requires-python`. This is evidence for task discovery and orchestration only, not a supported production environment.
- AstaBench's full suite uses the gated `allenai/asta-bench` dataset and requires an accepted Hugging Face license plus `HF_TOKEN`; no benchmark dataset or credential was fetched.
## Reproduction
Run on the remote host; all paths below are under the artifact directory.
```sh
root=/data/zsm/ai4sci-design-bench-20260809/astabench-smoke
cd "$root/source"
PYTHONPATH="$root/site-packages" python3 -m inspect_ai._cli.main list tasks astabench/evals/demo --json
PYTHONPATH="$root/site-packages" python3 -m inspect_ai._cli.main eval \
  --solver generate --model mockllm/model --limit 1 --display plain \
  --max-connections 1 --max-samples 1 \
  --log-dir "$root/logs/mock-demo-final" \
  astabench/evals/demo/arithmetic/task.py@arithmetic_demo
PYTHONPATH="$root/site-packages" python3 -m inspect_ai._cli.main eval \
  --solver generate --model mockllm/model --limit 4 --display plain \
  --max-connections 4 --max-samples 4 \
  --log-dir "$root/logs/mock-demo-parallel" \
  astabench/evals/demo/arithmetic/task.py@arithmetic_demo
PYTHONPATH="$root/site-packages" python3 -c 'from astabench.cli import cli; cli()' \
  eval --split validation --config-only --ignore-git \
  --log-dir "$root/logs/config-only-validation"
```
## Observed output
- `list tasks --json`: `arithmetic_demo`, `arithmetic_with_style_rubric`, `arithmetic_with_tools`, and `code_demo`.
- Inspect eval: one sample, `mockllm/model`, 64 tokens (`I:31`, `O:33`), accuracy `0.000`, exit code `0`; log is under `logs/mock-demo-final/`.
- Inspect parallel eval: four samples with `--max-samples 4 --max-connections 4`, 264 tokens (`I:132`, `O:132`), accuracy `0.000`, exit code `0`; log is under `logs/mock-demo-parallel/`.
- AstaBench config-only: exit code `0`; command expands `arxivdigestables_validation`, `sqa_dev`, `litqa2_validation`, `paper_finder_validation`, `paper_finder_litqa2_validation`, `discoverybench_validation`, `core_bench_validation`, `ds1000_validation`, `e2e_discovery_validation`, `e2e_discovery_hard_validation`, and `super_validation`; config is under `logs/config-only-validation/eval_config.json`.
- The direct demo emitted a non-fatal entrypoint warning while optional AstaBench registry dependencies were absent (`mcp` in the final run). The task itself loaded and scored.
## SearchBench decision
Reuse Inspect AI for Task/Solver/Scorer contracts, structured `.eval` logs, scoring, and bounded parallelism (`--max-samples`, `--max-connections`, `--max-sandboxes`). Reuse AstaBench's suite/config wrapper only for common task selection and reproducible run metadata. Keep ResearchHarness as the system-under-test runtime and keep SearchBench admission review, graph events, context rotation, hidden-artifact boundary, and method-family adjudication in the domain layer. AstaBench is therefore a viable outer evaluation layer, not a drop-in replacement for the custom SearchBench runner; no custom runner or adapter was added in this smoke.
## Hypothesis→experiment→feedback subsets (local collection, 2026-08-10)
Same source commit `8fbdbbb68a73fe4a47af4ebcf1819b90b608bd36` is cloned at `source/`; `uv venv .venv --python 3.11` plus `uv pip install -e source` gives astabench `0.5.4` with inspect_ai `0.3.255` (satisfies the declared `>=0.3.233,<0.4` floor). Local preflight without any model call or data download: `inspect list tasks` resolves `e2e_discovery_{validation,test,hard_validation,hard_test}`, `core_bench{,_validation,_test}` (and `ds1000*`), `litqa2{,_inspect,_validation,_test}`, `paper_finder{,_litqa2}{,_validation,_test}`; `astabench eval --split validation --config-only` exits 0 and expands the same 11 validation tasks as the remote smoke. DiscoveryWorld is not an AstaBench task; the in-suite "hypothesis→experiment→feedback" subsets are E2E-Bench (`e2e_discovery`) and CORE-Bench, with LitQA2 and PaperFindingBench as the literature-facing complements.
| subset | task (suite name) | data source | scorer | paid calls |
| --- | --- | --- | --- | --- |
| E2E-Bench | `e2e_discovery{,_hard}_{validation,test}` | gated `allenai/asta-bench` `tasks/e2e_discovery/*.json` | rubric LLM judge `claude-sonnet-4-6` | agent + judge |
| CORE-Bench | `core_bench_{validation,test}` | public `siegelz/core-bench` (MIT), capsule downloads at run time | `score_with_stderr` answer match, free; medium/hard run capsules in Docker sandbox | agent only |
| LitQA2 | `litqa2_{validation,test}` | public `futurehouse/lab-bench` LitQA2 + split mapping in gated `allenai/asta-bench` | multiple-choice match, free | agent only |
| PaperFindingBench | `paper_finder_{validation,test}`, `paper_finder_litqa2_*` | gated `allenai/asta-bench` | `adjusted_f1_micro_avg` with grader `openai/gpt-4o-2024-11-20` | agent + judge |
Official baseline numbers (leaderboard UI `allenai/asta-bench-leaderboard`, raw JSON in public dataset `allenai/asta-bench-results`; cited file `1.0.0/test/Ai2_ReAct_2026-04-27T17-31-11.json`, Ai2 ReAct on `openai/gpt-5.5-2026-04-23`, astabench 0.5.3): PaperFindingBench_test 0.3603, LitQA2_FullText_Search_test recall@30 0.8533, LitQA2_FullText_test 0.8933, CORE_Bench_Hard_test 0.9189, E2E_Bench_test 0.4070, E2E_Bench_Hard_test 0.3882, DiscoveryBench_test 0.3893. Boundaries: everything except CORE-Bench stays blocked until the gated `allenai/asta-bench` license is accepted and `HF_TOKEN` set (需人工申请); E2E-Bench and PaperFindingBench also need judge API budgets; CORE-Bench medium/hard needs Docker. No eval was run here.
