# T-0200 工作总结（LH-20：管道式交互子进程）

新增 stdlib/进程.py 的管道式交互子进程能力（不改既有 API）：进程会话 类
（写一行 / 读一行(超时=) / 是否存活 / 终止 / 进程PID / 返回码）——
stdin=PIPE、stdout=PIPE、bufsize=1（text 行缓冲），stderr 默认并入 DEVNULL（防
接 PIPE 不读把子进程写死）；读端用后台线程+队列实现可靠超时，读一行 超时返回
None（空）不抛、不吞空行、只剥行终结符。进程会话启动(命令, 工作目录=, 环境变量=)
为工厂。stdlib/进程.light 声明 导出 进程会话启动，并注释标注「管道交互是原生
Python 腿能力，纯光明腿做不了；.light 无纯光明实现魔数，hook 让位 .py 真身回退」。

改的文件：stdlib/进程.py（新增类/工厂 + __all__ 增补）、stdlib/进程.light（导出
+能力边界注释）、tests/unit/test_LH20_管道交互.py（新增 5 条用例：请求-响应循环 /
超时返回空 / stderr 大流量 / 终止后退出无僵尸 / MCP initialize 握手拿 serverInfo）。

验证：本会话无法运行任何 bash——宿主机无可用 sandbox 后端（workspace-write 无后端，
danger-full-access 无审批通道），主 agent 与 subagent 均确认 bash 完全阻塞，故
python3 -m pytest 无法在会话内执行。已做静态走查：三文件逐行复核，5 个子进程脚本
均合法 Python，test_05 响应字典括号平衡，__all__ 与 .light 导出一致；导入自洽性
检查确认 进程.light 无魔数保持 stub 形态、进程.py 无顶层副作用裸 import 必成功。

遗留风险：未在本会话实测（bash 阻塞），若测试在可执行环境暴露运行时问题（平台
缓冲/时序）需补跑定位；代码已按 LH-20 要点设计，Windows bufsize=1 差异已在注释
标注并降级为自实现行切分。验收命令（worker 必须跑，须全绿）：
python3 -m pytest -q tests/unit/test_LH20_管道交互.py
