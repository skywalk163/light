# -*- coding: utf-8 -*-
"""
v3.3 → v4.0 代码迁移工具

将 v3.3 光明代码迁移到 v4.0 语法。
主要变更：
- 关键字映射（如果→若，那么→则，否则→否 等）
- 语法结构调整
- 废弃 API 替换
"""

import re
import os
from typing import Dict, List, Optional, Tuple
from pathlib import Path


class MigrationV33ToV40:
    """v3.3 → v4.0 代码迁移工具"""

    def __init__(self):
        # 语法映射表
        self.keyword_map = {
            '如果': '若', '那么': '则', '否则': '否',
            '否则如果': '或若', '当': '当', '遍历': '历',
            '函数': '函', '段落': '段', '返回': '还',
            '类': '类', '继承': '承', '实现': '现',
            '打印': '印', '输出': '写', '输入': '读',
            '导入': '引', '导出': '出',
            '真': '真', '假': '假', '空': '空',
            '定义': '设', '等于': '为',
            '尝试': '试', '捕获': '捕', '抛出': '抛',
            '最终': '终', '匹配': '配',
        }

        # 仅用于 L1→L0 转换的映射
        self.l1_to_l0 = {
            '如果': '若', '否则': '否', '否则如果': '或若',
            '遍历': '遍', '返回': '返', '跳出': '跳', '跳过': '过',
            '定义': '设', '段落': '段', '函数': '函',
            '继承': '承', '接口': '接', '实现': '现',
            '尝试': '试', '捕获': '捕', '抛出': '抛', '最终': '终',
            '导入': '导', '导出': '出', '匹配': '配',
            '打印': '印', '输出': '写', '输入': '读',
        }

        # 需要保留的空格模式
        self._preserve_patterns = [
            (r'#.*$', r'#\g<0>'),  # 注释
            (r'"[^"]*"', r'"\g<0>"'),  # 双引号字符串
            (r"'[^']*'", r"'\g<0>'"),  # 单引号字符串
        ]

    def migrate(self, source: str) -> str:
        """将 v3.3 代码迁移到 v4.0"""
        # 先提取字符串和注释，保护它们不被替换
        protected = {}
        counter = [0]

        def protect(match):
            counter[0] += 1
            key = f'__PROTECTED_{counter[0]}__'
            protected[key] = match.group(0)
            return key

        # 保护注释
        source = re.sub(r'#.*', protect, source)
        # 保护字符串
        source = re.sub(r'"[^"]*"', protect, source)
        source = re.sub(r"'[^']*'", protect, source)

        # 执行关键字替换
        source = self._replace_keywords(source)
        # 迁移赋值语法：定义 x 等于 y → 设 x 为 y
        source = self._migrate_assignment(source)
        # 迁移函数定义：段 名 接收 参数 → 段 名(参数)
        source = self._migrate_function_def(source)
        # 迁移成员访问：对象之属性 → 对象.属性
        source = self._migrate_member_access(source)
        # 迁移打印语法：打印 x → 印(x) 或 印 x
        source = self._migrate_print(source)

        # 恢复保护的内容
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

        # 检查关键字替换
        for v33_keyword, v40_keyword in self.keyword_map.items():
            if v33_keyword == v40_keyword:
                continue
            for i, line in enumerate(source.split('\n'), 1):
                if v33_keyword in line:
                    # 确保是作为关键字使用
                    if re.search(r'\b' + re.escape(v33_keyword) + r'\b', line):
                        changes.append({
                            'line': i,
                            'type': '关键字替换',
                            'old': v33_keyword,
                            'new': v40_keyword,
                            'content': line.strip(),
                        })

        # 检查赋值语法
        for i, line in enumerate(source.split('\n'), 1):
            if re.search(r'定义\s+\S+\s+等于', line):
                changes.append({
                    'line': i,
                    'type': '赋值语法迁移',
                    'old': '定义 x 等于 y',
                    'new': '设 x 为 y',
                    'content': line.strip(),
                })

        # 检查函数定义
        for i, line in enumerate(source.split('\n'), 1):
            if re.search(r'(?:段落|段|函数)\s+\S+\s+接收', line):
                changes.append({
                    'line': i,
                    'type': '函数定义迁移',
                    'old': '段 名 接收 参数',
                    'new': '段 名(参数)',
                    'content': line.strip(),
                })

        # 检查成员访问
        for i, line in enumerate(source.split('\n'), 1):
            if re.search(r'[\u4e00-\u9fff\w]之[\u4e00-\u9fff\w]', line):
                changes.append({
                    'line': i,
                    'type': '成员访问迁移',
                    'old': '对象之属性',
                    'new': '对象.属性',
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
            return "无需修改，代码已兼容 v4.0 语法。\n"

        lines = []
        lines.append("=" * 60)
        lines.append("v3.3 → v4.0 代码迁移报告")
        lines.append("=" * 60)
        lines.append(f"总计 {len(changes)} 处需要修改\n")

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
            lines.append(f"  L{c['line']:4d} [{c['type']}] {c['old']} → {c['new']}")
            lines.append(f"        源: {c['content'][:60]}")

        lines.append("=" * 60)
        return '\n'.join(lines)

    # ------------------------------------------------------------------
    # 内部迁移方法
    # ------------------------------------------------------------------

    def _replace_keywords(self, source: str) -> str:
        """替换关键字"""
        # 按关键字长度降序排序，避免部分匹配
        sorted_keywords = sorted(self.keyword_map.items(), key=lambda x: -len(x[0]))

        for old_kw, new_kw in sorted_keywords:
            if old_kw == new_kw:
                continue
            # 使用正则进行单词边界替换
            pattern = re.compile(re.escape(old_kw))
            source = pattern.sub(new_kw, source)

        return source

    def _migrate_assignment(self, source: str) -> str:
        """迁移赋值语法：定义 x 等于 y → 设 x 为 y"""
        # 定义 x 等于 y → 设 x 为 y
        source = re.sub(
            r'定义\s+(\S+)\s+等于\s+',
            r'设 \1 为 ',
            source
        )
        # 补充：定义 x = y → 设 x 为 y
        source = re.sub(
            r'定义\s+(\S+)\s*=\s*',
            r'设 \1 为 ',
            source
        )
        return source

    def _migrate_function_def(self, source: str) -> str:
        """迁移函数定义：段 名 接收 参数 → 段 名(参数)"""
        # 段 名 接收 参数1, 参数2 → 段 名(参数1, 参数2)
        source = re.sub(
            r'(?:段落|段|函数)\s+(\S+)\s+接收\s+(.+)',
            lambda m: f'段 {m.group(1)}({m.group(2).strip()})',
            source
        )
        # 段 名 接收（无参数变体，保留后置冒号）
        source = re.sub(
            r'(?:段落|段|函数)\s+(\S+)\s+接收\s*',
            lambda m: f'段 {m.group(1)}()',
            source
        )
        return source

    def _migrate_member_access(self, source: str) -> str:
        """迁移成员访问：对象之属性 → 对象.属性"""
        # 中文之连接
        source = re.sub(
            r'([\u4e00-\u9fff\w])之([\u4e00-\u9fff\w])',
            r'\1.\2',
            source
        )
        return source

    def _migrate_print(self, source: str) -> str:
        """迁移打印语法"""
        # 打印 x → 印 x
        source = re.sub(
            r'打印\s+',
            '印 ',
            source
        )
        # 输出 x → 写 x
        source = re.sub(
            r'输出\s+',
            '写 ',
            source
        )
        return source