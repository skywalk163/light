"""原生腿测试的公共口径（第七轮 A7）

本文件只做两件事：**统一 clang 探测口径**、**说明两层原生用例的分工**。

────────────────────────────────────────────────────────────────────
两层原生用例的分工（第七轮 §2.3 消掉的那条假绿）
────────────────────────────────────────────────────────────────────
第一层「IR 正确性」——`tests/test_llvm_net.py` / `test_llvm_async.py` /
`test_llvm_tls.py` / `test_llvm_c3_expr.py` / `test_llvm_exception.py`：
它们调 `compile_source_typed` 拿 IR 文本，再自己发一条裸 `clang -O2` 把 IR
和运行时链成 exe。验的是「codegen 发的 IR 对不对」。这一层**允许保留**，
但它绕过 `compile_light_typed` / `get_optimization_flags`，所以对
「用户敲的那条命令能不能用」零信号。

第二层「产品路径」——`tests/test_native_cli.py`（A7 本轮新增）：
一律走 `compile_light_typed` 或直接子进程跑 `python -m cli.light`，
覆盖优化档位、`run --backend llvm-typed`、退出码透传、临时目录清理。

「测试全绿而 CLI 默认档全废」能共存六轮，就是因为只有第一层存在。
两层都要有：第一层挡 codegen 回归，第二层挡交付路径回归。

────────────────────────────────────────────────────────────────────
clang 探测口径
────────────────────────────────────────────────────────────────────
- 默认复用生产链路的 `src/llvm/compiler.py: find_clang()`（Windows 走
  `C:\\Program Files\\LLVM\\bin` 等固定位置 + PATH；POSIX 走 PATH 与
  `/usr/bin`、`/usr/local/bin`），**不再另写一份候选表** —— 两份表迟早分叉。
- 环境变量 `LIGHT_CLANG` 可覆盖，但**判定逻辑也在 `find_clang()` 里**，本文件
  不重复实现：指到一个不存在的路径时 `find_clang()` 抛 RuntimeError，等价于
  「本机没有 clang」，用来验证「缺 clang 时是 skip 而不是 error」。
  为什么不能用「把 clang 从 PATH 里摘掉」来模拟：候选表里那些绝对路径排在
  PATH 探测之前，摘 PATH 之后照样找得到（外部 POSIX 验证那轮实测：31 passed
  而不是 skip）。
- 缺 clang 一律 **skip**，不许 error：`find_clang()` 在缺失时直接 raise，
  谁在模块顶层调它，整个文件就是 collect error（跨平台闸门专拦这种「整批
  没跑起来」）。
"""
import os
import sys

import pytest

仓库根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(仓库根, 'src') not in sys.path:
    sys.path.insert(0, os.path.join(仓库根, 'src'))


def 探测clang():
    """返回 clang 路径，找不到返回 None（**不抛异常**）"""
    try:
        from llvm.compiler import find_clang  # type: ignore[import]
    except ImportError:
        return None
    try:
        return find_clang()
    except RuntimeError:
        return None


CLANG_PATH = 探测clang()
HAS_CLANG = CLANG_PATH is not None

skip_without_clang = pytest.mark.skipif(
    not HAS_CLANG,
    reason=(
        "缺 clang：原生腿的产品路径（compile_light_typed / "
        "light run --backend llvm-typed）全部未验证 —— 优化档位、"
        "退出码透传、产物清理都没被看过"
    ),
)
