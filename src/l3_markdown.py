"""
光明 L3 领域嵌入 - Markdown 文档 DSL
====================================
提供中文语法的 Markdown 文档生成能力。
支持标题、段落、列表、表格、代码块等文档结构。

用法示例（在 .light 文件中）：
    引 Python:
        from l3_markdown import L3Markdown
        l3_md = L3Markdown()
    结束引

    设 文档 = l3_md.文档("报告")
    l3_md.标题("第一章", 1)
    l3_md.段落("这是内容。")
    l3_md.列表(["项目A", "项目B"])
    设 结果 = l3_md.导出()
"""

from typing import List, Optional, Dict, Any, Union
import re


class L3MarkdownError(Exception):
    """L3 Markdown DSL 错误"""
    pass


class L3Markdown:
    """Markdown 文档生成 DSL

    支持中文关键字操作：
        - 文档(标题) - 创建新文档
        - 标题(文本, 级别) - 添加标题
        - 段落(文本) - 添加段落
        - 列表(项列表, 有序=False) - 添加列表
        - 表格(表头, 行数据) - 添加表格
        - 代码块(代码, 语言="") - 添加代码块
        - 引用(文本) - 添加引用
        - 分隔线() - 添加分隔线
        - 粗体(文本) - 粗体文本
        - 斜体(文本) - 斜体文本
        - 链接(文本, URL) - 超链接
        - 图片(替代文本, URL) - 图片
        - 导出() - 获取完整 Markdown 字符串
    """

    def __init__(self):
        self._lines: List[str] = []
        self._title: str = ""
        self._has_content: bool = False

    # ==================== 公共 API ====================

    def 文档(self, 标题: str, 级别: int = 1) -> str:
        """创建新文档（清空之前内容）

        参数:
            标题: 文档标题
            级别: 标题级别 1-6（默认 1）

        返回:
            str - 文档标题
        """
        self._lines = []
        self._title = 标题
        self._has_content = False
        self._validate_heading_level(级别)
        self._lines.append(f"{'#' * 级别} {标题}")
        self._lines.append("")
        return 标题

    def 标题(self, 文本: str, 级别: int = 1) -> str:
        """添加标题

        参数:
            文本: 标题文本
            级别: 1-6（默认 1）

        返回:
            str - 标题文本
        """
        self._validate_heading_level(级别)
        self._lines.append(f"{'#' * 级别} {文本}")
        self._lines.append("")
        self._has_content = True
        return 文本

    def 段落(self, 文本: str) -> str:
        """添加段落

        参数:
            文本: 段落文本

        返回:
            str - 段落文本
        """
        if not 文本 or not 文本.strip():
            raise L3MarkdownError("段落内容不能为空")
        self._lines.append(文本)
        self._lines.append("")
        self._has_content = True
        return 文本

    def 列表(self, 项: List[str], 有序: bool = False) -> List[str]:
        """添加列表

        参数:
            项: 列表项文本列表
            有序: True 为有序列表，False 为无序列表（默认）

        返回:
            List[str] - 列表项列表

        示例:
            >>> md = L3Markdown()
            >>> md.列表(["苹果", "香蕉", "橘子"])
            ['苹果', '香蕉', '橘子']
        """
        if not 项:
            raise L3MarkdownError("列表项不能为空")

        for i, item in enumerate(项):
            if not item or not item.strip():
                raise L3MarkdownError(f"列表第 {i+1} 项内容不能为空")
            if 有序:
                self._lines.append(f"{i+1}. {item}")
            else:
                self._lines.append(f"- {item}")

        self._lines.append("")
        self._has_content = True
        return 项

    def 表格(self, 表头: List[str], 行数据: List[List[str]]) -> str:
        """添加表格

        参数:
            表头: 列标题列表
            行数据: 行数据列表，每行是一个字符串列表

        返回:
            str - 表格的 Markdown 字符串

        示例:
            >>> md = L3Markdown()
            >>> md.表格(["姓名", "年龄"], [["张三", "20"], ["李四", "25"]])
        """
        if not 表头:
            raise L3MarkdownError("表格表头不能为空")
        if not 行数据:
            raise L3MarkdownError("表格行数据不能为空")

        col_count = len(表头)
        for row in 行数据:
            if len(row) != col_count:
                raise L3MarkdownError(
                    f"表格行数据列数 ({len(row)}) 与表头列数 ({col_count}) 不匹配"
                )

        # 表头
        self._lines.append("| " + " | ".join(表头) + " |")
        # 分隔行
        self._lines.append("| " + " | ".join(["---"] * col_count) + " |")
        # 数据行
        for row in 行数据:
            self._lines.append("| " + " | ".join(row) + " |")

        self._lines.append("")
        self._has_content = True
        return "| " + " | ".join(表头) + " |"

    def 代码块(self, 代码: str, 语言: str = "") -> str:
        """添加代码块

        参数:
            代码: 代码内容
            语言: 代码语言标识（如 "python", "javascript", "" 等）

        返回:
            str - 代码内容
        """
        if not 代码 or not 代码.strip():
            raise L3MarkdownError("代码块内容不能为空")

        self._lines.append(f"```{语言}")
        self._lines.append(代码)
        self._lines.append("```")
        self._lines.append("")
        self._has_content = True
        return 代码

    def 引用(self, 文本: str) -> str:
        """添加引用块

        参数:
            文本: 引用文本

        返回:
            str - 引用文本
        """
        if not 文本:
            raise L3MarkdownError("引用内容不能为空")

        for line in 文本.split("\n"):
            self._lines.append(f"> {line}")
        self._lines.append("")
        self._has_content = True
        return 文本

    def 分隔线(self) -> str:
        """添加分隔线

        返回:
            str - "---"
        """
        self._lines.append("---")
        self._lines.append("")
        self._has_content = True
        return "---"

    def 粗体(self, 文本: str) -> str:
        """生成粗体文本（内联，不自动换行）

        参数:
            文本: 要加粗的文本

        返回:
            str - 带 Markdown 粗体标记的文本
        """
        return f"**{文本}**"

    def 斜体(self, 文本: str) -> str:
        """生成斜体文本（内联，不自动换行）

        参数:
            文本: 要斜体的文本

        返回:
            str - 带 Markdown 斜体标记的文本
        """
        return f"*{文本}*"

    def 链接(self, 文本: str, url: str) -> str:
        """生成超链接（内联，不自动换行）

        参数:
            文本: 链接显示文本
            url: 链接地址

        返回:
            str - Markdown 链接格式
        """
        if not url:
            raise L3MarkdownError("链接 URL 不能为空")
        return f"[{文本}]({url})"

    def 图片(self, 替代文本: str, url: str) -> str:
        """生成图片（内联，不自动换行）

        参数:
            替代文本: 图片替代文本
            url: 图片 URL

        返回:
            str - Markdown 图片格式
        """
        if not url:
            raise L3MarkdownError("图片 URL 不能为空")
        return f"![{替代文本}]({url})"

    def 导出(self) -> str:
        """导出完整 Markdown 文档

        返回:
            str - 完整 Markdown 字符串
        """
        if not self._has_content and not self._title:
            raise L3MarkdownError("文档为空，请先添加内容")
        return "\n".join(self._lines)

    def 导出到文件(self, 文件路径: str) -> None:
        """导出 Markdown 文档到文件

        参数:
            文件路径: 输出文件路径
        """
        content = self.导出()
        with open(文件路径, "w", encoding="utf-8") as f:
            f.write(content)

    def 清空(self) -> None:
        """清空当前文档内容"""
        self._lines = []
        self._title = ""
        self._has_content = False

    # ==================== 内部方法 ====================

    def _validate_heading_level(self, 级别: int) -> None:
        """验证标题级别合法性"""
        if not isinstance(级别, int) or 级别 < 1 or 级别 > 6:
            raise L3MarkdownError(f"标题级别必须为 1-6 的整数，收到 {级别}")