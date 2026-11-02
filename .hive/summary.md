## T-0235 工作总结

- 新增 `scripts/smoke.sh`（POSIX sh，无 grep/head/awk 依赖），一条命令回答「装好了没有」。
- 判据：`light --version` 必须含 `v0.4.`；临时生成 `打印("你好，世界！")` 的 hello.light，`light run` 退出码须为 0 且 stdout 逐字等于「你好，世界！」；两条都过才退出 0。
- 成功输出三行（供站点「成功时你会看到什么」逐字对齐）：
  ```
  光明编译器 v0.4.0
  你好，世界！
  ✅ 装好了
  ```
- 验证：`sh -n` 语法通过；`test -x scripts/smoke.sh` 通过（git-bash）；用临时垫片模拟已安装的 `light`（转发到 `python -m cli.light`）跑通成功路径；无 `light` 时打印安装提示并退出 1。
- 本机实测：`python -m cli.light --version` → `光明编译器 v0.4.0`；`run examples/hello.light` → rc=0，首行为「你好，世界！」。
- 文件状态：git 索引 mode 100755、blob LF；commit `23eb3a0`（分支 task/T-0235）。
- 风险/限制：quye.com/start.html 文案更新不在本卡 paths（仅 scripts/smoke.sh），未改站点；Windows cmd.exe 不能直接执行 .sh / `test -x`（已用 git-bash 验证，POSIX 目标无碍）；0.88 上未找到已安装的 `light`，真实 pip 安装链路未端到端实测；脚本对 stdout 严格逐字匹配，CLI 若新增 banner 会转为失败（有意为之）。
