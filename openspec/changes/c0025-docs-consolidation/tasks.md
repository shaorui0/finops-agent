## 1. 新文档
- [x] 1.1 `docs/NARRATIVE.md`：十二项能力声明，证据链接，边界，诚实的成绩单
- [x] 1.2 `docs/MATURITY.md`：D1 到 D20 的状态、证据、验证命令
- [x] 1.3 `docs/BUILD_PROCESS.md`：闭环、调度规则、波次表、事故与教训

## 2. 更新
- [x] 2.1 `docs/ARCHITECTURE.md`、`docs/REQUIREMENTS.md` §5、`rules/WORKSPACE.md`、`CONTRIBUTING.md`、`docs/METHOD.md`、`docs/DISTILLATION.md`
- [x] 2.2 `README.md`：进度表、三层结果、嵌图、入口链接、设计表
- [x] 2.3 `eval/EXPERIMENTS.md`：对抗一节更新，顶部摘要与目录

## 3. 验收
- [x] 3.1 自写脚本检查链接与标题，输出贴进 evidence
- [x] 3.2 `python3 tools/build_index.py` 重新生成导读页；`python3 -m unittest tools.test_build_index`
- [x] 3.3 `make test`、`make check`（写完 evidence 之后再跑）；`openspec validate c0025-docs-consolidation`
- [x] 3.4 HTML 报告、笔记、README 进度行
