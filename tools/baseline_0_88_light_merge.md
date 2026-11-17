# 0.88（FreeBSD 15.1）全量基线 —— light-merge

抓取时间：2026-11-17 09:10–09:39
现场：`192.168.0.88:/tmp/lp-ci/run-20261117-091021-baseline-r222`
命令：`python tools/remote_ci.py --repo light-merge --tag baseline-r222`（2 槽 × `-n 6`）

结果：**18 failed / 9981 passed / 146 skipped / 10 xfailed in 1737.24s（28m57s）**，rc=1。

> **判据**：M 线与各线的「新增红 = 0」是相对**这份 18 条列表**，不是「0 failed」。
> 0.88 与 Windows 本机/082 门的环境不同（缺编译链、缺 cryptography、路径与本地化差异），
> 这 18 条是**0.88 上的已知红**，改动前后都要比这份名单。

## 已知红（18 条，按 pytest 输出原样）

1. `tests/test_pure_light_hook.py::test_magic_number_in_first_two_lines`
2. `tests/unit/test_native_leg_capability.py::test_运行时符号清单与代码一致`
3. `tests/unit/test_R16x_L217_所有权收敛.py::test_P1字面量循环_修后零增长_反跑复原`
4. `tests/unit/test_R140_L182_L191_原生腿.py::test_L182_形态甲_同名直返双腿一致`
5. `tests/test_frontend_blockers_run.py::test_a25_内层类继承顶层基类`
6. `tests/test_native_cli.py::Test原生类与方法代码生成::test_方法内调方法`
7. `tests/unit/test_doc_examples_gate.py::TestDocExamplesGate::test_不许新增ROT`
8. `tests/lightpub/test_R155_Socket顶层路由.py::R155_Socket顶层路由_根因锚点::test_顶层与lightpub导出面一致`
9. `tests/test_iterator_protocol.py::test_custom_iterator_for_loop`
10. `tests/unit/test_R159_E3_容器布尔repr.py::test_双腿对拍_容器内布尔repr收敛`
11. `tests/e2e/test_e2e_chain.py::test_duan_compile_and_run_product[E阶段_L3L4原生语法/E3_L3_公式数学原生.light]`
12. `tests/unit/test_runtime_residual_O0.py::test_转文本_字典序列化`
13. `tests/test_context_manager.py::TestJueyiOOP成员赋值目标::test_自之属性带索引赋值`
14. `tests/e2e/test_e2e_chain.py::test_duan_compile_and_run_product[E阶段_L3L4原生语法/E4_L4_沙箱隔离验证.light]`
15. `tests/test_lpd_002_import_hint.py::TestLpd002ImportHint::test_dict_keys_import`
16. `tests/e2e/test_e2e_chain.py::test_duan_compile_and_run_product[L4_python/all_in_one_demo.light]`
17. `tests/unit/test_R162_TLS降级守卫.py::test_缺cryptography时_恰好一条响亮降级红`
18. `tests/e2e/test_L4_compiled_e2e.py::TestL4_MultiLang_E2E::test_mixed_python_go_blocks`

## 耗时特征（排队时用来估时）

- 全仓 **10,155** 项，收集阶段本身约 72–89 s。
- 单条最慢 55–60 s：`tests/e2e/*`（真编译 + 真跑）、`test_native_cli.py`、`test_doc_examples_gate.py`。
- 28m57s / 全量，单槽 `-n 6`；两条线同时跑请按 1.3 倍估。
- 想快：先 `-k <自己线的名字>` 收敛到几十项，合流前再跑全量。
