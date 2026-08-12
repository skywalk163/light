# -*- coding: utf-8 -*-
"""快速批量语法扫描：对首批 5 个领域的所有 .light 文件直接调用 LightParser 做语法检查。

问题分类：
  - SyntaxError:    解析失败（parser 抛出 ParseError 或返回 None）
  - SelfRecursive:  函数体调用了自身（如 `返回 函数名(输入)`）
  - WrongVariable:  参数名为 `输入` 但函数体内使用了 `列表` 或 `值`
  - StubBlock:      函数体只有一行，且仅调用了另一个函数（无实际运算逻辑）
"""

import os
import re
import sys
import time
import traceback

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.normpath(os.path.join(_HERE, '..'))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, 'src'))

from light_parser_v3 import LightParser, ParseError

# 首批扫描的 5 个领域（可通过 --领域 参数覆盖）
TARGET_DOMAINS = ['数据', '数学', '统计', '排序', '搜索']

# 积木库根目录：优先 blocks_v5，回退到积木库本身
BLOCKS_DIR = os.path.join(_HERE, 'blocks_v5')
if not os.path.isdir(BLOCKS_DIR):
    BLOCKS_DIR = _HERE


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _extract_export_name(source: str) -> str | None:
    """从源码中提取导出名（`导出 XXX`）"""
    m = re.search(r'^(?:导出|导出)\s+(\S+)', source, re.MULTILINE)
    return m.group(1) if m else None


def _extract_paragraph_name(source: str) -> str | None:
    """从源码中提取段落/函数名（`段落 XXX 接收` / `函数 XXX 接收`）"""
    m = re.search(r'^(?:段落|函数|段)\s+(\S+)\s+接收', source, re.MULTILINE)
    return m.group(1) if m else None


def _extract_params(source: str) -> list[str] | None:
    """从源码中提取参数列表（`段落 XXX 接收 甲, 乙：` → ['甲', '乙']）"""
    m = re.search(r'^(?:段落|函数|段)\s+\S+\s+接收\s+(.+?)[：:]', source, re.MULTILINE)
    if m:
        raw = m.group(1)
        return [p.strip() for p in raw.split(',')]
    return None


def _get_body_lines(source: str) -> list[str]:
    """提取函数体语句行（去掉注释、导出行、段落定义行和空行）。"""
    lines = source.split('\n')
    body = []
    for line in lines:
        s = line.strip()
        if not s or s.startswith('#'):
            continue
        if s.startswith('导出') or s.startswith('导出'):
            continue
        if re.match(r'^(段落|函数|段)\s+', s):
            continue
        body.append(s)
    return body


def _is_simple_call(line: str) -> bool:
    """判断一行是否仅为简单函数调用（无运算/控制流关键字）。"""
    # 移除开头的 "返回 "
    call = re.sub(r'^返回\s+', '', line).strip()
    if not call:
        return False
    # 包含运算/控制流关键字 → 不是简单调用
    if re.search(r'[+\-*/]|\b加\b|\b减\b|\b乘\b|\b除\b|\b设\b|\b当\b|\b如果\b|\b遍历\b|\b且\b|\b或\b', call):
        return False
    # 必须是函数调用形式：XXX(...) 或 XXX YYY(...)
    if re.search(r'\w+\s*\(', call):
        return True
    return False


# ---------------------------------------------------------------------------
# 分析函数
# ---------------------------------------------------------------------------

def analyze_file(filepath: str) -> list[tuple[str, str]]:
    """分析单个 .light 文件，返回 [(问题类型, 详情), ...]。"""
    issues: list[tuple[str, str]] = []

    # ---- 读取文件 ----
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
    except Exception as e:
        return [('SyntaxError', f'读取文件失败: {e}')]

    if not source.strip():
        return [('SyntaxError', '空文件')]

    # ---- 语法检查 ----
    parser = LightParser()
    try:
        module = parser.parse(source)
        if module is None:
            issues.append(('SyntaxError', 'parser 返回 None'))
            # 尝试取 errors 属性（部分版本可能有）
            errs = getattr(parser, 'errors', None)
            if errs:
                issues[0] = ('SyntaxError', '; '.join(errs) if isinstance(errs, list) else str(errs))
            return issues
    except ParseError as e:
        # 取简短错误信息（去掉 ParseError 的格式化边框）
        brief = str(e).split('└─')[0].strip() if '└─' in str(e) else str(e)
        issues.append(('SyntaxError', brief[:200]))
        return issues
    except Exception as e:
        issues.append(('SyntaxError', f'{type(e).__name__}: {e}'))
        return issues

    # ---- 提取元信息 ----
    func_name = _extract_export_name(source) or _extract_paragraph_name(source)
    params = _extract_params(source)
    param_names = set(params) if params else set()
    body_lines = _get_body_lines(source)
    body_text = ' '.join(body_lines)

    # ---- 检查 SelfRecursive ----
    if func_name:
        # 匹配 func_name(...) 以及 func_name XXX(...) 形式
        pattern = re.escape(func_name) + r'\s*\('
        if re.search(pattern, body_text):
            # 找到具体行
            for bl in body_lines:
                if re.search(pattern, bl):
                    issues.append(('SelfRecursive', f'函数体调用自身: {bl[:100]}'))
                    break

    # ---- 检查 WrongVariable ----
    # 参数名只有 "输入" 一个时，检查函数体是否使用了 "列表" 或 "值"
    if params and len(params) == 1 and params[0] == '输入':
        for wrong_var in ('列表', '值'):
            # 用单词边界匹配，避免匹配到 "列表2" 等
            if re.search(r'(?<!\w)' + re.escape(wrong_var) + r'(?!\w)', body_text):
                issues.append(('WrongVariable',
                               f'参数为"输入"但函数体使用了"{wrong_var}"'))
                break  # 一个文件最多报一次该类型

    # ---- 检查 StubBlock ----
    if len(body_lines) == 1 and not issues:
        line = body_lines[0]
        if _is_simple_call(line):
            # 排除自身调用（已被 SelfRecursive 捕获）
            if func_name:
                call_pattern = re.escape(func_name) + r'\s*\('
                if not re.search(call_pattern, line):
                    issues.append(('StubBlock', f'仅一行调用: {line[:100]}'))
            else:
                issues.append(('StubBlock', f'仅一行调用: {line[:100]}'))

    return issues


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description='积木质量扫描')
    parser.add_argument('--领域', nargs='*', help='目标领域列表（默认: 数据 数学 统计 排序 搜索）')
    args = parser.parse_args()
    
    global TARGET_DOMAINS
    if args.领域:
        TARGET_DOMAINS = args.领域
    
    start = time.time()

    print(f'积木库根目录: {BLOCKS_DIR}')
    print(f'目标领域: {", ".join(TARGET_DOMAINS)}')
    print()

    # 各领域统计
    domain_total: dict[str, int] = {}
    domain_issue_files: dict[str, int] = {}
    # 所有问题详情
    all_issues: dict[str, dict[str, list[tuple[str, str]]]] = {}
    # 问题类型计数
    type_counts: dict[str, int] = {}
    type_file_refs: dict[str, list[str]] = {}

    for domain in TARGET_DOMAINS:
        domain_dir = os.path.join(BLOCKS_DIR, domain)
        if not os.path.isdir(domain_dir):
            print(f'  ⚠ 领域目录不存在: {domain_dir}')
            domain_total[domain] = 0
            domain_issue_files[domain] = 0
            all_issues[domain] = {}
            continue

        light_files = sorted([
            f for f in os.listdir(domain_dir)
            if f.endswith('.light')
        ])
        domain_total[domain] = len(light_files)
        domain_issue_files[domain] = 0
        all_issues[domain] = {}

        for fname in light_files:
            fpath = os.path.join(domain_dir, fname)
            issues = analyze_file(fpath)
            if issues:
                domain_issue_files[domain] += 1
                all_issues[domain][fname] = issues
                seen_types = set()
                for typ, detail in issues:
                    if typ not in seen_types:
                        type_counts[typ] = type_counts.get(typ, 0) + 1
                        seen_types.add(typ)
                    type_file_refs.setdefault(typ, [])
                    type_file_refs[typ].append(f'{domain}/{fname}: {detail[:80]}')

    elapsed = time.time() - start
    total_files = sum(domain_total.values())
    total_issue_files = sum(domain_issue_files.values())

    # ================================================================
    # 输出到 stdout
    # ================================================================
    print('=' * 60)
    print('  积木质量扫描报告')
    print('=' * 60)
    print()
    print(f'  扫描领域: {", ".join(TARGET_DOMAINS)}')
    print(f'  总文件数: {total_files}')
    print(f'  有问题的文件: {total_issue_files}')
    print(f'  扫描耗时: {elapsed:.2f}s')
    print()

    print('--- 各领域统计 ---')
    for domain in TARGET_DOMAINS:
        t = domain_total.get(domain, 0)
        b = domain_issue_files.get(domain, 0)
        status = '✅' if b == 0 else '⚠️'
        print(f'  {status} {domain}: {t} 文件, {b} 有问题')
    print()

    # 按数量降序排列问题类型
    sorted_types = sorted(type_counts.items(), key=lambda x: -x[1])
    print('--- 问题分类统计 ---')
    for typ, cnt in sorted_types:
        print(f'  [{cnt}] {typ}')
    if not sorted_types:
        print('  (无问题)')
    print()

    print('--- 问题详情 ---')
    for typ, cnt in sorted_types:
        refs = type_file_refs.get(typ, [])
        print(f'\n  ▸ {typ} ({cnt} 处)')
        for ref in refs[:10]:
            print(f'    - {ref}')
        if len(refs) > 10:
            print(f'    ... 还有 {len(refs) - 10} 个')
    if not sorted_types:
        print('  (无问题)')

    # ================================================================
    # 保存到 _质量报告.md
    # ================================================================
    report_path = os.path.join(_HERE, '_质量报告.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('# 积木质量扫描报告\n\n')
        f.write(f'- **扫描时间**: {time.strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write(f'- **积木库根目录**: {BLOCKS_DIR}\n')
        f.write(f'- **扫描领域**: {", ".join(TARGET_DOMAINS)}\n')
        f.write(f'- **总文件数**: {total_files}\n')
        f.write(f'- **有问题的文件**: {total_issue_files}\n')
        f.write(f'- **扫描耗时**: {elapsed:.2f}s\n\n')

        f.write('## 各领域统计\n\n')
        f.write('| 领域 | 文件数 | 有问题 | 状态 |\n')
        f.write('|------|--------|--------|------|\n')
        for domain in TARGET_DOMAINS:
            t = domain_total.get(domain, 0)
            b = domain_issue_files.get(domain, 0)
            status = '✅' if b == 0 else '⚠️'
            f.write(f'| {domain} | {t} | {b} | {status} |\n')

        f.write('\n## 问题分类统计\n\n')
        if sorted_types:
            f.write('| 问题类型 | 数量 |\n')
            f.write('|----------|------|\n')
            for typ, cnt in sorted_types:
                f.write(f'| {typ} | {cnt} |\n')
        else:
            f.write('无问题。\n')

        f.write('\n## 问题详情\n\n')
        for typ, cnt in sorted_types:
            f.write(f'### {typ}（{cnt} 处）\n\n')
            for ref in type_file_refs.get(typ, []):
                f.write(f'- {ref}\n')
            f.write('\n')
        if not sorted_types:
            f.write('无问题。\n')

    print(f'\n报告已保存: {report_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())