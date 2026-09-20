#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试从数据集中随机选择的例子
"""

import json
import subprocess
import sys
from pathlib import Path

# 从数据集中随机选择5个例子
with open('docs/dataset_deepseek_r1_100_examples_fixed.jsonl', 'r', encoding='utf-8') as f:
    lines = [line.strip() for line in f if line.strip()]

# 选择5个示例并解析JSON
examples_to_test = []
for idx in [81, 14, 3, 94, 35]:
    try:
        example_data = json.loads(lines[idx])
        examples_to_test.append(example_data)
    except Exception as e:
        print(f"❌ 解析示例 {idx} 失败：{e}")

def test_example(example_data, index):
    """测试单个示例"""
    print(f"\n{'='*70}")
    print(f"测试示例 {index + 1}")
    print(f"{'='*70}")
    print(f"任务：{example_data['instruction']}")
    print(f"\n代码：")
    print(example_data['response'])

    # 保存代码到临时文件
    temp_file = Path(f"temp_test_{index}.light")
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(example_data['response'])

    # 尝试编译
    print(f"\n--- 尝试编译 ---")
    try:
        result = subprocess.run(
            ['python3', 'cli/lightc.py', '--run', str(temp_file)],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print("✅ 编译并运行成功！")
            if result.stdout:
                print(f"输出：\n{result.stdout}")
        else:
            print(f"❌ 编译/运行失败！")
            print(f"错误信息：\n{result.stderr}")

    except subprocess.TimeoutExpired:
        print("❌ 编译/运行超时")
    except Exception as e:
        print(f"❌ 编译/运行失败：{e}")

    finally:
        # 清理临时文件
        if temp_file.exists():
            temp_file.unlink()

    print(f"\n{'-'*70}\n")

def main():
    """主函数"""
    print("开始测试从数据集中随机选择的例子...")

    for idx, example_data in enumerate(examples_to_test):
        test_example(example_data, idx)

    print(f"\n{'='*70}")
    print("测试完成！")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
