# -*- coding: utf-8 -*-
"""
v4.0 → v5.x 代码迁移工具

将 v4.0 光明代码迁移到 v5.x 语法。
主要变更：
- 类型注解语法增强（支持泛型注解）
- 模块系统更新（导入语法增强）
- 新关键字引入（异步/等待/生成/类型等）
- 废弃旧 API 替换
- 接口语法增强
"""

import re
import os
from typing import Dict, List, Optional, Tuple
from pathlib import Path


class MigrationV40ToV50:
    """v4.0 → v5.x 代码迁移工具"""

    def __init__(self):
        # v5.x 新增关键字
        self.new_keywords = {
            '异步': '异步',
            '等待': '等待',
            '生成': '生成',
            '类型': '类型',
            '接口': '接口',
            '实现': '实现',
            '泛型': '泛型',
            '约束': '约束',
        }

        # 废弃的 v4.0 语法模式 → v5.x 语法
        self.deprecated_patterns = [
            (r'接收\s*:', '接收: → 使用括号参数语法'),
            (r'导入\s+(\S+)\s+as\s+(\S+)', '导入 x as y → 引 x 为 y'),
            (r'从\s+(\S+)\s+导入\s+(\S+)', '从 x 导入 y → 引 x 中 y'),
        ]

        # 需要保留的空格模式
        self._preserve_patterns = [
            (r'#.*$', r'#\g<0>'),
            (r'"[^"]*"', r'"\g<0>"'),
            (r"'[^']*'", r"'\g<0>'"),
        ]

    def migrate(self, source: str) -> str:
        """将 v4.0 代码迁移到 v5.x"""
        # 保护注释和字符串
        protected = {}
        counter = [0]

        def protect(match):
            counter[0] += 1
            key = f'__PROTECTED_{counter[0]}__'
            protected[key] = match.group(0)
            return key

        source = re.sub(r'#.*', protect, source)
        source = re.sub(r'"[^"]*"', protect, source)
        source = re.sub(r"'[^']*'", protect, source)

        # 执行迁移
        source = self._migrate_content(source)

        # 恢复保护内容
        for key, value in protected.items():
            source = source.replace(key, value)

        return source

    def migrate_file(self, file_path: str) -> str:
        """迁移文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        result = self.migrate(source)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(result)
        return result

    def migrate_directory(self, dir_path: str) -> Dict[str, str]:
        """迁移目录中的所有 .light 文件"""
        results = {}
        base = Path(dir_path)

        for f in base.rglob('*.light'):
            try:
                result = self.migrate_file(str(f))
                results[str(f)] = result
            except Exception as e:
                results[str(f)] = f'错误: {e}'

        return results

    def preview_changes(self, source: str) -> List[Dict]:
        """预览需要修改的地方"""
        changes = []

        for i, line in enumerate(source.split('\n'), 1):
            # 检查废弃模式
            for pattern, description in self.deprecated_patterns:
                if re.search(pattern, line):
                    changes.append({
                        'line': i,
                        'type': '废弃语法',
                        'description': description,
                        'content': line.strip(),
                    })

            # 检查旧的导入语法
            if re.match(r'导入\s+', line):
                changes.append({
                    'line': i,
                    'type': '导入语法',
                    'description': '「导入」→「引」',
                    'content': line.strip(),
                })

            # 检查缺少类型注解的函数
            func_match = re.match(r'(?:段|函)\s+\S+\s*\(([^)]*)\)', line)
            if func_match:
                params_str = func_match.group(1)
                if params_str.strip():
                    params = [p.strip() for p in params_str.split(',') if p.strip()]
                    for param in params:
                        if ':' not in param and '为' not in param:
                            changes.append({
                                'line': i,
                                'type': '类型注解建议',
                                'description': f'建议为参数「{param}」添加类型注解',
                                'content': line.strip(),
                            })
                            break

            # 检查无类型注解的返回
            if re.match(r'(?:段|函)\s+\S+\s*\([^)]*\)\s*[：:]?\s*$', line):
                changes.append({
                    'line': i,
                    'type': '返回类型注解',
                    'description': '建议为函数添加返回类型注解: 段 名() -> 类型',
                    'content': line.strip(),
                })

            # 检查旧式注释格式
            if '#' in line and line.strip().startswith('#'):
                if re.match(r'^#\s*[A-Z][a-z]+:', line):
                    changes.append({
                        'line': i,
                        'type': '注释格式',
                        'description': '使用 v5.x 推荐注释格式: # 标题 → ## 标题',
                        'content': line.strip(),
                    })

        # 去重
        seen = set()
        unique_changes = []
        for c in changes:
            key = (c['line'], c['type'])
            if key not in seen:
                seen.add(key)
                unique_changes.append(c)

        return unique_changes

    def report(self, changes: List[Dict]) -> str:
        """生成迁移报告"""
        if not changes:
            return "无需修改，代码已兼容 v5.x 语法。\n"

        lines = []
        lines.append("=" * 60)
        lines.append("v4.0 → v5.x 代码迁移报告")
        lines.append("=" * 60)
        lines.append(f"总计 {len(changes)} 处建议修改\n")

        type_counts: Dict[str, int] = {}
        for c in changes:
            t = c['type']
            type_counts[t] = type_counts.get(t, 0) + 1

        lines.append("修改类型统计:")
        for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {t}: {count} 处")
        lines.append("")

        lines.append("详细修改列表:")
        for c in changes:
            lines.append(f"  L{c['line']:4d} [{c['type']}] {c['description']}")
            lines.append(f"        源: {c['content'][:60]}")

        lines.append("=" * 60)
        lines.append("注意: v4.0 → v5.x 迁移主要是新增功能，")
        lines.append("现有 v4.0 代码在 v5.x 中仍可正常使用。")
        lines.append("=" * 60)
        return '\n'.join(lines)

    # ------------------------------------------------------------------
    # 内部迁移方法
    # ------------------------------------------------------------------

    def _migrate_content(self, source: str) -> str:
        """执行具体的迁移转换"""
        # 1. 迁移 import 语法
        # 导入 x as y → 引 x 为 y
        source = re.sub(
            r'导入\s+(\S+)\s+as\s+(\S+)',
            r'引 \1 为 \2',
            source
        )
        # 从 x 导入 y → 引 x 中 y
        source = re.sub(
            r'从\s+(\S+)\s+导入\s+(\S+)',
            r'引 \1 中 \2',
            source
        )
        # 简单 导入 x → 引 x
        source = re.sub(
            r'导入\s+',
            '引 ',
            source
        )

        # 2. 导出语法迁移
        source = re.sub(
            r'导出\s+',
            '出 ',
            source
        )

        # 3. 接收语法迁移（如果还有残留）
        source = re.sub(
            r'(?:段|函|段落|函数)\s+(\S+)\s+接收\s+',
            lambda m: f'段 {m.group(1)}(',
            source
        )

        # 4. 添加返回类型注解标记（提示性）
        # 段 名(参数) → 段 名(参数) -> 类型（仅在注释中提示）
        source = re.sub(
            r'(段|函)\s+(\S+)\s*\(([^)]*)\)\s*[：:]?\s*$',
            lambda m: f'{m.group(1)} {m.group(2)}({m.group(3)}) -> 类型',
            source
        )

        # 5. 类型注解增强（: 类型 → : 类型 的泛型语法）
        # 简单类型注解不变，复杂类型需要转换
        source = re.sub(
            r'列表\[(\S+)\]',
            r'列表<\1>',
            source
        )
        source = re.sub(
            r'映射\[(\S+),\s*(\S+)\]',
            r'映射<\1, \2>',
            source
        )

        # 6. 匹配语法增强
        source = re.sub(
            r'情况\s+(\S+)\s*[：:]',
            lambda m: f'情况 {m.group(1)}：',
            source
        )

        # 7. 异步语法转换
        # 异步 段 名() → 异步 段 名()
        # 已经是 v5.x 语法，保持不变

        return source