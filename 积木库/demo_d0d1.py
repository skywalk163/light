# -*- coding: utf-8 -*-
"""
光明磊落系统 · D0+D1 积木选块 Demo
====================================
可独立运行，展示 1048 块积木库的选块能力。

流程:
  1. 用户输入需求（如"把列表求和"）
  2. D0（关键词选块）快速匹配
  3. 若置信度不足，D1（Tfidf-ngram）补充召回
  4. 输出候选积木及选块路径

用法:
  python demo_d0d1.py                          # 交互模式
  python demo_d0d1.py "对列表求和"              # 单次查询
  python demo_d0d1.py --batch                   # 批量运行预设用例
"""

import sys, os, time, json, argparse

_HERE = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, _HERE)

# ──────────────────────────────────────────────────────
# 导入选块器
# ──────────────────────────────────────────────────────
from 选块 import select_blocks as 关键词选块, load_index
from _ml_selector import 分类_需求领域, 补充_选块, tfidf_选块
from _ml_selector import _块列表 as _tfidf_块列表

索引 = load_index()
print(f"光明积木库 v{索引.get('版本', '?')} 已加载，共 {len(索引['块'])} 块积木")


# ──────────────────────────────────────────────────────
# D0+D1 统一选块
# ──────────────────────────────────────────────────────
def 选块(需求, top=3, 详细=False):
    """D0 关键词选块 + D1 Tfidf 补充

    参数:
        需求: 自然语言描述
        top: 返回候选数
        详细: 是否输出选块路径

    返回:
        (候选列表, 选块路径描述)
    """
    t0 = time.perf_counter()
    路径 = []

    # Step 1: D5 领域分类（仅用于信息）
    try:
        类别, 置信度 = 分类_需求领域(需求)
        类型标签 = "搭积木" if 类别 == 1 else "写代码"
        路径.append(f"[D5] 需求分类: {类型标签} (置信度 {置信度:.2f})")
    except Exception as e:
        路径.append(f"[D5] 跳过: {e}")

    # Step 2: D0 关键词选块
    t1 = time.perf_counter()
    候选 = 关键词选块(需求, 索引, top=top)
    t2 = time.perf_counter()
    路径.append(f"[D0] 关键词选块: {len(候选)} 候选 ({((t2-t1)*1000):.1f}ms)")

    # Step 3: D1 Tfidf 补充（如果 top-1 分数低于阈值）
    需要补充 = False
    if 候选:
        top1_分数 = 候选[0].get('分数', 0)
        if top1_分数 < 5.0:
            需要补充 = True
            路径.append(f"[D1] 置信度不足 ({top1_分数:.1f} < 5.0)，启动 Tfidf 补充")
            t3 = time.perf_counter()
            候选 = 补充_选块(需求, 候选, top=top+2)
            t4 = time.perf_counter()
            路径.append(f"[D1] Tfidf 补充完成: {len(候选)} 候选 ({((t4-t3)*1000):.1f}ms)")

    if not 需要补充 and 候选:
        路径.append(f"[D1] 跳过 (Top-1 分数 {候选[0].get('分数', 0):.1f} >= 5.0，无需补充)")

    if not 候选:
        路径.append("[D0+D1] 无候选 -> 建议走兜底生成器")

    total_ms = (time.perf_counter() - t0) * 1000
    路径.append(f"总耗时: {total_ms:.1f}ms")

    return 候选[:top], 路径


# ──────────────────────────────────────────────────────
# 格式化输出
# ──────────────────────────────────────────────────────
def 格式化_结果(候选, 路径):
    """将结果格式化为可读字符串"""
    lines = []
    lines.append("-" * 60)
    lines.append(f"选块路径:")
    for p in 路径:
        lines.append(f"  {p}")
    lines.append("-" * 60)
    if 候选:
        lines.append(f"候选积木 (Top-{len(候选)}):")
        for i, c in enumerate(候选, 1):
            分数 = c.get('分数', 'N/A')
            if isinstance(分数, float):
                分数 = f"{分数:.2f}"
            lines.append(f"  {i}. [{c['领域']}] {c['名称']:20s} 分数={分数}")
            lines.append(f"     → {c['描述']}")
    else:
        lines.append("  无候选积木匹配当前需求")
    lines.append("-" * 60)
    return "\n".join(lines)


# ──────────────────────────────────────────────────────
# 交互模式
# ──────────────────────────────────────────────────────
def 交互模式():
    print("\n" + "=" * 60)
    print("光明磊落 · D0+D1 积木选块 Demo (交互模式)")
    print("=" * 60)
    print("输入需求描述，或输入以下命令:")
    print("  /stats  - 查看积木库统计")
    print("  /find   - 查找积木")
    print("  /quit   - 退出")
    print("=" * 60)

    while True:
        try:
            需求 = input("\n需求 > ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not 需求:
            continue
        if 需求 == '/quit':
            break
        if 需求 == '/stats':
            from collections import Counter
            领域计数 = Counter(b['领域'] for b in 索引['块'])
            print(f"\n积木库统计 ({len(索引['块'])} 块):")
            for 领域, 计数 in 领域计数.most_common():
                print(f"  {领域}: {计数}")
            continue
        if 需求 == '/find':
            名称 = input("查找积木名 > ").strip()
            if 名称:
                for b in 索引['块']:
                    if 名称 in b['名称']:
                        print(f"  [{b['领域']}] {b['名称']:25s} {b['描述']}")
            continue

        候选, 路径 = 选块(需求, top=3)
        print(格式化_结果(候选, 路径))


# ──────────────────────────────────────────────────────
# 批量测试模式
# ──────────────────────────────────────────────────────
预设用例 = [
    # (需求, 期望说明)
    ("对列表求和", "数据领域聚合"),
    ("计算列表平均值", "数据领域统计"),
    ("去掉字符串首尾空格", "文本处理"),
    ("摄氏度转华氏度", "单位换算"),
    ("计算两个数的乘积", "数学运算"),
    ("Base64编码", "编码转换"),
    ("验证邮箱格式", "数据验证"),
    ("计算圆面积", "几何计算"),
    ("逻辑与运算", "逻辑运算"),
    ("生成随机范围", "随机数"),
    ("中文数字转大写", "中文处理"),
    ("计算毛利率", "财务计算"),
    ("秒转分钟", "时间转换"),
    ("对列表元素排序", "数据操作"),
    ("求列表最大值", "数据统计"),
    ("统计文本长度", "文本处理"),
    ("四舍五入到整数", "数学运算"),
    ("反转列表顺序", "数据操作"),
    ("去掉列表重复元素", "数据操作"),
    ("计算复利", "财务计算"),
]


def 批量模式():
    print("\n" + "=" * 60)
    print("光明磊落 · D0+D1 批量测试")
    print("=" * 60)
    print(f"测试用例: {len(预设用例)} 条")
    print()

    正确_top1 = 0
    正确_top3 = 0
    总耗时 = 0.0

    for 需求, 说明 in 预设用例:
        候选, 路径 = 选块(需求, top=3)
        总耗时 += float(路径[-1].replace('总耗时: ', '').replace('ms', ''))

    # 重新运行以获取精度
    print(f"{'需求':<22} {'Top-1':<18} {'耗时':<10}")
    print("-" * 55)
    for 需求, 说明 in 预设用例:
        候选, 路径 = 选块(需求, top=3)
        top1 = 候选[0]['名称'] if 候选 else "无"
        top3 = ", ".join(c['名称'] for c in 候选) if 候选 else "无"
        ms = 路径[-1].replace('总耗时: ', '').replace('ms', '')
        print(f"{需求:<22} {top1:<18} {ms:<10}")

    print("-" * 55)
    print(f"共 {len(预设用例)} 条用例")


# ──────────────────────────────────────────────────────
# 单次查询模式
# ──────────────────────────────────────────────────────
def 单次模式(需求):
    候选, 路径 = 选块(需求, top=3, 详细=True)
    print(格式化_结果(候选, 路径))


# ──────────────────────────────────────────────────────
# 入口
# ──────────────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='光明磊落 D0+D1 选块 Demo')
    parser.add_argument('需求', nargs='?', default=None, help='查询需求')
    parser.add_argument('--batch', action='store_true', help='批量运行预设用例')
    args = parser.parse_args()

    if args.batch:
        批量模式()
    elif args.需求:
        单次模式(args.需求)
    else:
        交互模式()