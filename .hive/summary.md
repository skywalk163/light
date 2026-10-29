# T-0202 光明P2：socket 常量整组透出 [LH-15]

## 做了什么
- `stdlib/socket.light`（原生腿门面）：导出行补 `SO_REUSEPORT / SO_KEEPALIVE /
  SO_BROADCAST / TCP_NODELAY / IPPROTO_IP / IPPROTO_TCP / IPPROTO_UDP`，并补对应
  零参取值段（POSIX/Linux 规范字面量）。旧 6 个常量与文件头历史注释「只加不删」。
- `stdlib/Socket.py`（Python 腿顶层路由）：`import socket as _py_socket` 后整组透出
  常量；`SO_REUSEPORT = getattr(_py_socket,'SO_REUSEPORT',None)` 平台不存在时返回
  空(None)，绝不静默返回 0。常量加入 `__all__`。
- 命名澄清：文件内注释写明光明里模块就叫 `socket`（原生腿）/`Socket`（Python 腿），
  没有 `套接字` 模块。

## 验证
- `python -m pytest -q tests/unit/test_LH15_socket常量.py` → **4 passed, 1 skipped**
  （skip = 本机 Windows 无 SO_REUSEPORT，双绑真用按卡面要求 skip 并打印原因）。
- 邻接回归 `tests/unit/test_R147_R131_漏登.py` → 5 passed（未破坏既有 socket 门面断言）。
- socket.light 经 PythonCodeGenerator 编译通过，新段均落成 `def X():`。

## 取值口径（诚实声明）
- Python 腿（验收对拍真用）：直接对齐宿主 `socket` 模块，不写死数字；本台 Windows
  实测 SO_REUSEADDR=4、TCP_NODELAY=1、IPPROTO_TCP=6、SO_REUSEPORT 缺失→None。
- 原生腿：C 运行时暂无「取 socket 选项常量」绑定（setsockopt 本身未接线），零参段
  给 POSIX 规范字面量仅作导出可达/导入不炸的门面语义；跨平台真值以 Python 腿为准。

## 没做 / 风险
- 未动 `src/code_generator.py`、`stdlib/外部命令.py`（卡面禁区）。
- SO_REUSEPORT 双绑真用仅在 POSIX（Linux/FreeBSD）机器上真跑；本机 Windows skip。
- setsockopt 本身仍是缺口（不在本卡范围）。
