---
sources:
  - title: Matbench
    url: https://github.com/materialsproject/matbench
  - title: Matbench paper
    url: https://doi.org/10.1038/s41524-020-00406-3
---
# Matbench smoke
`matbench_expt_gap` provides 4604 experimental band-gap samples, five fixed folds, official recording, validation and regression metrics. `run.py` uses a training-mean prediction only to exercise that lifecycle; it is not a SearchBench method or baseline claim.
Remote artifacts: `/data/zsm/ai4sci-design-bench-20260809/matbench-smoke/artifacts`. Matbench 0.6 loaded all 4604 samples, recorded 5/5 folds, passed `MatbenchTask.validate()`, and wrote the official benchmark result. The smoke mean MAE is 1.1435269609161665; the task metadata MAD is 1.1432002429044061.
The PyPI package pins scikit-learn 1.0.1, which has no compatible wheel in this Python 3.10 environment. The official Matbench wheel was installed without dependencies, then run against scikit-learn 1.5.2 and current declared runtime libraries; no Matbench source was modified.
