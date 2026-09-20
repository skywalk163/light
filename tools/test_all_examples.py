#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试所有 103 个示例，确保它们都能编译运行
"""

import json
import subprocess
from pathlib import Path

# 读取数据集
with open('docs/dataset_deepseek_r1_100_examples_final.jsonl', 'r', encoding='utf-8') as f:
    lines = [line.strip() for line in f if line.strip()]

print(f"读取到 {len(lines)} 条数据，开始测试...\n")

# 测试统计
total = len(lines)
success = 0
failed = 0
failed_examples = []

for idx, line in enumerate(lines):
    try:
        example_data = json.loads(line)
        task = example_data['instruction']
        code = example_data['response']

        # 保存代码到临时文件
        temp_file = Path(f"temp_test_{idx}.light")
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(code)

        # 尝试编译并运行
        result = subprocess.run(
            ['python3', 'cli/lightc.py', '--run', str(temp_file)],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            success += 1
            if (idx + 1) % 20 == 0:
                print(f"✅ 测试 {idx + 1}/{total} 成功")
        else:
            failed += 1
            failed_examples.append({
                'index': idx + 1,
                'task': task,
                'error': result.stderr
            })
            print(f"❌ 测试 {idx + 1}/{total} 失败")
            print(f"   任务：{task[:60]}...")
            print(f"   错误：{result.stderr[:100]}...")

    except subprocess.TimeoutExpired:
        failed += 1
        failed_examples.append({
            'index': idx + 1,
            'task': task,
            'error': '超时'
        })
        print(f"❌ 测试 {idx + 1}/{total} 超时")
    except Exception as e:
        failed += 1
        failed_examples.append({
            'index': idx + 1,
            'task': task,
            'error': str(e)
        })
        print(f"❌ 测试 {idx + 1}/{total} 异常：{e}")

    finally:
        # 清理临时文件
        if temp_file.exists():
            temp_file.unlink()

# 打印测试结果
print(f"\n{'='*70}")
print("测试完成！")
print(f"{'='*70}")
print(f"总测试数：{total}")
print(f"成功：{success} ({success/total*100:.1f}%)")
print(f"失败：{failed} ({failed/total*100:.1f}%)")

# 保存失败示例
if failed > 0:
    print(f"\n失败示例详情：")
    for ex in failed_examples:
        print(f"\n--- 示例 {ex['index']} ---")
        print(f"任务：{ex['task'][:80]}...")
        print(f"错误：{ex['error']}")

    # 保存到文件
    with open('docs/test_failed_examples.json', 'w', encoding='utf-8') as f:
        json.dump(failed_examples, f, ensure_ascii=False, indent=2)
    print(f"\n失败示例已保存到 docs/test_failed_examples.json")
else:
    print("\n🎉 所有示例测试通过！")
