# -*- coding: utf-8 -*-
"""
test_harness_agent_light.py —— C7 M18（收口）：评测链接上带工具的 agent 链。

判据对三件事，全部真跑整进程（examples/harness/评测驱动.light 经 cli.light_unified
编译/依赖内联链路，HARNESS_MODE=agent）：
  1. 功能（M18 判据 1）：评测集 评测集_agent.jsonl 里 2 条「查首都」**必须**靠工具
     调用才能答对（mock 通道发出 finish_reason == tool_calls → 代理循环 执行工具 →
     下轮读取 tool 结果当最终答）。断言这 2 条 得分=1 且 工具调用次数>=1、轮数>=2。
  2. 韧性（M18 判据 2）：TimeoutError / HTTP 401 / OSError / 工具抛异常 各注入一条，
     整场必须跑完、报告必须落盘、失败条目各带六类错误分类（超时/HTTP状态/连接/工具）。
  3. 反跑（M18 判据 3）：本文件韧性用例本身就是反跑证明——只要 评测驱动.light 里
     评测一条_agent 的单条兜底 `捕获` 被摘掉，Timeout/401/OSError 会冒泡到
     asyncio.gather（无 return_exceptions）→ 整场崩溃、报告不落盘、rc=1 → 本用例立红。
     反跑的实测变异输出贴在交付报告 §3。
  4. 并发时序（agent 模式）：并发 2 的整场总耗时 < 串行 1（延迟注入响应体中段）。

零发网：全程 HARNESS_CHANNEL=mock，报告一律写进 tmp_path。
"""
import json
import os
import subprocess
import sys

import pytest

_PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_评测驱动 = os.path.join(_PROJECT, "examples", "harness", "评测驱动.light")


def _跑评测(报告目录, 并发=2, 延迟="0.05", 速率="100", 报告名="评测报告", 超时=240):
    环境 = {
        **os.environ,
        "HARNESS_MODE": "agent",
        "HARNESS_TOOLS": "on",
        "HARNESS_CHANNEL": "mock",
        "HARNESS_REPORT": os.path.join(str(报告目录), 报告名),
        "HARNESS_CONCURRENCY": str(并发),
        "HARNESS_DELAY_SEC": 延迟,
        "HARNESS_RATE": 速率,
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    结果 = subprocess.run(
        [sys.executable, "-m", "cli.light_unified", "run", _评测驱动],
        cwd=_PROJECT,
        env=环境,
        capture_output=True,
        timeout=超时,
    )
    return 结果.returncode, os.path.join(str(报告目录), 报告名 + ".json"), 结果.stdout, 结果.stderr


def _文本(字节串):
    return 字节串.decode("utf-8", errors="replace")


def _读报告(报告路径):
    with open(报告路径, encoding="utf-8") as f:
        return json.load(f)


class TestM18功能:
    """评测驱动带工具多轮 agent 端到端跑完整场，2 条须工具条目答对且带真实指标。"""

    def test_agent模式工具题端到端(self, tmp_path):
        rc, 报告路径, 输出, 错误 = _跑评测(tmp_path)
        assert rc == 0, "agent 模式整进程失败，stdout:\n%s\nstderr:\n%s" % (
            _文本(输出),
            _文本(错误),
        )
        assert os.path.exists(报告路径), "报告 JSON 未落盘"

        报告 = _读报告(报告路径)
        汇总 = 报告["汇总"]

        # 全 6 条都处理完（2 工具题 + 4 故障注入）
        assert 汇总["总条数"] == 6
        assert 汇总["通过数"] == 2
        assert 汇总["未通过数"] == 4

        # 2 条须工具的「查首都」条目：必须靠工具才能答对，得分 1 且有真实轮数/工具次数
        工具题 = [e for e in 报告["条目"] if e["prompt"].endswith("首都是哪个城市")]
        assert len(工具题) == 2
        for e in 工具题:
            assert e["得分"] == 1, "须工具条目未答对: %s -> %r" % (e["prompt"], e["输出"])
            assert e["工具调用次数"] >= 1, "须工具条目必须有工具调用: %s" % e["prompt"]
            assert e["完成轮数"] >= 2, "须工具条目必须多轮(工具+收尾): %s" % e["prompt"]

        # 元信息带 模式/工具 两个新字段
        元 = 报告["元信息"]
        assert 元["模式"] == "agent"
        assert 元["工具"] == "on"

    def test_多轮的用量按轮累加且失败条目留空(self, tmp_path):
        """第八轮：agent 链的用量透传（#11 的兑现判据）。

        mock 的词元是字符数替身：一条工具题跑 2 轮，两轮都把同一个 prompt 发上去，
        所以 输入词元 == 2 * len(prompt)（这正好证明「逐轮累加」而不是「只留最后一轮」）；
        输出词元 == len(最终回复)（第 1 轮只发 tool_calls、正文为空）。
        故障条目没跑完 → 输入/输出词元 必须是 None，**不许是 0**。
        """
        rc, 报告路径, 输出, 错误 = _跑评测(tmp_path)
        assert rc == 0, "%s\n%s" % (_文本(输出), _文本(错误))
        报告 = _读报告(报告路径)
        by_prompt = {e["prompt"]: e for e in 报告["条目"]}

        for prompt in ["中国的首都是哪个城市", "法国的首都是哪个城市"]:
            e = by_prompt[prompt]
            assert e["完成轮数"] == 2, e
            assert e["输入词元"] == 2 * len(prompt), e
            assert e["输出词元"] == len(e["输出"]), e

        for prompt in ["注入超时", "注入HTTP401", "注入OSError"]:
            e = by_prompt[prompt]
            assert e["输入词元"] is None, e
            assert e["输出词元"] is None, e

        # 汇总只累计采到的那几条
        采到的 = [e for e in 报告["条目"] if e["输入词元"] is not None]
        assert 报告["汇总"]["用量"]["总输入词元"] == sum(e["输入词元"] for e in 采到的)
        assert 报告["汇总"]["用量"]["总输出词元"] == sum(e["输出词元"] for e in 采到的)


class TestM18韧性:
    """四类故障各一条，整场跑完、报告落盘、四条各带正确错误分类。"""

    def test_四类故障注入整场跑完报告落盘且分类正确(self, tmp_path):
        rc, 报告路径, 输出, 错误 = _跑评测(tmp_path)
        assert rc == 0, "有失败条目但整场应成功退出(rc=0)，stdout:\n%s\nstderr:\n%s" % (
            _文本(输出),
            _文本(错误),
        )
        assert os.path.exists(报告路径), "报告 JSON 必须落盘"

        报告 = _读报告(报告路径)
        by_prompt = {e["prompt"]: e for e in 报告["条目"]}

        # 四条故障注入各带正确分类（六类值域，缺一即红）
        assert by_prompt["注入超时"]["错误分类"] == "超时"
        assert by_prompt["注入HTTP401"]["错误分类"] == "HTTP状态"
        assert by_prompt["注入OSError"]["错误分类"] == "连接"
        assert by_prompt["查询故障的东西"]["错误分类"] == "工具"

        # 失败条目不是被擦成常量的空分类，且带可读错误消息
        for prompt in ["注入超时", "注入HTTP401", "注入OSError", "查询故障的东西"]:
            e = by_prompt[prompt]
            assert e["错误消息"] != "", "失败条目必须带原始错误消息: %s" % prompt

        # 失败分类计数与各分类对应
        计 = 报告["汇总"]["失败分类计数"]
        assert 计["超时"] == 1
        assert 计["HTTP状态"] == 1
        assert 计["连接"] == 1
        assert 计["工具"] == 1
        assert 计["未分类"] == 0
        assert 计["解析"] == 0

        # 元信息锚点也到位（agent 模式控制台断言在 e2e 里已覆盖，这里只查报告字段）
        assert 报告["元信息"]["模式"] == "agent"


class TestM18时序:
    """agent 模式并发比串行快：同评测集并发 2 整场耗时 < 串行 1。"""

    def test_agent并发比串行快(self, tmp_path):
        def 单次(并发, 名字):
            rc, 报告路径, 输出, 错误 = _跑评测(tmp_path, 并发=并发, 延迟="0.3", 报告名=名字)
            assert rc == 0, "并发=%s 失败: %s" % (并发, _文本(输出))
            return _读报告(报告路径)["元信息"]["总耗时"]

        串行 = 单次(1, "串行")
        并发 = 单次(2, "并发")
        assert 并发 < 串行, "agent 并发时序未提速（延迟注入应置于响应体中段），并发=%s 串行=%s" % (
            并发,
            串行,
        )