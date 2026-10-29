# -*- coding: utf-8 -*-
"""LH-17 + LH-06 + LH-19 回归护栏：外部命令三处病灶一次性收口。

## 病灶（均为 lighthive 一手实测 / 源码确认）

- **LH-17（P0）**：`后台执行` 默认把 stdout/stderr 接成 PIPE 且**无人消费**。
  常驻进程写满 Linux 64KB 管道缓冲后阻塞在 write()；`poll()` 仍是 None（"活着"），
  但再也不干活，**零报错**——静默卡死。
- **LH-06（P1）**：`执行命令` 签名无 `标准输入`，无法把内存内容喂给命令
  （`git hash-object -w --stdin` / `gpg --verify` / 管道喂数据 全断）。
- **LH-19（P2）**：`工作目录=""` 是陷阱——`chdir("")` 抛 FileNotFoundError 被
  except 兜住，误报「命令未找到」。

## 修复口径

- `后台执行` 默认 stdout/stderr → `DEVNULL`（不读不堵）；仅显式 `捕获输出=真`
  才接 PIPE（调用方负责消费，文档写明）。`等待进程` 对 DEVNULL 返回空输出而非崩。
- `执行命令(..., 标准输入=空)` 透传 `subprocess.run(input=…)`；不传行为不变。
- `工作目录=""` 一律归一成 `None`（"不指定"，与 `空` 同义），`外部命令` 与
  `进程.进程启动` 同步归一。

## 覆盖

1. **不堵**：`后台执行` 起一个写 ≥1MB stdout 后 touch 标记的子进程，10 秒内标记出现；
2. **不死**：子进程写满输出后 `wait`/`poll` 仍返回最终码（不因管道卡死而永久 None）；
3. **兼容**：`等待进程` 未开捕获输出时不崩（返空输出）；开捕获输出时拿到 stdout；
4. **stdin**：`执行命令(["cat"], 真, 空, 空, 空, "utf-8", 标准输入="甲乙")` stdout 含「甲乙」；
5. **空串工作目录**：`执行命令(["pwd"], 真, "")` 返回码 0 且与传 `空` 等价；
6. **附带**：`后台执行(..., 工作目录="")` 与 `进程启动(..., 工作目录="")` 一并归一。
"""
import os
import tempfile
import time
import uuid

import pytest

# 光明风格字面量别名（与任务书符号一致，便于直接对照）
真 = True
空 = None

# 写 ≥1MB 到 stdout：30000 行 × 41 字节 ≈ 1.23MB，远超 Linux 64KB 管道缓冲。
_大量输出 = (
    "for i in $(seq 1 30000); do "
    "echo 0123456789012345678901234567890123456789; done"
)

_POSIX = os.name != "nt"


def _唯一标记路径() -> str:
    return os.path.join(
        tempfile.gettempdir(), "light_lh17_%s.flag" % uuid.uuid4().hex
    )


@pytest.mark.skipif(not _POSIX, reason="sh/echo 为 POSIX 探针")
class TestLH17后台执行管道:
    """LH-17：后台执行默认不接 PIPE，写满输出不卡死。"""

    def test_不堵_大量输出后标记出现(self):
        from 外部命令 import 后台执行
        标记 = _唯一标记路径()
        try:
            脚本 = _大量输出 + "; touch " + 标记
            句柄 = 后台执行(["sh", "-c", 脚本])
            截止 = time.time() + 10
            while time.time() < 截止 and not os.path.exists(标记):
                time.sleep(0.05)
            assert os.path.exists(标记), "10 秒内标记文件未出现 → 管道卡死"
            句柄.wait(timeout=5)  # 回收，不留孤儿
        finally:
            if os.path.exists(标记):
                os.unlink(标记)

    def test_不死_写满后poll返回最终码(self):
        from 外部命令 import 后台执行
        句柄 = 后台执行(["sh", "-c", _大量输出])
        # 旧实现（默认 PIPE 无人读）会在这里超时挂死；DEVNULL 下应立即完成。
        assert 句柄.wait(timeout=10) == 0, "子进程写满输出后应正常退出"
        assert 句柄.poll() == 0, "poll() 应返回最终返回码，不因管道卡死而永久 None"

    def test_兼容_未开捕获输出时等待进程不崩(self):
        from 外部命令 import 后台执行, 等待进程
        句柄 = 后台执行(["sh", "-c", "echo hello"])
        结果 = 等待进程(句柄, 超时=10)
        assert 结果.返回码 == 0
        assert 结果.标准输出 == "", "未开捕获输出时输出应恒为空（DEVNULL）"
        assert 结果.标准错误 == ""

    def test_兼容_开捕获输出时拿到stdout(self):
        from 外部命令 import 后台执行, 等待进程
        句柄 = 后台执行(["echo", "hello"], 捕获输出=真)
        结果 = 等待进程(句柄, 超时=10)
        assert 结果.返回码 == 0
        assert "hello" in 结果.标准输出

    def test_后台执行_空串工作目录归一(self):
        from 外部命令 import 后台执行
        句柄 = 后台执行(["pwd"], 工作目录="")
        assert 句柄.wait(timeout=10) == 0, "空串工作目录应视为不指定（返回码 0）"


@pytest.mark.skipif(not _POSIX, reason="cat/pwd 为 POSIX 探针")
class TestLH06LH19执行命令:
    """LH-06（标准输入）与 LH-19（空串工作目录）回归护栏。"""

    def test_stdin_标准输入透传给cat(self):
        from 外部命令 import 执行命令
        结果 = 执行命令(["cat"], 真, 空, 空, 空, "utf-8", 标准输入="甲乙")
        assert 结果.返回码 == 0
        assert "甲乙" in 结果.标准输出

    def test_stdin_缺省不传行为不变(self):
        from 外部命令 import 执行命令
        结果 = 执行命令(["echo", "x"], 真, 空, 空, 空, "utf-8")
        assert 结果.返回码 == 0
        assert "x" in 结果.标准输出

    def test_空串工作目录_返回0且与空等价(self):
        from 外部命令 import 执行命令
        结果 = 执行命令(["pwd"], 真, "")
        基线 = 执行命令(["pwd"], 真, 空)
        assert 结果.返回码 == 0, (
            f"空串工作目录应返回码 0，实际 {结果.返回码}：{结果.标准错误}"
        )
        assert 结果.标准输出 == 基线.标准输出, (
            "空串工作目录应与 空（不指定）等价"
        )
        assert 结果.标准输出.strip() != "", "输出应非空（即当前目录）"


@pytest.mark.skipif(not _POSIX, reason="pwd 为 POSIX 探针")
class TestLH19进程启动:
    """LH-19 在 stdlib/进程.py 的 进程启动 同样归一（任务书授权一并改）。"""

    def test_进程启动_空串工作目录归一(self):
        from 进程 import 进程启动
        句柄 = 进程启动(["pwd"], 等待=真, 超时=10, 工作目录="")
        assert 句柄.poll() == 0, "空串工作目录应视为不指定（返回码 0）"
