# -*- coding: utf-8 -*-
"""T-0320：语法速查卡按近 30 天错误频次动态置顶。

覆盖四块：
  1. error_stats.rank_pitfalls：按 code 聚合 hits、hits 降序 / last_seen 倒序、
     top 截断、30 天窗口过滤、坏行跳过并计数；
  2. 语料缺失 / 坏行 / 空目录 → 空列表，不抛；
  3. 快照：无 ranked 时 generate_syntax_card() / (compact=True) 与改动前逐字一致；
  4. 有 ranked 时置顶区块在最前，且原有小节顺序不变。

快照说明：卡面原计划放 tests/fixtures/syntax_card_baseline_*.txt，但该目录不在本卡
允许修改路径内，故把改动前的逐字输出内联成常量（_BASELINE_FULL / _BASELINE_COMPACT），
效果等价：任何静态输出的字节漂移都会让快照用例失败。
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOLS = os.path.join(_ROOT, "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

from ai_copilot import error_stats, syntax_card  # noqa: E402


# ── 快照：改动前 generate_syntax_card 的逐字输出 ─────────────────────
_BASELINE_FULL = r"""【光明 v3.2 语法速查卡】

一、变量与赋值
  声明：设 甲 为 10 / 定义 乙 等于 "你好"
  赋值：甲 等于 30 / 甲 为 40 / 甲加上1 / 甲减去2 / 甲乘以3 / 甲除以4
  注意：空格可选，设甲为10 合法

二、段落（函数）
  定义：段落 名 接收 参数1, 参数2：  （仅"段落"+"接收"，无旧形式）
  无参：段落 名：
  类型：段落 名 接收 甲:数, 乙:文本：
  返回：返回 值

三、条件
  如果 条件：/ 否则如果 条件：/ 否则：
  单行：如果 条件：语句
  简写：若 代替 如果
  冒号必选

四、循环
  当 条件：          （while）
  遍历 项 于 列表：   （for-in，于/在/之/中的 均可）
  遍历 i 于 1至10：  （范围遍历，步长：1至10步2）
  跳出 / 跳过         （break/continue，无句号）

五、运算符
  算术：加/减/乘/除以/取余/幂
  复合：加上/减去/乘以/除以
  比较：等于/不等于/大于/小于/大于等于/小于等于
  逻辑：且/或/非

六、异常
  尝试：…捕获 异常：…最终：…
  抛出 异常

七、类
  类 名：/ 类 子 继承 父：
  属性 名 / 构造 接收 …：
  己.属性 / 父.构造(…)
  新建 类名(参数)
  ⚠ 类系统建议用 LLVM 后端运行

八、导入导出
  导入 模块 / 从 模块 导入 符号 / 导出 符号1, 符号2

九、特殊值
  真/假/空

十、内置类型
  串 / 任意 / 典 / 列 / 列表 / 字典 / 小数 / 布尔 / 数 / 整数 / 文本 / 浮数 / 空 / 集 / 集合

十一、SRC后端可用内建函数（Python内建，直接可用）
  len()/str()/int()/float()/type()/range()/abs()/round()/min()/max()
  print()已映射为打印

十二、中文内建函数（需导入或已内置，按类别）
  文件I/O：读取文件 / 写入文件 / 追加文件 / 文件存在 / 目录存在 / 路径存在 / 创建目录 / 删除文件 / 删除目录 / 列出目录 / 文件大小
  路径操作：绝对路径 / 连接路径 / 目录名 / 文件名 / 扩展名 / 分割路径 / 分割扩展名
  字符串工具：转整数 / 转浮点 / 转字符串 / 字符串长度 / 字符串获取 / 分割字符串 / 连接字符串 / 替换字符串 / 去除空白
  列表工具：列 / 列表长度 / 列表追加 / 列表弹出 / 列表排序 / 列表反转 / 列表包含
  字典工具：字典创建 / 字典设置 / 字典删除 / 字典键列表 / 字典值列表 / 字典项列表 / 字典包含键 / 字典获取
  类型检查：是整数 / 是浮点 / 是字符串 / 是列表 / 是字典 / 是空 / 是字母 / 是数字 / 是空白
  数学统计：阶乘 / 平均数 / 中位数 / 众数 / 方差 / 标准差 / 样本方差 / 样本标准差 / 求和 / 累积和 / 圆周率 / 自然常数 / 角度转弧度 / 弧度转角度
  随机：随机整数 / 随机浮点 / 随机选择
  JSON：解析JSON / 序列化JSON / 美化JSON
  系统：环境变量 / 设置环境变量 / 参数列表 / 退出程序 / 当前目录 / 切换目录 / 执行命令
  输入输出：读取行 / 读取N字节 / 写入输出 / 打印输出 / 刷新输出 / 写入错误 / 打印错误

十三、核心规则
  · 冒号必选（块级语句末尾）
  · 句号可选（所有语句）
  · 空格可选（关键字/变量/运算符间）
  · 纯缩进表示代码块（无花括号/无结束关键字）
"""

_BASELINE_COMPACT = r"""【光明v3.2速查】
变量：设甲为10 / 定义乙等于"你好" / 甲等于30 / 甲加上1
段落：段落名接收a,b： / 返回值 / 段落名：（无参）
条件：如果条件：/ 否则如果条件：/ 否则：/ 冒号必选
循环：当条件：/ 遍历i于1至10：/ 遍历项于列表：/ 跳出/跳过
运算：加/减/乘/除以/取余/等于/不等于/大于/小于/大于等于/小于等于/且/或/非
异常：尝试：…捕获异常：…/ 抛出异常
类：类名：/ 构造接收…：/ 己.属性/ 父.构造/ 新建类名() ⚠需LLVM后端
导入：从模块导入符号 / 导出符号1,符号2
特殊：真/假/空
SRC内建：len()/str()/int()/float()/type()/range()/print()→打印
暗坑：列表[i]=值✓ | 设列表[i]为值✗ | 变量名≠内建函数名 | 运算用中文不用符号
规则：冒号必选·句号可选·空格可选·纯缩进代码块
"""


# ── 语料构造辅助 ──────────────────────────────────────────────────

def _now():
    return datetime.now().astimezone()


def _iso(days_ago=0):
    return (_now() - timedelta(days=days_ago)).isoformat(timespec="seconds")


def _write_lines(corpus_dir, records):
    """按记录自身时间戳落到 YYYY-MM.jsonl（模拟 error_corpus 的落盘布局）。"""
    os.makedirs(corpus_dir, exist_ok=True)
    for record in records:
        stamp = record.get("last_seen") or record.get("ts")
        dt = datetime.fromisoformat(stamp)
        path = os.path.join(corpus_dir, "%04d-%02d.jsonl" % (dt.year, dt.month))
        with open(path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _ranked_fixture(top=3):
    ranked = []
    for index in range(1, top + 1):
        ranked.append({
            "code": "L400%d" % index,
            "title": "第%d个坑" % index,
            "hits": 100 - index,
            "last_seen": "2026-11-09T10:00:0%d+08:00" % index,
            "example": "正确写法%d" % index,
        })
    return ranked


# ── rank_pitfalls：排序 / 聚合 / 截断 / 窗口 ────────────────────────

def test_rank_orders_by_hits_then_last_seen(tmp_path):
    recent = {"ts": _iso(1), "code": "L4001", "hits": 5, "message": "近期高频",
              "fixes": ["列表[0] = 10"]}
    older = {"ts": _iso(5), "code": "L4002", "hits": 5, "message": "同样 5 次但更早"}
    top_hits = {"ts": _iso(9), "code": "L4003", "hits": 9, "message": "最高频"}
    low = {"ts": _iso(2), "code": "L4004", "hits": 1, "message": "低频"}
    _write_lines(str(tmp_path), [recent, older, top_hits, low])

    ranked = error_stats.rank_pitfalls(corpus_dir=str(tmp_path))

    assert [item["code"] for item in ranked] == ["L4003", "L4001", "L4002", "L4004"]
    assert set(ranked[0]) == {"code", "title", "hits", "last_seen", "example"}
    assert ranked[0]["hits"] == 9
    assert ranked[0]["last_seen"] == top_hits["ts"]
    assert ranked[1]["example"] == "列表[0] = 10"
    assert ranked[0]["title"]  # title 永远非空（registry 缺失时退化为 code）


def test_rank_aggregates_hits_by_code_and_keeps_latest_example(tmp_path):
    first = {"ts": _iso(3), "code": "L4001", "hits": 2, "fixes": ["旧写法"]}
    second = {"ts": _iso(1), "code": "L4001", "hits": 3, "fixes": ["新写法"], "hint": "提示"}
    other = {"ts": _iso(2), "code": "L4002", "hits": 4, "fixes": ["另一条"]}
    _write_lines(str(tmp_path), [first, second, other])

    ranked = error_stats.rank_pitfalls(corpus_dir=str(tmp_path))

    assert [(item["code"], item["hits"]) for item in ranked] == [("L4001", 5), ("L4002", 4)]
    assert ranked[0]["last_seen"] == second["ts"]      # 最近一条决定 last_seen
    assert ranked[0]["example"] == "新写法"             # 最近一条的 fixes 优先


def test_rank_uses_hint_when_no_fixes_and_hits_default_one(tmp_path):
    record = {"ts": _iso(2), "code": "L3001", "hint": "先转换类型"}
    _write_lines(str(tmp_path), [record, {"ts": _iso(1), "code": "L3001"}])

    ranked = error_stats.rank_pitfalls(corpus_dir=str(tmp_path))

    assert len(ranked) == 1
    assert ranked[0]["hits"] == 2          # 缺 hits 的行按 1 计
    assert ranked[0]["example"] == "先转换类型"


def test_rank_top_truncates(tmp_path):
    records = [{"ts": _iso(index), "code": "L40%02d" % index, "hits": 20 - index}
               for index in range(1, 8)]
    _write_lines(str(tmp_path), records)

    ranked = error_stats.rank_pitfalls(corpus_dir=str(tmp_path), top=3)
    assert [item["code"] for item in ranked] == ["L4001", "L4002", "L4003"]
    assert len(error_stats.rank_pitfalls(corpus_dir=str(tmp_path), top=None)) == 7
    assert len(error_stats.rank_pitfalls(corpus_dir=str(tmp_path), top=0)) == 7


def test_rank_filters_by_window_days(tmp_path):
    recent = {"ts": _iso(3), "code": "L1001", "hits": 2}
    edge = {"ts": _iso(29), "code": "L1003", "hits": 1}
    stale = {"ts": _iso(45), "code": "L1002", "hits": 99}
    _write_lines(str(tmp_path), [recent, edge, stale])

    windowed = error_stats.rank_pitfalls(corpus_dir=str(tmp_path), window_days=30)
    assert [item["code"] for item in windowed] == ["L1001", "L1003"]

    widened = error_stats.rank_pitfalls(corpus_dir=str(tmp_path), window_days=90)
    assert [item["code"] for item in widened][0] == "L1002"   # 旧数据确实在文件里
    assert len(widened) == 3


# ── 坏数据 / 缺失：一律降级为空，不抛 ──────────────────────────────

def test_bad_lines_skipped_and_counted(tmp_path):
    corpus = str(tmp_path)
    os.makedirs(corpus, exist_ok=True)
    prefix = "L4001"
    lines = [
        "这不是 JSON",
        json.dumps({"ts": _iso(1), "message": "缺 code"}, ensure_ascii=False),
        "",
        json.dumps({"ts": _iso(2), "code": prefix, "hits": 2}, ensure_ascii=False),
        json.dumps({"ts": _iso(3), "code": "   ", "hits": 9}, ensure_ascii=False),
        json.dumps([1, 2, 3]),
    ]
    now = _now()
    path = os.path.join(corpus, "%04d-%02d.jsonl" % (now.year, now.month))
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")

    stats = {}
    ranked = error_stats.rank_pitfalls(corpus_dir=corpus, stats=stats)

    assert [item["code"] for item in ranked] == [prefix]
    assert ranked[0]["hits"] == 2
    assert stats["files_read"] == 1
    assert stats["lines_read"] == 5      # 空行不计
    assert stats["lines_skipped"] == 4   # 坏 JSON / 缺 code / 空白 code / 非对象


def test_missing_or_empty_corpus_returns_empty(tmp_path):
    assert error_stats.rank_pitfalls(corpus_dir=str(tmp_path / "不存在")) == []
    empty = tmp_path / "empty"
    empty.mkdir()
    assert error_stats.rank_pitfalls(corpus_dir=str(empty)) == []


def test_unreadable_corpus_file_degrades(tmp_path):
    corpus = tmp_path / "locked"
    corpus.mkdir()
    now = _now()
    path = corpus / ("%04d-%02d.jsonl" % (now.year, now.month))
    path.mkdir()  # 同名目录：open() 必然失败，验证不抛
    assert error_stats.rank_pitfalls(corpus_dir=str(corpus)) == []


def test_corpus_dir_env_override(monkeypatch, tmp_path):
    corpus = tmp_path / "env-corpus"
    _write_lines(str(corpus), [{"ts": _iso(1), "code": "L5001", "hits": 3}])
    monkeypatch.setenv("LIGHT_ERROR_CORPUS_DIR", str(corpus))

    assert [item["code"] for item in error_stats.rank_pitfalls()] == ["L5001"]
    # 显式 corpus_dir 优先于环境变量
    assert error_stats.rank_pitfalls(corpus_dir=str(tmp_path / "none")) == []


def test_title_degrades_to_code_when_registry_missing(tmp_path):
    _write_lines(str(tmp_path), [{"ts": _iso(1), "code": "L8888", "hits": 1}])
    item = error_stats.rank_pitfalls(corpus_dir=str(tmp_path))[0]

    assert item["title"]
    if error_stats._lookup_title(item["code"]) is None:
        assert item["title"] == item["code"]   # 不臆造标题


def test_non_utf8_bytes_do_not_crash(tmp_path):
    corpus = str(tmp_path)
    now = _now()
    path = os.path.join(corpus, "%04d-%02d.jsonl" % (now.year, now.month))
    with open(path, "wb") as handle:
        handle.write(b'\xff\xfe{"code": "L1", "hits": 3}\n')
        handle.write(json.dumps({"ts": _iso(1), "code": "L4001",
                                 "hits": 2}, ensure_ascii=False).encode("utf-8") + b"\n")

    stats = {}
    ranked = error_stats.rank_pitfalls(corpus_dir=corpus, stats=stats)

    assert [item["code"] for item in ranked] == ["L4001"]
    assert stats["lines_skipped"] == 1


def test_timestamp_formats_are_tolerated(tmp_path):
    utc = datetime.now(timezone.utc)
    local = datetime.now()
    records = [
        {"ts": utc.isoformat(timespec="seconds").replace("+00:00", "Z"), "code": "L1"},
        {"ts": local.strftime("%Y-%m-%dT%H:%M:%S"), "code": "L2"},
        {"ts": local.strftime("%Y-%m-%d"), "code": "L3"},
    ]
    _write_lines(str(tmp_path), records)

    ranked = error_stats.rank_pitfalls(corpus_dir=str(tmp_path))

    assert sorted(item["code"] for item in ranked) == ["L1", "L2", "L3"]
    assert {item["code"]: item["last_seen"] for item in ranked} == {
        record["code"]: record["ts"] for record in records}


# ── 卡片快照：无数据时逐字不变 ─────────────────────────────────────

def test_static_card_matches_baseline():
    assert syntax_card.generate_syntax_card() == _BASELINE_FULL
    assert syntax_card.generate_syntax_card(compact=True) == _BASELINE_COMPACT


def test_empty_ranked_is_byte_identical_to_baseline():
    assert syntax_card.generate_syntax_card(ranked=None) == _BASELINE_FULL
    assert syntax_card.generate_syntax_card(ranked=[]) == _BASELINE_FULL
    assert syntax_card.generate_syntax_card(ranked=[None, {}, ""]) == _BASELINE_FULL
    assert syntax_card.generate_syntax_card(compact=True, ranked=[]) == _BASELINE_COMPACT


# ── 卡片置顶区块：格式 / 位置 / 不破坏原有小节 ─────────────────────

_FULL_SECTIONS = [
    "一、变量与赋值",
    "二、段落（函数）",
    "三、条件",
    "四、循环",
    "五、运算符",
    "六、异常",
    "七、类",
    "八、导入导出",
    "九、特殊值",
    "十、内置类型",
    "十一、SRC后端可用内建函数",
    "十二、中文内建函数",
    "十三、核心规则",
]


def test_ranked_block_is_at_very_top_and_format_is_one_line_per_item():
    ranked = _ranked_fixture(top=3)

    card = syntax_card.generate_syntax_card(ranked=ranked)
    lines = card.splitlines()

    assert lines[0] == "## 最近 30 天最常踩的坑（TOP 3）"
    assert lines[1] == "1. [L4001] 第1个坑 —— 正确写法1"
    assert lines[2] == "2. [L4002] 第2个坑 —— 正确写法2"
    assert lines[3] == "3. [L4003] 第3个坑 —— 正确写法3"
    assert lines[4] == ""
    assert lines[5] == "【光明 v3.2 语法速查卡】"

    # 原有内容逐字保留，只是被前置
    assert card.endswith(_BASELINE_FULL)
    assert card.index("## 最近 30 天最常踩的坑") < card.index("【光明 v3.2 语法速查卡】")


def test_ranked_block_keeps_original_section_order():
    card = syntax_card.generate_syntax_card(ranked=_ranked_fixture(top=2))

    positions = [card.index(section) for section in _FULL_SECTIONS]
    assert positions == sorted(positions)
    assert card.index("## 最近 30 天最常踩的坑") == 0


def test_ranked_compact_card_also_gets_top_block():
    card = syntax_card.generate_syntax_card(
        compact=True, ranked=_ranked_fixture(top=2))

    assert card.startswith("## 最近 30 天最常踩的坑（TOP 2）\n")
    assert "1. [L4001] 第1个坑 —— 正确写法1" in card
    assert card.endswith(_BASELINE_COMPACT)


def test_ranked_item_without_example_has_no_dash():
    ranked = [{"code": "L255", "title": "变量名遮蔽内建", "hits": 4,
               "last_seen": "", "example": ""}]

    card = syntax_card.generate_syntax_card(compact=True, ranked=ranked)

    assert "1. [L255] 变量名遮蔽内建\n" in card
    assert " —— " not in card.splitlines()[1]


def test_ranked_example_is_flattened_to_single_line():
    ranked = [{"code": "L1", "title": "多行修法", "hits": 1,
               "last_seen": "", "example": "第一行\n  第二行"}]

    card = syntax_card.generate_syntax_card(compact=True, ranked=ranked)

    assert card.splitlines()[1] == "1. [L1] 多行修法 —— 第一行 第二行"


def test_ranked_composes_with_extra_sections():
    card = syntax_card.generate_syntax_card(
        include_verbs=True, include_pitfalls=True, ranked=_ranked_fixture(top=1))

    assert card.startswith("## 最近 30 天最常踩的坑（TOP 1）\n")
    assert card.count("【动词参数参照】") == 1
    assert card.count("【光明暗坑 — AI 生成时必须注意】") == 1
    assert card.index("【动词参数参照】") > card.index("十三、核心规则")


def test_rank_pitfalls_feeds_card_end_to_end(tmp_path):
    records = [
        {"ts": _iso(1), "code": "L4001", "hits": 7, "fixes": ["列表[0] = 10"]},
        {"ts": _iso(2), "code": "L4002", "hits": 3, "fixes": ["设 n 为 10"]},
        {"ts": _iso(3), "code": "L4003", "hits": 1, "fixes": ["遍历 i 于 1至10："]},
    ]
    _write_lines(str(tmp_path), records)

    ranked = error_stats.rank_pitfalls(corpus_dir=str(tmp_path), top=10)
    card = syntax_card.generate_syntax_card(compact=True, ranked=ranked)

    assert card.startswith("## 最近 30 天最常踩的坑（TOP 3）\n")
    assert "1. [L4001]" in card and "列表[0] = 10" in card
    assert card.endswith(_BASELINE_COMPACT)