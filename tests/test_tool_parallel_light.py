# -*- coding: utf-8 -*-
"""test_tool_parallel_light.py —— A4-1 / A4-2 / A4-3：工具副作用判据与并行调度

被测对象是 `stdlib/代理循环.light` 的 `注册工具` / `工具声明` / `分发工具`。

**为什么这个文件不起 HTTP 服务器**：本轮测的是「拿到一批 tool_calls 之后怎么调度」，
`分发工具` 是这条路的入口，可以直接喂它一个 tool_calls 列表。绕开网络层不是偷懒，
是把变量减到只剩调度本身——否则 SSE 分帧、重试退避、端口竞争都会混进耗时里，
时序判据立刻失去意义。往返链路的覆盖在 test_agent_loop_light.py 与 test_deepseek_mock.py。

**判据口径（第四轮总纲 §5.1）**：并行是运行时行为，只能用**时序 + 副作用 + 返回值**判，
不许用「代码里有 threading.Thread 这个字符串」之类的静态断言。所以：
  - 时序判据：同一组 sleep，只改 副作用 标记，断并行/串行两种耗时都符合预期并断比值
  - 顺序判据：先证明「完成顺序真的被打乱了」，再断回填顺序仍等于 tool_calls 顺序
    （少了前半句，这条判据在「其实没并行」时也会绿——那就是假绿）
  - 隔离判据：混合批必须串行，且**不发** 并行开始 / 并行结束
  - 失败判据：并行批里一个抛异常，其余两个照常回填
"""
import os
import sys
import time

import pytest

_STDLIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stdlib")
if _STDLIB not in sys.path:
    sys.path.insert(0, _STDLIB)
import _light_import_hook
_light_import_hook.install([_STDLIB])

from 代理循环 import 代理循环


# 单个工具的 sleep 时长。0.3s 的选取理由：
#  - 足够长，能盖住线程创建与 join 的开销（Windows 上约 1ms 级），
#    让「并行 ≈ 0.3s / 串行 ≈ 0.9s」这两个区间不重叠；
#  - 足够短，四条时序用例加起来仍在几秒内跑完，不至于拖慢定向回归。
睡 = 0.3

空模式 = {"type": "object", "properties": {}, "required": []}


def _agent(并行上限=4):
    """造一个不发网络请求的 agent。

    地址指向 127.0.0.1:1（必然连不上）是刻意的：本文件从不调 运行()，
    只调 分发工具()。真去连了就说明测试写错了，会当场超时暴露，而不是静默走网络。
    """
    a = 代理循环("http://127.0.0.1:1", "test-model", "",
              最大轮数值=3, 消息上限值=20)
    a.并行上限 = 并行上限
    return a


def _tc(名称, 序号, 参数="{}"):
    return {"name": 名称, "arguments": 参数, "index": 序号}


def _睡工具(名字, 秒=睡, 完成序列=None):
    def 实现(参数):
        time.sleep(秒)
        if 完成序列 is not None:
            完成序列.append(名字)
        return "结果:" + 名字
    return 实现


def _炸工具(名字, 秒=睡):
    def 实现(参数):
        time.sleep(秒)
        raise RuntimeError("_taskA4_故意炸:" + 名字)
    return 实现


def _tool消息(a):
    return [m for m in a.会话列表() if m["role"] == "tool"]


def _批(a, 名字们, 副作用, 完成序列=None, 炸的名字=()):
    """注册一批工具并返回对应的 tool_calls（顺序与 名字们 一致）。"""
    for i, n in enumerate(名字们):
        实现 = _炸工具(n) if n in 炸的名字 else _睡工具(n, 睡, 完成序列)
        a.注册工具(n, "测试工具 " + n, 空模式, 实现, 副作用)
    return [_tc(n, i) for i, n in enumerate(名字们)]


def _计时分发(a, 调用):
    t0 = time.monotonic()
    a.分发工具(调用)
    return time.monotonic() - t0


# ==================================================== A4-1：副作用第五参
class Test副作用字段:
    def test_省略第五参时默认是写(self):
        """默认必须是最保守的那个。断的是 工具表 里的字典内容，不是「没报错」。"""
        a = _agent()
        a.注册工具("t_default", "省略第五参", 空模式, lambda p: "x")
        assert a.工具表["t_default"]["副作用"] == "写"

    def test_三种合法取值原样进表(self):
        a = _agent()
        for 名, 值 in (("t_ro", "只读"), ("t_w", "写"), ("t_x", "执行")):
            a.注册工具(名, "d", 空模式, lambda p: "x", 值)
        assert a.工具表["t_ro"]["副作用"] == "只读"
        assert a.工具表["t_w"]["副作用"] == "写"
        assert a.工具表["t_x"]["副作用"] == "执行"

    @pytest.mark.parametrize("坏值", [
        "readonly", "read_only", "只讀", "", "READONLY", "只读 ", None, 1, True,
    ])
    def test_非法取值必须抛错而不是回落到默认(self, 坏值):
        """静默回落是最坏的选择：一个被标成 "read_only" 的写工具会被当成默认「写」，
        看起来"安全"，但没人会发现标记根本没生效；反过来若默认成「只读」，
        它会被并行执行。所以只许抛。"""
        a = _agent()
        with pytest.raises(Exception) as ei:
            a.注册工具("t_bad", "d", 空模式, lambda p: "x", 坏值)
        assert ei.type.__name__ == "工具注册错误"
        assert "只许三种" in str(ei.value)
        # 抛错后不许留下半注册的痕迹
        assert "t_bad" not in a.工具表

    def test_工具声明逐字段只有name_description_parameters(self):
        """副作用 是本地调度判据，OpenAI 的 function 对象规范里没有这个键。
        多发未知字段的后果是「本地全绿、一连真模型就 400」。"""
        a = _agent()
        a.注册工具("read_file", "读文件", 空模式, lambda p: "x", "只读")
        a.注册工具("write_file", "写文件", 空模式, lambda p: "x", "写")
        声明 = a.工具声明()
        assert [d["type"] for d in 声明] == ["function", "function"]
        for d in 声明:
            assert sorted(d.keys()) == ["function", "type"]
            assert sorted(d["function"].keys()) == ["description", "name", "parameters"]
        assert [d["function"]["name"] for d in 声明] == ["read_file", "write_file"]
        # 整个声明序列化后不许出现「副作用」这三个字（含嵌套的任何层）
        import json
        assert "副作用" not in json.dumps(声明, ensure_ascii=False)


# ==================================================== A4-2：并行调度
class Test并行时序:
    def test_只读批并行_同一批标成写则串行(self):
        """时序判据：同一组工具、同样的 sleep，**只改 副作用 标记**，两种跑法都跑。

        只跑并行那一半是不够的：万一 0.3s 的 sleep 在这台机器上就是量不准，
        并行那条也会绿。必须让串行那条在同一次运行里给出对照值。
        """
        甲 = _agent()
        调用甲 = _批(甲, ["r1", "r2", "r3"], "只读")
        并行耗时 = _计时分发(甲, 调用甲)

        乙 = _agent()
        调用乙 = _批(乙, ["w1", "w2", "w3"], "写")
        串行耗时 = _计时分发(乙, 调用乙)

        报告 = "并行 %.3fs / 串行 %.3fs（单工具 sleep %.2fs）" % (并行耗时, 串行耗时, 睡)
        print("[A4-2 时序] " + 报告 + "，比值 %.2f" % (串行耗时 / 并行耗时))
        assert 并行耗时 < 0.5, "只读批没有真并行：" + 报告
        assert 串行耗时 > 0.9, "写批没有真串行：" + 报告
        assert 串行耗时 / 并行耗时 > 2.0, "并行/串行没有量级差异：" + 报告
        # 两种跑法都必须把三条结果都回填了——快不等于对
        assert [m["content"] for m in _tool消息(甲)] == ["结果:r1", "结果:r2", "结果:r3"]
        assert [m["content"] for m in _tool消息(乙)] == ["结果:w1", "结果:w2", "结果:w3"]

    def test_漏标第五参的批不会被并行(self):
        """「默认最保守」的行为级验证：省略第五参的三个工具必须串行跑。
        只断 工具表["副作用"] == "写" 不够——那只证明字典写对了，
        不证明调度层真按它走。"""
        a = _agent()
        for n in ("d1", "d2", "d3"):
            a.注册工具(n, "省略第五参", 空模式, _睡工具(n))
        耗时 = _计时分发(a, [_tc("d1", 0), _tc("d2", 1), _tc("d3", 2)])
        print("[A4-1 保守默认] 三个省略第五参的工具耗时 %.3fs" % 耗时)
        assert 耗时 > 0.9, "漏标第五参的工具被并行执行了（耗时 %.3fs）" % 耗时

    def test_并发上限真的限制了同时在跑的数量(self):
        """并发上限=2 跑四个 0.3s 只读工具 → 必须分两批 ≈0.6s。
        上限若是摆设（一次全起），耗时会掉到 ≈0.3s；若退化成串行，会涨到 ≈1.2s。
        两侧都卡住，中间那个区间只有「真的分了两批」能落进来。"""
        a = _agent(并行上限=2)
        调用 = _批(a, ["q1", "q2", "q3", "q4"], "只读")
        耗时 = _计时分发(a, 调用)
        print("[A4-2 并发上限] 上限=2 四个 sleep %.2fs 的只读工具，耗时 %.3fs" % (睡, 耗时))
        assert 0.5 < 耗时 < 0.9, "并发上限=2 跑四任务耗时 %.3fs，不符合「两批」预期" % 耗时
        assert [m["content"] for m in _tool消息(a)] == [
            "结果:q1", "结果:q2", "结果:q3", "结果:q4"]

    def test_单项批不起线程(self):
        """一个工具起一个线程再 join，纯属白付开销。可整批并行 对 len<2 返回假。"""
        a = _agent()
        事件 = []
        a.订阅("并行开始", lambda e, p: 事件.append(e))
        调用 = _批(a, ["solo"], "只读")
        耗时 = _计时分发(a, 调用)
        assert 事件 == []
        assert 耗时 < 0.5
        assert [m["content"] for m in _tool消息(a)] == ["结果:solo"]


class Test回填顺序:
    def test_回填顺序等于tool_calls顺序而不是完成顺序(self):
        """顺序判据。sleep 递减让完成顺序**倒过来**，回填顺序必须不受影响。

        第一条断言（完成 == 反序）是这条用例的**前提校验**：它证明完成顺序真的
        被打乱了。没有它，本用例在「其实完全串行」的实现上也会绿——那时完成顺序
        恰好等于 tool_calls 顺序，第二条断言不费力就过，等于零信号。
        """
        a = _agent()
        完成 = []
        for 名, 秒 in (("slow", 0.30), ("mid", 0.18), ("fast", 0.06)):
            a.注册工具(名, "d", 空模式, _睡工具(名, 秒, 完成), "只读")
        调用 = [_tc("slow", 0), _tc("mid", 1), _tc("fast", 2)]
        a.分发工具(调用)

        assert 完成 == ["fast", "mid", "slow"], (
            "完成顺序没有被打乱（实际 %r），本用例的前提不成立" % (完成,))
        消息们 = _tool消息(a)
        assert [m["name"] for m in 消息们] == ["slow", "mid", "fast"]
        assert [m["content"] for m in 消息们] == ["结果:slow", "结果:mid", "结果:fast"]
        # tool_call_id 也必须跟着位置走，不能跟着完成顺序走
        assert [m["tool_call_id"] for m in 消息们] == ["call_0", "call_1", "call_2"]


class Test隔离:
    def test_混合批整批串行且不重排(self):
        """隔离判据：两只读 + 一写。不许「先把两个只读并行掉、再串行跑那个写」。

        重排在本地永远看不出问题，但模型可能靠顺序表达因果（先 write 再 read
        同一个文件）。所以判据是**总耗时等于三个串行之和**，而不是「写的那个最后跑」。
        """
        a = _agent()
        事件 = []
        a.订阅("并行开始", lambda e, p: 事件.append(e))
        a.订阅("并行结束", lambda e, p: 事件.append(e))
        a.注册工具("m_r1", "只读", 空模式, _睡工具("m_r1"), "只读")
        a.注册工具("m_r2", "只读", 空模式, _睡工具("m_r2"), "只读")
        a.注册工具("m_w1", "写", 空模式, _睡工具("m_w1"), "写")
        调用 = [_tc("m_r1", 0), _tc("m_r2", 1), _tc("m_w1", 2)]
        耗时 = _计时分发(a, 调用)
        print("[A4-2 隔离] 两只读+一写 混合批耗时 %.3fs（三个 sleep %.2fs 串行）" % (耗时, 睡))
        assert 耗时 > 0.9, "混合批被部分并行了（耗时 %.3fs，三个串行应 >0.9s）" % 耗时
        assert 事件 == [], "混合批不该发并行事件，实际发了 %r" % (事件,)
        assert [m["name"] for m in _tool消息(a)] == ["m_r1", "m_r2", "m_w1"]

    def test_执行类工具也让整批降级串行(self):
        a = _agent()
        a.注册工具("x_r1", "只读", 空模式, _睡工具("x_r1"), "只读")
        a.注册工具("x_r2", "只读", 空模式, _睡工具("x_r2"), "只读")
        a.注册工具("x_cmd", "执行", 空模式, _睡工具("x_cmd"), "执行")
        耗时 = _计时分发(a, [_tc("x_r1", 0), _tc("x_r2", 1), _tc("x_cmd", 2)])
        assert 耗时 > 0.9, "混入「执行」的批被并行了（耗时 %.3fs）" % 耗时


class Test失败隔离:
    def test_并行批里一个抛异常其余两个照常回填(self):
        a = _agent()
        调用 = _批(a, ["ok1", "boom", "ok2"], "只读", 炸的名字=("boom",))
        耗时 = _计时分发(a, 调用)
        消息们 = _tool消息(a)
        assert [m["name"] for m in 消息们] == ["ok1", "boom", "ok2"]
        assert 消息们[0]["content"] == "结果:ok1"
        assert 消息们[2]["content"] == "结果:ok2"
        # 失败项转成可读文本喂回模型，且带上原始异常信息（不许吞成空串）
        assert "工具执行出错" in 消息们[1]["content"]
        assert "_taskA4_故意炸:boom" in 消息们[1]["content"]
        # 一个失败不许把并行退化成串行
        assert 耗时 < 0.5, "一个工具抛异常后整批退化成串行了（耗时 %.3fs）" % 耗时

    def test_校验失败的项让整批走串行且不进工具实现(self):
        """参数不合 schema 的项在编排阶段就被判失败，实现不会被调用。
        它的 副作用 仍是注册时的值，所以这一批仍可能并行——但**它自己不执行**。"""
        a = _agent()
        进过 = []

        def 记账(参数):
            进过.append(1)
            return "不该被调用"

        严模式 = {"type": "object", "properties": {"city": {"type": "string"}},
                "required": ["city"]}
        a.注册工具("v_ok", "只读", 空模式, _睡工具("v_ok"), "只读")
        a.注册工具("v_bad", "只读", 严模式, 记账, "只读")
        a.分发工具([_tc("v_ok", 0), _tc("v_bad", 1, '{"city": 123}')])
        消息们 = _tool消息(a)
        assert [m["name"] for m in 消息们] == ["v_ok", "v_bad"]
        assert 消息们[0]["content"] == "结果:v_ok"
        assert "工具调用失败" in 消息们[1]["content"]
        assert 进过 == []

    def test_未注册工具让整批降级串行(self):
        """未注册项记「写」是保守票：注册表里查不到的东西不许被当成可并行的只读项。"""
        a = _agent()
        a.注册工具("u_r1", "只读", 空模式, _睡工具("u_r1"), "只读")
        a.注册工具("u_r2", "只读", 空模式, _睡工具("u_r2"), "只读")
        耗时 = _计时分发(a, [_tc("u_r1", 0), _tc("u_r2", 1), _tc("u_ghost", 2)])
        消息们 = _tool消息(a)
        assert [m["name"] for m in 消息们] == ["u_r1", "u_r2", "u_ghost"]
        assert "未注册工具" in 消息们[2]["content"]
        assert 耗时 > 0.55, "混入未注册项的批被并行了（耗时 %.3fs）" % 耗时


# ==================================================== A4-3：并行开始 / 并行结束
class Test并行事件:
    def test_并行批成对发出两个事件并带工具名列表(self):
        a = _agent()
        事件 = []
        a.订阅("并行开始", lambda 名, 载荷: 事件.append((名, 载荷)))
        a.订阅("并行结束", lambda 名, 载荷: 事件.append((名, 载荷)))
        调用 = _批(a, ["e1", "e2", "e3"], "只读")
        a.分发工具(调用)
        assert [名 for 名, _ in 事件] == ["并行开始", "并行结束"]
        for _, 载荷 in 事件:
            # 工具名列表按 tool_calls 顺序，不是注册顺序也不是完成顺序
            assert 载荷["工具名列表"] == ["e1", "e2", "e3"]
            assert 载荷["并发上限"] == 4
            assert 载荷["轮次"] == 0

    def test_并行结束在结果全部回填之后才发(self):
        """事件顺序有语义：订阅方收到 并行结束 时，会话里应该已经有全部 tool 消息。
        若把 发事件 提到回填之前，监听器看到的会话是残缺的。"""
        a = _agent()
        快照 = []
        a.订阅("并行开始", lambda 名, 载荷: 快照.append(("开始", len(_tool消息(a)))))
        a.订阅("并行结束", lambda 名, 载荷: 快照.append(("结束", len(_tool消息(a)))))
        调用 = _批(a, ["s1", "s2", "s3"], "只读")
        a.分发工具(调用)
        assert 快照 == [("开始", 0), ("结束", 3)]

    def test_串行批一个并行事件都不发(self):
        a = _agent()
        事件 = []
        a.订阅("并行开始", lambda 名, 载荷: 事件.append(名))
        a.订阅("并行结束", lambda 名, 载荷: 事件.append(名))
        调用 = _批(a, ["n1", "n2", "n3"], "写")
        a.分发工具(调用)
        assert 事件 == []

    def test_工具调用事件仍对每一项各发一次且在主线程(self):
        """并行改造不许弄丢既有事件。工具调用 是编排阶段发的，
        所以三项都发、顺序与 tool_calls 一致，且全部在主线程（线程 id 相同）。"""
        import threading
        a = _agent()
        记录 = []
        a.订阅("工具调用", lambda 名, 载荷: 记录.append(
            (载荷["名称"], threading.current_thread().ident)))
        调用 = _批(a, ["p1", "p2", "p3"], "只读")
        a.分发工具(调用)
        assert [名 for 名, _ in 记录] == ["p1", "p2", "p3"]
        assert set(t for _, t in 记录) == {threading.current_thread().ident}
