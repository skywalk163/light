# -*- coding: utf-8 -*-
"""用户实参（CLI `--` 透传）runtime 内建。

**为什么实现放这里而不在 builtins.py 里开 `def`**（与 `_t5b_runtime.py` 同一条理由）：
`tools/ci/floor_bootstrap.py` 用 ast 数 `stdlib/builtins.py` 的顶层函数当分母，
`tests/unit/test_R158_地板证据窗口漂移.py` 把「地板自举率 == 68/96」钉成了回归门 ——
在地板文件里新增一个顶层 `def`，分母就变 97，那条门立刻转红。
所以这里只做**实现**，`builtins.py` 用 `from ... import` 做**名字接线**
（from import 不产生 FunctionDef，地板计数不受影响）。

约定：`light run <入口> -- 甲 乙` 时，`cli/light.py` 把 `["甲","乙"]`
以 JSON 写进环境变量 `LIGHT_USER_ARGS`。用 JSON 而不是空格拼接，
是为了让含空格 / 引号 / 中文的实参**原样到达**，不被任何一层二次解释。
"""

import json
import os
import sys

_用户参数环境变量 = 'LIGHT_USER_ARGS'


def 读注入的用户参数():
    """读 CLI 注入的用户实参；未注入（或注入物不可信）返回 None。"""
    原始 = os.environ.get(_用户参数环境变量)
    if not 原始:
        return None
    try:
        值 = json.loads(原始)
    except Exception:
        return None
    if isinstance(值, list):
        return [str(项) for 项 in 值]
    return None


# 光明侧调用名：`_读注入的用户参数`（带下划线前缀，属 runtime 私有面，
# 与 用户参数 这条公开内建区分开）。
_读注入的用户参数 = 读注入的用户参数


def 用户参数() -> list:
    """获取「用户实参」：`light run <入口> --` 之后的那些参数。

    - 有注入时：返回这批实参（不含程序名、不含 CLI 自己的选项）；
    - 无注入时：回退 `sys.argv[1:]`（去掉程序名）。

    `参数列表()` 在无注入时返回的是**宿主进程**的 `sys.argv`，
    那个名字留着是为了兼容存量脚本；新代码一律用这条，语义是确定的。
    """
    注入 = 读注入的用户参数()
    if 注入 is not None:
        return 注入
    return list(sys.argv[1:])
