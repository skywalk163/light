# -*- coding: utf-8 -*-
"""test_R145_R119B_嵌套对象字段写回.py —— R145-B（L-202 修复）。

被测缺陷（R145-B 定位与修复，符号级）：
  L-202 原生腿「实例字段写回嵌套对象被 `strchr` 提前截断」。
  `dv_class_get_member` / `dv_class_set_member` 用 `strchr(found,'\x1F')` 定位值尾，
  但嵌套对象被序列化为 `S<len>:obj:__class__\x1F<字段>\x1F<值>...`（含内部 `\x1F`），
  `strchr` 会停在嵌套对象内部第一个 `\x1F`，读回对象被截断为 `"S<len>:obj:__class__"`，
  字段全丢 → 属性访问恒返回空。
  修复：`src/llvm/runtime_typed.c` 新增静态 helper `dv_typed_value_end`，
  按自描述语法精确扫描值尾；`dv_class_get_member` / `dv_class_set_member` 由
  `strchr(...)` 改为 `dv_typed_value_end(...)`。

判实方式（全部真编译 + 真运行 + 两腿对拍，仿 test_R142_L196_异步方法形参与协程.py）：
  原生腿输出 == Python 腿输出 == 显式期望值，三者缺一不可。

覆盖（全部用本地纯对象，不依赖网络/主控；嵌套对象覆盖类实例字段 + await 返回值，
  对齐 `reg_core.light` 的 `注册()` 场景）：
  A1  嵌套对象读回：`外.内.取名称()` 应为 "你好"（修前 native 恒 "空"）。
  A2  嵌套对象字段逐层读回：`外.内.值`、`外.内.标签`。
  A3  实例字段写回嵌套对象：`设 己.回 为 新建 应答(...)` 后读回 `.错误`。
  A4  await 返回值是嵌套对象：协程内 `等待 某方法()` 返回 `新建 应答(...)`，
      读 `.错误.码` == -1（R119-B 注册链路 `注册()` 的纯本地等价最小复现——
      `节点核心.light` L56-58 的 `回["错误"] != 空` 依赖 `回` 不被截断）。

反跑（证明断言有牙，已在 0.82 实测，不写进自动化用例——它需要改 src/，属 CI 不该做的事）：
  把 `src/llvm/runtime_typed.c` 的 `dv_typed_value_end` 调用改回 `strchr(found,'\x1F')`
  旧行为 → A1/A2/A3/A4 立即由绿转红（读回恒空）；恢复修复 → 全绿。

平台：本机 Windows 不实跑（项目铁律），全部在 192.168.0.82（FreeBSD 15.1）执行。
"""
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _native_helpers import 仓库根, skip_without_clang  # type: ignore[import]

_SRC = os.path.join(仓库根, 'src')
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

子进程口径 = dict(capture_output=True, text=True, encoding='utf-8', errors='replace')


def 写文件(目录, 文件名, 内容):
    """无 BOM 写 .light（BOM 会被词法层当字符卡住）"""
    路径 = os.path.join(目录, 文件名)
    with open(路径, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(内容)
    return 路径


def 原生腿跑(主文件, 目录):
    from llvm.compiler import compile_light_typed  # type: ignore[import]
    exe = compile_light_typed(主文件, os.path.join(目录, '产物'), optimize_level=2)
    结果 = subprocess.run([exe], timeout=120, cwd=目录, **子进程口径)
    return 结果.returncode, [行.strip() for 行 in 结果.stdout.splitlines() if 行.strip()]


def python腿跑(主文件, 目录):
    结果 = subprocess.run(
        [sys.executable, os.path.join(仓库根, 'cli', 'light.py'), 'run', 主文件],
        cwd=目录, timeout=180, **子进程口径)
    return 结果.returncode, [行.strip() for 行 in 结果.stdout.splitlines() if 行.strip()]


def 双腿跑(tmp_path, 名, 源):
    """返回 (原生腿输出, Python腿输出)。两腿都真编译/真运行。"""
    目录 = str(tmp_path / 名)
    os.makedirs(目录, exist_ok=True)
    主文件 = 写文件(目录, 名 + '.light', 源)
    原_rc, 原_出 = 原生腿跑(主文件, 目录)
    py_rc, py_出 = python腿跑(主文件, 目录)
    assert 原_rc == 0, '原生腿 rc=%s' % 原_出
    assert py_rc == 0, 'Python 腿 rc=%s' % py_出
    return 原_出, py_出


# A1：嵌套对象读回（最小复现）—— 修前 native 恒 "空"，修后 "你好"
A1 = """类 内:
  段落 初始化(自, 名):
    设 己.名称 为 名
  段落 取名称(自):
    返回 己.名称

类 外:
  段落 初始化(自):
    设 己.内 为 新建 内("你好")

段落 主():
  设 对 为 新建 外()
  输出("名称=" 加上 转字符串(对.内.取名称()))
"""

# A2：嵌套对象字段逐层读回 —— 修前字段全丢（读回只剩类名）
A2 = """类 内:
  段落 初始化(自):
    设 己.值 为 42
    设 己.标签 为 "ok"

段落 主():
  设 对 为 新建 内()
  输出("值=" 加上 转字符串(对.值) 加上 " 标签=" 加上 转字符串(对.标签))
"""

# A3：实例字段写回嵌套对象 —— 修前 `己.回` 读回只剩类名
A3 = """类 应答:
  段落 初始化(自, 码, 消息):
    设 己.码 为 码
    设 己.消息 为 消息

类 持有:
  段落 初始化(自):
    设 己.回 为 空

段落 主():
  设 对 为 新建 持有()
  设 对.回 为 新建 应答(-1, "连接失败")
  输出("码=" 加上 转字符串(对.回.码) 加上 " 消息=" 加上 转字符串(对.回.消息))
"""

# A4：await 返回值是嵌套对象（R119-B 注册链路 `注册()` 的纯本地等价最小复现）——
#     修前 `回` 被截断只剩类名 → `回.错误` 恒空 → 恒走成功分支
A4 = """类 应答:
  段落 初始化(自, 码, 消息):
    设 己.码 为 码
    设 己.消息 为 消息
  段落 有错误(自):
    返回 己.码 != 0

类 客户端:
  异步 段落 请求(自, 名):
    返回 新建 应答(-1, "连接失败")

类 主控:
  段落 初始化(自):
    设 己.客户端 为 新建 客户端()
    设 己.错误码 为 0
  异步 段落 注册(自):
    设 回 为 等待 己.客户端.请求("注册")
    设 己.错误码 为 回.码
    设 己.有错误 为 回.有错误()

段落 主():
  设 对 为 新建 主控()
  异步 运行 对.注册()
  输出("错误码=" 加上 转字符串(对.错误码) 加上 " 有错误=" 加上 转字符串(对.有错误))
"""


@skip_without_clang
def test_A1_嵌套对象读回_取名称(tmp_path):
    """L-202 根因：嵌套对象读回不再被 `strchr` 截断。

    修前 native 输出 `名称=空`；修后 `名称=你好`。src 腿全程 `你好`。
    """
    原, py = 双腿跑(tmp_path, 'A1', A1)
    assert 原 == ['名称=你好'], '原生腿=%s' % 原
    assert py == ['名称=你好'], 'Python 腿=%s' % py
    assert 原 == py


@skip_without_clang
def test_A2_嵌套对象字段逐层读回(tmp_path):
    """嵌套对象多个字段（值 + 字符串标签）读回一致。"""
    原, py = 双腿跑(tmp_path, 'A2', A2)
    assert 原 == ['值=42 标签=ok'], '原生腿=%s' % 原
    assert py == ['值=42 标签=ok'], 'Python 腿=%s' % py
    assert 原 == py


@skip_without_clang
def test_A3_实例字段写回嵌套对象(tmp_path):
    """`设 己.回 为 新建 应答(...)` 后读回 `.码` / `.消息` 完整。

    修前 `己.回` 被 `strchr` 截断为 `S<len>:obj:应答` → 字段全丢 → 恒空。
    """
    原, py = 双腿跑(tmp_path, 'A3', A3)
    assert 原 == ['码=-1 消息=连接失败'], '原生腿=%s' % 原
    assert py == ['码=-1 消息=连接失败'], 'Python 腿=%s' % py
    assert 原 == py


@skip_without_clang
def test_A4_await返回值嵌套对象_错误码(tmp_path):
    """R119-B 注册链路 `注册()` 的纯本地等价最小复现。

    修前 `回` 被 `strchr` 截断 → `回.码` 恒空 → `回.有错误()` 恒假 →
    恒走成功分支（即 `reg_core.light` 的「意外：走了成功分支」原症状）。
    修后 `错误码=-1 有错误=真`。
    """
    原, py = 双腿跑(tmp_path, 'A4', A4)
    assert 原 == ['错误码=-1 有错误=真'], '原生腿=%s' % 原
    assert py == ['错误码=-1 有错误=真'], 'Python 腿=%s' % py
    assert 原 == py