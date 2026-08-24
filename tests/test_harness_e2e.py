# -*- coding: utf-8 -*-
"""
test_harness_e2e.py —— A3-8 / M5 的判绿点：harness **整进程**跑起来，在沙箱里真干活。

和 test_deepseek_mock.py 的分工
--------------------------------
test_deepseek_mock.py 在**进程内**直接构造 代理循环，验证协议层（tools 下发、
tool_call id 配对、参数透传）。它证明不了「examples/harness/主程序.light 这个文件
能不能跑」——那是两件事：例子文件要经 cli/light.py 的编译/依赖内联链路，
要能从环境变量拿配置，要把工具接到真磁盘上。

本文件用 subprocess 起 `python cli/light.py run examples/harness/主程序.light`，
指向进程内的 MockDeepSeek + 一个 pytest tmp_path 沙箱，然后断言**磁盘副作用**：
文件真的存在、内容逐字相等。这条判据挑不出软话说 —— 工具没被调用、参数拼错、
护栏把路径挡了、写进了别的目录，任何一种都会红。

为什么必须断言磁盘而不是只断言 stdout
--------------------------------------
代理循环.执行工具 会把工具抛出的任何异常吞成 "工具执行出错: …" 的 tool 消息喂回
模型（这是刻意的——要让模型自己看到失败）。所以「主程序打出了最终回复」完全
可以在工具从头到尾没成功过的情况下成立。只有断言磁盘状态才能区分这两种情况。
"""

# ⚠️ 工具集来源：主程序.light 收口时已切到 stdlib/代理工具集.light 的 `注册全部(代理, 沙箱根, 选项)`
# （替掉了自带的 write_file/read_file/list_dir 三件套），六个工具一次注册。
# 本文件断言的是**磁盘副作用 + 越界被拦**——工具集换型后按行为重写的部分：
#   工具下发名单   → 现在是 6 个（read/write/edit_file/list_dir/grep/run_command，注册顺序）
#   写嵌套路径     → 代理工具集 的 write_file **不自动建父目录**，需先建目录再写（新增建目录步骤）
import json
import os
import subprocess
import sys

import pytest

_PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_主程序 = os.path.join(_PROJECT, "examples", "harness", "主程序.light")

# 复用 A3-2 的「会读请求体并断言」的 mock（tests 目录无 __init__.py，pytest 会把
# 它插进 sys.path，可直接按模块名导入）。
from test_deepseek_mock import (       # noqa: E402
    MockDeepSeek,
    _body_200,
    _delta,
    _sse,
    _tool_delta,
)


def _写文件响应(路径, 内容, 调用id="call_e2e_01"):
    """第一轮：模型决定调 write_file。arguments 故意切成三片，考验分片累积。"""
    参数 = json.dumps({"path": 路径, "content": 内容})
    切点 = len(参数) // 2
    return _body_200([
        _sse(_tool_delta(name="write_file", tc_id=调用id)),
        _sse(_tool_delta(args=参数[:切点])),
        _sse(_tool_delta(args=参数[切点:])),
        _sse(_delta({}, "tool_calls")),
        b"data: [DONE]\r\n\r\n",
    ])


def _最终回复(文本):
    return _body_200([
        _sse(_delta({"role": "assistant", "content": 文本}, None)),
        _sse(_delta({}, "stop")),
        b"data: [DONE]\r\n\r\n",
    ])


@pytest.fixture
def 起mock():
    servers = []

    def _make(responses):
        s = MockDeepSeek(responses, 需要工具=True)
        s.start()
        servers.append(s)
        return s

    yield _make
    for s in servers:
        try:
            s.srv.close()
        except OSError:
            pass


def _跑主程序(服务器, 沙箱, 任务, 超时=120):
    环境 = dict(os.environ)
    环境.update({
        "DEEPSEEK_BASE_URL": 服务器.base_url,
        "DEEPSEEK_API_KEY": "sk-mock-not-a-real-key",
        "DEEPSEEK_MODEL": "deepseek-chat",
        "HARNESS_SANDBOX": str(沙箱),
        "HARNESS_TASK": 任务,
        # Windows 上子进程默认按 GBK 写 stdout，中文会炸成 UnicodeEncodeError，
        # 而那个异常会伪装成「主程序失败」。两个变量都要给：PYTHONUTF8 管解释器
        # 内部，PYTHONIOENCODING 管标准流。
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    })
    return subprocess.run(
        [sys.executable, os.path.join("cli", "light.py"), "run", _主程序],
        cwd=_PROJECT,
        env=环境,
        capture_output=True,
        timeout=超时,
    )


def _文本(字节串):
    return 字节串.decode("utf-8", errors="replace")


class Test沙箱内真干活:
    def test_主程序在沙箱里建出文件且内容逐字相等(self, 起mock, tmp_path):
        目标名 = "报告.txt"
        正文 = "光明能干活了"
        s = 起mock([_写文件响应(目标名, 正文), _最终回复("我已经把内容写进 报告.txt 了。")])

        结果 = _跑主程序(s, tmp_path, "请在沙箱里新建 报告.txt，内容写：" + 正文)
        标准输出 = _文本(结果.stdout)
        标准错误 = _文本(结果.stderr)

        # 1) 磁盘副作用——这是本用例的核心判据
        产出 = tmp_path / 目标名
        assert 产出.exists(), "沙箱里没有产出文件\nstdout:\n%s\nstderr:\n%s" % (标准输出, 标准错误)
        assert 产出.read_text(encoding="utf-8") == 正文

        # 2) 主流程跑到了尽头（不是中途抛异常后碰巧文件已写）
        assert 结果.returncode == 0, "stderr:\n%s" % 标准错误
        assert "[完成] 我已经把内容写进 报告.txt 了。" in 标准输出

        # 3) 服务端视角：两轮、零协议违规
        assert len(s.payloads) == 2
        assert s.violations == []

        # 4) 六个工具都按注册顺序下发了（代理工具集 的注册顺序 read/edit/write/list/grep/run）
        名字们 = [t["function"]["name"] for t in s.payloads[0]["tools"]]
        assert 名字们 == ["read_file", "write_file", "edit_file", "list_dir", "grep", "run_command"]

        # 5) 系统提示作为首条消息，且带上了沙箱根（模型需要知道自己被关在哪）
        首条 = s.payloads[0]["messages"][0]
        assert 首条["role"] == "system"
        assert "write_file" in 首条["content"]

        # 6) 第二轮里工具结果作为 tool 消息回喂，且是成功文案而不是 "工具执行出错"
        工具消息 = s.payloads[1]["messages"][-1]
        assert 工具消息["role"] == "tool"
        assert 工具消息["name"] == "write_file"
        assert "工具执行出错" not in 工具消息["content"]
        assert "已写入" in 工具消息["content"]

    def test_写嵌套路径且父目录已存在内容逐字相等(self, 起mock, tmp_path):
        # 代理工具集 的 write_file **不自动建父目录**（须先建目录再写），与旧自带
        # 三件套不同。这里先建好父目录，验证写嵌套路径仍落到沙箱内。
        嵌套根 = tmp_path / "产物" / "深"
        嵌套根.mkdir(parents=True)
        s = 起mock([_写文件响应("产物/深/一层.txt", "嵌套也行"), _最终回复("建好了。")])
        结果 = _跑主程序(s, tmp_path, "在 产物/深/ 下建 一层.txt")
        assert 结果.returncode == 0, _文本(结果.stderr)
        产出 = tmp_path / "产物" / "深" / "一层.txt"
        assert 产出.exists(), _文本(结果.stdout)
        assert 产出.read_text(encoding="utf-8") == "嵌套也行"
        assert s.violations == []


class Test护栏真的接上了:
    """反向控制：如果护栏没接进工具，越界写会**成功**，沙箱这个词就是假的。"""

    def test_越界路径被拦下且沙箱外没有留下文件(self, 起mock, tmp_path):
        沙箱 = tmp_path / "沙箱"
        沙箱.mkdir()
        外面 = tmp_path / "逃逸.txt"       # 沙箱的兄弟目录，护栏应当拒绝
        s = 起mock([
            _写文件响应("../逃逸.txt", "我出来了"),
            _最终回复("那个路径不允许，我没有写。"),
        ])

        结果 = _跑主程序(s, 沙箱, "把内容写到 ../逃逸.txt")

        # 1) 沙箱外**没有**文件——护栏真的挡住了
        assert not 外面.exists(), "护栏没挡住越界写，沙箱是假的"
        # 2) 失败没有让主程序崩：转成 tool 消息喂回模型，继续跑完
        assert 结果.returncode == 0, _文本(结果.stderr)
        assert len(s.payloads) == 2
        工具消息 = s.payloads[1]["messages"][-1]
        assert 工具消息["role"] == "tool"
        # 3) 错误原因是「越界」，能被模型和人读懂；不是空串、不是 None
        assert "越界" in 工具消息["content"], 工具消息["content"]

    def test_未注册的工具名不会静默成功(self, 起mock, tmp_path):
        # 模型幻觉出一个不存在的工具时，必须回一条明确的 tool 消息，
        # 而不是当作成功（当作成功会让模型以为事情办了）。
        s = 起mock([
            _body_200([
                _sse(_tool_delta(name="delete_everything", tc_id="call_e2e_hallu")),
                _sse(_tool_delta(args="{}")),
                _sse(_delta({}, "tool_calls")),
                b"data: [DONE]\r\n\r\n",
            ]),
            _最终回复("没有这个工具，我换个办法。"),
        ])
        结果 = _跑主程序(s, tmp_path, "删掉所有东西")
        assert 结果.returncode == 0, _文本(结果.stderr)
        工具消息 = s.payloads[1]["messages"][-1]
        assert "未注册工具" in 工具消息["content"]
        assert "delete_everything" in 工具消息["content"]
