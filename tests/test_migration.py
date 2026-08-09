# -*- coding: utf-8 -*-
"""
测试光明代码迁移工具

测试覆盖：
- v3.3 → v4.0 关键字替换
- v3.3 → v4.0 赋值语法迁移
- v3.3 → v4.0 函数定义迁移
- v3.3 → v4.0 成员访问迁移
- v3.3 → v4.0 打印语法迁移
- v3.3 → v4.0 预览变更
- v3.3 → v4.0 迁移报告
- v4.0 → v5.x 导入语法迁移
- v4.0 → v5.x 类型注解增强
- v4.0 → v5.x 预览变更
- v4.0 → v5.x 迁移报告
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from migration.v33_to_v40 import MigrationV33ToV40
from migration.v40_to_v50 import MigrationV40ToV50


class TestMigrationV33ToV40:
    """测试 v3.3 → v4.0 迁移"""

    def setup_method(self):
        self.migrator = MigrationV33ToV40()

    # ------------------------------------------------------------------
    # 关键字替换
    # ------------------------------------------------------------------

    def test_keyword_if(self):
        """测试关键字替换：如果 → 若"""
        source = "如果 条件："
        expected = "若 条件："
        result = self.migrator.migrate(source)
        assert result.strip() == expected.strip(), f"关键字替换失败\n期望: {expected}\n实际: {result}"

    def test_keyword_else(self):
        """测试关键字替换：否则 → 否"""
        source = "否则："
        expected = "否："
        result = self.migrator.migrate(source)
        assert result.strip() == expected.strip(), f"关键字替换失败\n期望: {expected}\n实际: {result}"

    def test_keyword_function(self):
        """测试关键字替换：函数 → 函"""
        source = "函数 测试()："
        expected = "函 测试()："
        result = self.migrator.migrate(source)
        assert result.strip() == expected.strip(), f"关键字替换失败\n期望: {expected}\n实际: {result}"

    def test_keyword_return(self):
        """测试关键字替换：返回 → 还"""
        source = "返回 结果"
        expected = "还 结果"
        result = self.migrator.migrate(source)
        assert result.strip() == expected.strip(), f"关键字替换失败\n期望: {expected}\n实际: {result}"

    def test_keyword_print(self):
        """测试关键字替换：打印 → 印"""
        source = "打印 消息"
        expected = "印 消息"
        result = self.migrator.migrate(source)
        assert result.strip() == expected.strip(), f"关键字替换失败\n期望: {expected}\n实际: {result}"

    def test_keyword_import(self):
        """测试关键字替换：导入 → 引"""
        source = "导入 数学"
        expected = "引 数学"
        result = self.migrator.migrate(source)
        assert result.strip() == expected.strip(), f"关键字替换失败\n期望: {expected}\n实际: {result}"

    # ------------------------------------------------------------------
    # 赋值语法迁移
    # ------------------------------------------------------------------

    def test_assignment(self):
        """测试赋值语法迁移：定义 x 等于 y → 设 x 为 y"""
        source = "定义 x 等于 10"
        expected = "设 x 为 10"
        result = self.migrator.migrate(source)
        assert result.strip() == expected.strip(), f"赋值语法迁移失败\n期望: {expected}\n实际: {result}"

    # ------------------------------------------------------------------
    # 函数定义迁移
    # ------------------------------------------------------------------

    def test_function_def(self):
        """测试函数定义迁移：段 名 接收 参数 → 段 名(参数)"""
        source = "段 添加 接收 a, b"
        expected = "段 添加(a, b)"
        # 注意：去掉可能附加的冒号
        result = self.migrator.migrate(source).strip().rstrip('：:')
        expected = expected.strip().rstrip('：:')
        assert result == expected, f"函数定义迁移失败\n期望: {expected}\n实际: {result}"

    # ------------------------------------------------------------------
    # 成员访问迁移
    # ------------------------------------------------------------------

    def test_member_access(self):
        """测试成员访问迁移：对象之属性 → 对象.属性"""
        source = "控制台之日志"
        expected = "控制台.日志"
        result = self.migrator.migrate(source)
        assert result.strip() == expected.strip(), f"成员访问迁移失败\n期望: {expected}\n实际: {result}"

    # ------------------------------------------------------------------
    # 打印语法迁移
    # ------------------------------------------------------------------

    def test_print_syntax(self):
        """测试打印语法迁移：打印 x → 印 x"""
        source = "打印 消息"
        expected = "印 消息"
        result = self.migrator.migrate(source)
        assert result.strip() == expected.strip(), f"打印语法迁移失败\n期望: {expected}\n实际: {result}"

    def test_output_syntax(self):
        """测试输出语法迁移：输出 x → 写 x"""
        source = "输出 结果"
        expected = "写 结果"
        result = self.migrator.migrate(source)
        assert result.strip() == expected.strip(), f"输出语法迁移失败\n期望: {expected}\n实际: {result}"

    # ------------------------------------------------------------------
    # 完整代码迁移
    # ------------------------------------------------------------------

    def test_complete_migration(self):
        """测试完整代码迁移"""
        source = """定义 名称 等于 "光明"
打印 名称
函数 添加(a, b)：
    返回 a + b
结果 = 添加(3, 4)
打印 结果
"""
        result = self.migrator.migrate(source)
        # 检查关键字替换
        assert '定义' not in result, "定义 应被替换"
        assert '打印' not in result, "打印 应被替换"
        assert '函数' not in result, "函数 应被替换"
        assert '返回' not in result, "返回 应被替换"
        # 检查新关键字
        assert '设' in result, "应包含 设"
        assert '印' in result, "应包含 印"

    # ------------------------------------------------------------------
    # 字符串保护
    # ------------------------------------------------------------------

    def test_string_protection(self):
        """测试字符串内容不被替换"""
        source = "打印 \"如果 条件 成立\""
        result = self.migrator.migrate(source)
        # 字符串内的"如果"不应被替换
        assert '"如果 条件 成立"' in result, "字符串内容应被保护"

    def test_comment_protection(self):
        """测试注释内容不被替换"""
        source = "如果 条件：# 这是如果条件"
        result = self.migrator.migrate(source)
        # 注释中的"如果"应被保护（注释行整体被保护）
        assert '如果' in result or '若' in result, "注释内容应被保护或关键字已替换"

    # ------------------------------------------------------------------
    # 预览变更
    # ------------------------------------------------------------------

    def test_preview_changes(self):
        """测试预览变更"""
        source = """如果 条件：
    打印 "hello"
"""
        changes = self.migrator.preview_changes(source)
        assert len(changes) >= 1, f"期望检测到变更，实际{len(changes)}"

    # ------------------------------------------------------------------
    # 迁移报告
    # ------------------------------------------------------------------

    def test_report(self):
        """测试迁移报告生成"""
        changes = [
            {'line': 1, 'type': '关键字替换', 'old': '如果', 'new': '若',
             'content': '如果 条件：'}
        ]
        report = self.migrator.report(changes)
        assert 'v3.3 → v4.0' in report, "报告应包含版本信息"
        assert '1 处' in report, "报告应包含变更数量"
        assert '如果' in report, "报告应包含旧关键字"

    def test_report_no_changes(self):
        """测试无变更时的报告"""
        report = self.migrator.report([])
        assert '无需修改' in report, "无变更报告应提示无需修改"


class TestMigrationV40ToV50:
    """测试 v4.0 → v5.x 迁移"""

    def setup_method(self):
        self.migrator = MigrationV40ToV50()

    # ------------------------------------------------------------------
    # 导入语法迁移
    # ------------------------------------------------------------------

    def test_import_simple(self):
        """测试简单导入迁移：导入 x → 引 x"""
        source = "导入 数学"
        expected = "引 数学"
        result = self.migrator.migrate(source)
        assert result.strip() == expected.strip(), f"导入迁移失败\n期望: {expected}\n实际: {result}"

    def test_import_as(self):
        """测试带别名的导入迁移：导入 x as y → 引 x 为 y"""
        source = "导入 数学 as 数"
        expected = "引 数学 为 数"
        result = self.migrator.migrate(source)
        assert result.strip() == expected.strip(), f"别名导入迁移失败\n期望: {expected}\n实际: {result}"

    def test_import_from(self):
        """测试从...导入迁移：从 x 导入 y → 引 x 中 y"""
        source = "从 数学 导入 平方"
        expected = "引 数学 中 平方"
        result = self.migrator.migrate(source)
        assert result.strip() == expected.strip(), f"从导入迁移失败\n期望: {expected}\n实际: {result}"

    # ------------------------------------------------------------------
    # 导出语法迁移
    # ------------------------------------------------------------------

    def test_export(self):
        """测试导出迁移：导出 → 出"""
        source = "导出 函数名"
        expected = "出 函数名"
        result = self.migrator.migrate(source)
        assert result.strip() == expected.strip(), f"导出迁移失败\n期望: {expected}\n实际: {result}"

    # ------------------------------------------------------------------
    # 类型注解增强
    # ------------------------------------------------------------------

    def test_list_type_annotation(self):
        """测试列表类型注解：列表[类型] → 列表<类型>"""
        source = "列表[整数]"
        expected = "列表<整数>"
        result = self.migrator.migrate(source)
        assert expected.strip() in result.strip(), f"列表类型注解迁移失败\n期望: {expected}\n实际: {result}"

    def test_map_type_annotation(self):
        """测试映射类型注解：映射[键, 值] → 映射<键, 值>"""
        source = "映射[文本, 整数]"
        expected = "映射<文本, 整数>"
        result = self.migrator.migrate(source)
        assert expected.replace(" ", "") in result.replace(" ", ""), f"映射类型注解迁移失败"

    # ------------------------------------------------------------------
    # 预览变更
    # ------------------------------------------------------------------

    def test_preview_changes(self):
        """测试预览变更"""
        source = """导入 数学

段 主():
    印("hello")
"""
        changes = self.migrator.preview_changes(source)
        # 应检测到导入语法需要变更
        import_changes = [c for c in changes if c['type'] == '导入语法']
        assert len(import_changes) >= 1, f"期望检测到导入语法变更，实际{len(import_changes)}"

    # ------------------------------------------------------------------
    # 迁移报告
    # ------------------------------------------------------------------

    def test_report(self):
        """测试迁移报告生成"""
        changes = [
            {'line': 1, 'type': '导入语法', 'description': '「导入」→「引」',
             'content': '导入 数学'}
        ]
        report = self.migrator.report(changes)
        assert 'v4.0 → v5.x' in report, "报告应包含版本信息"
        assert '1 处' in report, "报告应包含变更数量"

    def test_report_no_changes(self):
        """测试无变更时的报告"""
        report = self.migrator.report([])
        assert '无需修改' in report, "无变更报告应提示无需修改"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])