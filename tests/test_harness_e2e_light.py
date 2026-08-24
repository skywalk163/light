# -*- coding: utf-8 -*-
"""
test_harness_e2e_light.py —— M14 的判绿点：examples/harness/评测驱动.light **整进程**
端到端跑起来（读 JSONL → 并发评测 → 打分 → 出报告），并断言报告数字与手算逐项一致。

为什么是「整进程」而不是进程内调用
----------------------------------
评测驱动.light 是 D5 的最终交付物，判据必须是「这个文件能不能跑」：要经
cli.light_unified 的编译/依赖内联链路（LLM通道/编排/打分/行流 四个支撑模块
是本地依赖，运行时经 _register_user_modules 编译注册），要从环境变量拿配置，
要真的把报告文件写到磁盘。任何一步断掉，下面的断言都会红。

和 examples/harness/主程序.light 的 mock 测试的分工
----------------------------------------------------
test_harness_e2e.py 用 HTTP MockDeepSeek 起协议等价的本地 mock，验证主程序
（代理循环 + 工具协议链路）整进程行为。评测驱动.light 不依赖工具协议，它依赖
的是「并发编排 + 打分 + 报告」这条评测链路；本轮基线中 A5/C5 未合入，评测驱动
的 LLM 通道是 harness 内的确定性 mock 通道（LLM通道.light，零网络）。因此本
文件用「内置确定性通道 + 环境变量注入故障」的 mock 方式跑整进程，断言：
  1. 报告 JSON 数字与手算逐项相等（通过/未通过/通过率/子集/逐条得分）
  2. 并发时序断关系（并发 2 总耗时 < 串行 1 总耗时）
  3. 故障注入 → 重试路径生效（尝试次数=重试次数、错误分类、得分 0）
A5 合入后评测驱动替换 LLM 通道为 stdlib 异步客户端，本文件的断言（报告数字 +
时序 + 故障）不需要改——判据断行为，不断实现。
"""
import json
import os
import subprocess
import sys

import pytest

_PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_评测驱动 = os.path.join(_PROJECT, "examples", "harness", "评测驱动.light")


def _跑评测(报告目录, 额外环境=None, 超时=180):
    """整进程跑 评测驱动.light，返回 (returncode, 报告路径, stdout)"""
    环境 = {
        **os.environ,
        "HARNESS_REPORT": os.path.join(str(报告目录), "评测报告"),
        # 第六轮给驱动加了 HARNESS_CHANNEL=real 真实后端。这里**钉死 mock**：
        # 这个 dict 继承 os.environ，开发者环境里留着一个 HARNESS_CHANNEL=real
        # 就会让这一整套「零发网」用例真发网到 api.deepseek.com。
        "HARNESS_CHANNEL": "mock",
        # 同理钉死 single：第七轮 C7 给驱动加了 HARNESS_MODE=agent，开发者 shell 里
        # 残留一个 agent 就会让这一整套「单轮零工具」用例跑成 agent 链（评测集都换了），
        # 断言全错却指不到根因。第八轮实地踩过一次。
        "HARNESS_MODE": "single",
        # 单价同样钉空：残留的 HARNESS_PRICE_IN/OUT 会让「未配置单价」那条断言本机红。
        "HARNESS_PRICE_IN": "",
        "HARNESS_PRICE_OUT": "",
        # 超时同理钉空（第八轮新增）：shell 里残留一个 HARNESS_TIMEOUT_SEC=0.05
        # 会把这一整套用例跑成「六条全超时」。
        "HARNESS_TIMEOUT_SEC": "",
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }

    if 额外环境:
        环境.update(额外环境)
    结果 = subprocess.run(
        [sys.executable, "-m", "cli.light_unified", "run", _评测驱动],
        cwd=_PROJECT,
        env=环境,
        capture_output=True,
        timeout=超时,
    )
    return 结果.returncode, os.path.join(str(报告目录), "评测报告.json"), 结果.stdout


def _文本(字节串):
    return 字节串.decode("utf-8", errors="replace")


def _读报告(报告路径):
    with open(报告路径, encoding="utf-8") as f:
        return json.load(f)


class Test报告数字与手算逐项一致:
    """默认评测集（6 条，内置确定性答案表）跑完，报告里每一个数字都对得上。"""

    def test_整进程跑通且报告数字逐项相等(self, tmp_path):
        rc, 报告路径, 输出 = _跑评测(tmp_path, {"HARNESS_DELAY_SEC": "0.01"})
        assert rc == 0, "评测驱动整进程失败\nstdout:\n%s" % _文本(输出)
        报告 = _读报告(报告路径)

        # 汇总：手算 = 6 条，精确 1/2、集合 1/2、正则 1/2 → 通过 3 / 未通过 3 / 0.5
        汇总 = 报告["汇总"]
        assert 汇总["总条数"] == 6
        assert 汇总["通过数"] == 3
        assert 汇总["未通过数"] == 3
        assert 汇总["通过率"] == 0.5

        # 子集统计：三个打分器各 2 条、各通过 1 条、各 0.5
        子集 = {s["打分器"]: s for s in 汇总["子集"]}
        assert 子集["精确"]["总条数"] == 2
        assert 子集["精确"]["通过数"] == 1
        assert 子集["精确"]["通过率"] == 0.5
        assert 子集["集合"]["总条数"] == 2
        assert 子集["集合"]["通过数"] == 1
        assert 子集["集合"]["通过率"] == 0.5
        assert 子集["正则"]["总条数"] == 2
        assert 子集["正则"]["通过数"] == 1
        assert 子集["正则"]["通过率"] == 0.5

        # 逐条得分：精确 1/0、集合 1/0、正则 1/0
        得分表 = [e["得分"] for e in 报告["条目"]]
        assert 得分表 == [1, 0, 1, 0, 1, 0]

        # 每条都一次成功（无故障注入时尝试次数恒为 1）
        尝试表 = [e["尝试次数"] for e in 报告["条目"]]
        assert 尝试表 == [1, 1, 1, 1, 1, 1]

        # 输出内容与内置答案表一致（断言模型输出真的进了报告）
        输出表 = [e["输出"] for e in 报告["条目"]]
        assert 输出表 == ["北京", "西方", "苹果、香蕉、橙子", "Python、Java", "user@example.com", "12345"]

    def test_并发时序断关系(self, tmp_path):
        """同一条延迟下：并发 2 的总耗时必须明显小于串行 1 的总耗时（断关系不断绝对）。

        6 条 × 0.4s：串行理论 2.4s+，并发 2 理论 1.2s+。断言「并发 < 串行」这个关系，
        不写死绝对秒数（CI 负载会让绝对数漂）。
        """
        环境 = {"HARNESS_DELAY_SEC": "0.4"}
        rc并, 报告并, 输出并 = _跑评测(tmp_path / "并", {**环境, "HARNESS_CONCURRENCY": "2"})
        assert rc并 == 0, "并发 2 跑失败\n%s" % _文本(输出并)
        并发耗时 = _读报告(报告并)["元信息"]["总耗时"]

        rc串, 报告串, 输出串 = _跑评测(tmp_path / "串", {**环境, "HARNESS_CONCURRENCY": "1"})
        assert rc串 == 0, "串行跑失败\n%s" % _文本(输出串)
        串行耗时 = _读报告(报告串)["元信息"]["总耗时"]

        # 关系断言：并发 2 明显快于串行 1（并发不是假的）
        assert 并发耗时 < 串行耗时, (
            "并发没有生效：并发 %s >= 串行 %s" % (并发耗时, 串行耗时))
        # 并发 2 的耗时应接近 2 批 × 0.4 = 0.8s 而非串行的 2.4s
        assert 并发耗时 < 串行耗时 * 0.8


class Test故障注入与重试路径:
    """环境变量注入超时/连接错误 → 对应条目标记尝试次数=重试次数、错误分类、得分 0。"""

    def test_超时注入走重试且得分为零(self, tmp_path):
        环境 = {
            "HARNESS_DELAY_SEC": "0.01",
            "HARNESS_RETRIES": "3",
            "HARNESS_FAULT_TIMEOUT_PROMPTS": "列出中国的首都",
        }
        rc, 报告路径, 输出 = _跑评测(tmp_path, 环境)
        assert rc == 0, _文本(输出)
        报告 = _读报告(报告路径)

        首条 = 报告["条目"][0]
        assert 首条["prompt"] == "列出中国的首都"
        assert 首条["尝试次数"] == 3
        assert 首条["错误"] == "可重试错误"
        assert 首条["得分"] == 0

        # 汇总同步变化：通过 3 - 1 = 2，通过率 2/6
        assert 报告["汇总"]["通过数"] == 2
        assert 报告["汇总"]["未通过数"] == 4
        assert 报告["汇总"]["通过率"] == 2 / 6

    def test_连接错误注入走重试且得分为零(self, tmp_path):
        环境 = {
            "HARNESS_DELAY_SEC": "0.01",
            "HARNESS_RETRIES": "2",
            "HARNESS_FAULT_ERROR_PROMPTS": "给出一个邮箱地址",
        }
        rc, 报告路径, 输出 = _跑评测(tmp_path, 环境)
        assert rc == 0, _文本(输出)
        报告 = _读报告(报告路径)

        第五 = 报告["条目"][4]
        assert 第五["prompt"] == "给出一个邮箱地址"
        assert 第五["尝试次数"] == 2
        assert 第五["错误"] == "可重试错误"
        assert 第五["得分"] == 0

        assert 报告["汇总"]["通过数"] == 2


class Test缺环境早退:
    """评测集缺失时打印原因并以非零码退出（不静默成功，与主程序.light 同口径）。"""

    def test_评测集不存在时非零退出(self, tmp_path):
        环境 = {
            "HARNESS_EVAL_SET": os.path.join(str(tmp_path), "不存在的评测集.jsonl"),
        }
        rc, 报告路径, 输出 = _跑评测(tmp_path, 环境)
        assert rc == 2
        标准输出 = _文本(输出)
        assert "评测集不存在" in 标准输出

    def test_real通道缺key时非零退出且不降级(self, tmp_path):
        """HARNESS_CHANNEL=real 且无 key：必须退 2，不许静默降级回 mock。

        降级回 mock 会让「真实实测」和「mock 复读」产出同一份报告——
        报告数字看起来齐全，读的人无法分辨它到底发过网没有。
        本用例不发网：缺 key 的判断在建通道之前。
        """
        环境 = {"HARNESS_CHANNEL": "real", "DEEPSEEK_API_KEY": ""}
        rc, 报告路径, 输出 = _跑评测(tmp_path, 环境)
        assert rc == 2, "real 通道缺 key 应退 2，实际 %d\n%s" % (rc, _文本(输出))
        标准输出 = _文本(输出)
        assert "DEEPSEEK_API_KEY" in 标准输出, 标准输出
        assert not os.path.exists(报告路径), "缺 key 早退不该写出报告"

    def test_mock报告标注通道(self, tmp_path):
        """报告元信息里必须写明通道，否则两种模式的报告长得一模一样。"""
        rc, 报告路径, 输出 = _跑评测(tmp_path, {"HARNESS_DELAY_SEC": "0.01"})
        assert rc == 0, _文本(输出)
        assert _读报告(报告路径)["元信息"]["通道"] == "mock"


class Test用量与成本进报告:
    """第八轮：用量透传端到端（#11 的兑现判据）。

    mock 通道的词元数是**字符数替身**（LLM通道.造桩用量），所以报告里的总数
    必须精确等于逐条 prompt / 输出 的字符数之和 —— 可手算对账，等值断言。
    """

    def test_单模用量等于逐条字符数之和(self, tmp_path):
        rc, 报告路径, 输出 = _跑评测(tmp_path, {"HARNESS_DELAY_SEC": "0"})
        assert rc == 0, _文本(输出)
        报告 = _读报告(报告路径)
        入 = sum(len(e["prompt"]) for e in 报告["条目"])
        出 = sum(len(e["输出"]) for e in 报告["条目"])
        assert 报告["汇总"]["用量"] == {"总输入词元": 入, "总输出词元": 出}
        # 逐条也要带上，否则汇总对了也可能是别处硬编的
        assert [e["输入词元"] for e in 报告["条目"]] == [len(e["prompt"]) for e in 报告["条目"]]
        # 没给单价：成本估算 留空串 + 说明写明缘由，**不许拿 0 冒充**
        assert 报告["汇总"]["成本"]["成本估算"] == ""
        assert 报告["汇总"]["成本"]["成本说明"] == "未配置单价"

    def test_配了单价就按每千词元算出成本(self, tmp_path):
        rc, 报告路径, 输出 = _跑评测(
            tmp_path,
            {"HARNESS_DELAY_SEC": "0", "HARNESS_PRICE_IN": "0.5", "HARNESS_PRICE_OUT": "1.5"},
        )
        assert rc == 0, _文本(输出)
        报告 = _读报告(报告路径)
        用量 = 报告["汇总"]["用量"]
        期望 = (用量["总输入词元"] / 1000) * 0.5 + (用量["总输出词元"] / 1000) * 1.5
        assert 报告["汇总"]["成本"]["成本估算"] == pytest.approx(期望)
        assert 报告["汇总"]["成本"]["成本说明"] == "已按每千词元单价估算"

    def test_只给一半单价当没配(self, tmp_path):
        """拿 0 当另一半会算出个「看着像真的、其实只算了一半」的成本，比不算更坏。"""
        rc, 报告路径, 输出 = _跑评测(
            tmp_path, {"HARNESS_DELAY_SEC": "0", "HARNESS_PRICE_IN": "0.5"}
        )
        assert rc == 0, _文本(输出)
        assert _读报告(报告路径)["汇总"]["成本"]["成本说明"] == "未配置单价"


class Test单条超时:
    """第八轮：HARNESS_TIMEOUT_SEC 接 stdlib/并发.超时运行（#16 由 none 升回 partial 的判据）。

    判据形态是「等值 + 全场跑完」：超时秒 咬死于 mock 延迟之下时，六条**全部**落
    「超时」类、报告照样落盘、rc=0（协程内自保，异常不冒泡到任务池）。
    """

    def test_限时小于延迟时六条全记超时且整场跑完(self, tmp_path):
        rc, 报告路径, 输出 = _跑评测(
            tmp_path, {"HARNESS_DELAY_SEC": "0.3", "HARNESS_TIMEOUT_SEC": "0.05"}
        )
        assert rc == 0, _文本(输出)
        报告 = _读报告(报告路径)
        assert 报告["汇总"]["失败分类计数"]["超时"] == 6
        assert 报告["汇总"]["通过数"] == 0
        assert [e["错误分类"] for e in 报告["条目"]] == ["超时"] * 6
        # 没跑完的条目不许报词元数（空 = 没采到，不是 0）
        assert [e["输入词元"] for e in 报告["条目"]] == [None] * 6
        assert 报告["汇总"]["用量"] == {}

    def test_限时大于延迟时与不限时逐项等价(self, tmp_path):
        rc, 报告路径, 输出 = _跑评测(
            tmp_path, {"HARNESS_DELAY_SEC": "0.01", "HARNESS_TIMEOUT_SEC": "30"}
        )
        assert rc == 0, _文本(输出)
        报告 = _读报告(报告路径)
        assert [e["得分"] for e in 报告["条目"]] == [1, 0, 1, 0, 1, 0]
        assert 报告["汇总"]["失败分类计数"]["超时"] == 0

    def test_超时秒给0当没配(self, tmp_path):
        """0 秒当「不限时」而不是「立刻超时」：wait_for(…, 0) 会把每条都判死。"""
        rc, 报告路径, 输出 = _跑评测(
            tmp_path, {"HARNESS_DELAY_SEC": "0.01", "HARNESS_TIMEOUT_SEC": "0"}
        )
        assert rc == 0, _文本(输出)
        assert _读报告(报告路径)["汇总"]["通过数"] == 3




