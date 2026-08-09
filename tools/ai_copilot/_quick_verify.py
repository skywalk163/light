#!/usr/bin/env python3
"""快速验证 - 解析+执行+对比，带超时保护"""
import json, sys, os, io, re
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src'))
from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator

DATASET_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sft_dataset.jsonl')

items = []
with open(DATASET_PATH, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line:
            items.append(json.loads(line))

parser = LightParser()
gen = PythonCodeGenerator()

parse_fails = []
exec_fails = []
mismatches = []
pass_count = 0

# 跳过带input()或大循环的
skip_set = set()
for idx, item in enumerate(items):
    py = item.get('input', '').replace('\\n', '\n')
    if 'input(' in py:
        skip_set.add(idx)
    large = re.findall(r'range\s*\(\s*(\d{6,})\s*\)', py)
    if large:
        skip_set.add(idx)
    large = re.findall(r'range\s*\([^,]+,\s*(\d{6,})\s*\)', py)
    if large:
        skip_set.add(idx)

print(f"Skip set: {len(skip_set)} entries")

for idx, item in enumerate(items):
    py = item.get('input', '').replace('\\n', '\n')
    du = item.get('output', '').replace('\\n', '\n')
    
    if idx in skip_set:
        continue
    
    # Parse
    try:
        module = parser.parse(du)
        py_code = gen.generate(module)
    except Exception as e:
        parse_fails.append((idx, str(e)[:100]))
        if len(parse_fails) <= 20:
            print(f"  [{idx}] parse_fail: {str(e)[:100]}", flush=True)
        continue
    
    # Exec Python
    try:
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        exec(py, {})
        py_out = sys.stdout.getvalue().strip()
        sys.stdout = old_stdout
    except Exception as e:
        sys.stdout = old_stdout
        exec_fails.append((idx, 'py', str(e)[:100]))
        if len(exec_fails) <= 10:
            print(f"  [{idx}] py_exec_fail: {str(e)[:100]}", flush=True)
        continue
    
    # Exec Light
    try:
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        exec(py_code, {})
        du_out = sys.stdout.getvalue().strip()
        sys.stdout = old_stdout
    except Exception as e:
        sys.stdout = old_stdout
        exec_fails.append((idx, 'du', str(e)[:100]))
        if len(exec_fails) <= 10:
            print(f"  [{idx}] du_exec_fail: {str(e)[:100]}", flush=True)
        continue
    
    if py_out == du_out:
        pass_count += 1
    else:
        mismatches.append((idx, py_out[:60], du_out[:60]))
        if len(mismatches) <= 20:
            print(f"  [{idx}] mismatch: py={repr(py_out)[:50]} du={repr(du_out)[:50]}", flush=True)
    
    if (idx + 1) % 200 == 0:
        print(f"  --- 进度: {idx+1}/{len(items)} (PASS={pass_count}) ---", flush=True)

total = len(items) - len(skip_set)
print(f"\n{'='*60}")
print(f"Parse fails: {len(parse_fails)}")
print(f"Exec fails: {len(exec_fails)}")
print(f"Mismatches: {len(mismatches)}")
print(f"Pass: {pass_count}/{total} = {pass_count/total*100:.1f}%")

# 详细错误分类
print(f"\n=== Parse Failures ===")
for idx, err in parse_fails:
    print(f"  [{idx}] {err}")

print(f"\n=== Exec Failures ===")
err_counter = Counter()
for idx, typ, err in exec_fails:
    err_counter[f'{typ}: {err[:80]}'] += 1
for k, v in err_counter.most_common(30):
    print(f"  [{v}x] {k}")

print(f"\n=== Mismatch Samples ===")
for idx, py_out, du_out in mismatches[:30]:
    print(f"  [{idx}] py={repr(py_out)[:50]} du={repr(du_out)[:50]}")

# 保存结果
result = {
    'pass_count': pass_count,
    'total': total,
    'rate': round(pass_count/total*100, 1),
    'parse_fails': parse_fails,
    'exec_fails': [(idx, typ, err) for idx, typ, err in exec_fails],
    'mismatches': [(idx, py, du) for idx, py, du in mismatches],
    'skip_set': list(skip_set)
}
out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_quick_verify_results.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"\nResults saved to {out_path}")