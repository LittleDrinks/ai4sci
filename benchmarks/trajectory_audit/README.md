---
sources:
  - title: TELBench and DRIFT
    url: https://github.com/NJU-LINK/DRIFT
  - title: TELBench dataset
    url: https://huggingface.co/datasets/NJU-LINK/TELBench
  - title: Where Do Deep-Research Agents Go Wrong?
    url: https://arxiv.org/abs/2606.02060
---
# TELBench trajectory audit
Remote root: `/data/zsm/ai4sci-design-bench-20260809/trajectory-audit`; DRIFT commit `1280b373b5af1954bf0577bf6d58b38e1bce341e`.
TELBench 提供 1000 条专家核验的 deep-research 轨迹、顺序语义段与 harmful error span 金标。官方密文和解密后 JSONL 的 SHA-256 均通过，数据 1000 行、20230340 bytes；release-contract 2/2、空预测与 oracle scorer 上下界通过。
固定切片按 `bench x difficulty` 六个分层各取最小两个 ID，共 12 条。gold、annotations 与 meta 不进入模型提示。`gpt-5.4-mini` 的 bare/DRIFT 宏 F1 为 0.1861/0.2528，首错准确率为 0.0833/0；Token 为 101940/258409。`gpt-5.6-luna` 为 0.2472/0.2528，首错为 0.0833/0；Token 为 112811/269350。36 次 DRIFT 调用均无 API 或解析回退。
TELBench 直接进入“有害错误段定位”评测。DRIFT 的 claim ledger、按需证据包与 dependency tracer 只作为公开对照；当前结果提高错误段覆盖但未找到首错，成本约为 bare 的 2.39–2.53 倍，不能代替人工可读性实验。
Mini 与 Luna 的证据选择分别保留 57/133、45/133 个语义段，却仍披露 328289/359943、329318/359943 个字符，即 91.21% 与 91.49%。语义段数量不能代理审查负担；渐进披露按实际字符、Token 和展开次数计量。
Hugging Face 数据卡标记 Apache-2.0；DRIFT 代码仓库当前没有 LICENSE 文件或 `pyproject` 许可声明。数据可按许可复用，代码只在远端内部评测中原样运行，不复制进产品。
`analyze_public_labels.py` 在官方文件上生成远端 `label-stats.json`，SHA-256 为 `a07b5603243ccd48e34f61d317c158a4369804cf9b734577df496e2a9f517b2d`。TELBench 1000 条轨迹均至少有一个 harmful error span，其中 298 条最终答案正确；它能测错误段漏检，不能单独测误报。AgentRx τ-bench 的 73 条 reward=1 运行只作为“无导致最终失败根因”的负例，不作为“全程无异常”标签。
