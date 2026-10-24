# 0026 code-wrapup

- 全局变量传参是债：c0023 为了不改签名在模块里偷存快照，改成显式参数后行为逐字节不变，用 findings.json / slo.json 的 diff 证明。
- `make test` 手写模块清单会漏：漏了 7 个模块没人发现。改成按目录 discover，新测试自动进。
- 文档检查要有 file:line，并且跳过代码围栏，否则 shell 注释会被当成标题。
- 反引号路径的判定要收紧（已知顶层目录或已知扩展名），否则 `owner/repo`、docker 镜像名全是误报。
- 新检查先挂 flag：main 上已有 6 处失败，等文档改写合并再打开，避免 CI 先红。
- 默认端口写进代码而不是靠环境变量，「clean checkout 能跑」才成立。

PROGRESS_ROW: | c0026-code-wrapup | 10-24 | 收尾代码尾巴（显式快照、未再检出入报告、make test 覆盖全部、heldout 默认端口）+ 文档检查 D11/D16（--docs 开关） | 全局暂存和手写测试清单都是静默债；新检查先挂 flag 再切换 | [报告](reports/0026-code-wrapup.html) · [笔记](notes/blog/0026-code-wrapup.md) |
