# -*- coding: utf-8 -*-
"""
光明代码格式化器（安全子集，R97 重写）

========================================================================
R97 重写说明（对应 R96-KI-01 语义破坏缺陷的根除）
------------------------------------------------------------------------
旧实现（`LightFormatter.format()`）试图用「基于行首前缀猜测」的 regex 启发式
来重排缩进、给语句补冒号、加运算符空格、排序导入…… 这在光明这种**缩进敏感**
且关键字多为中文的语言上必然出错：

  1. `NEEDS_COLON` 含单字关键字 `返/跳/过/抛/终`，`返回 x` 被前缀匹配到 `返`
     → 错误追加中文冒号 `返回 x：`；
  2. 把整文件缩进重排为 4 空格，破坏嵌套块结构 → 产物不可被解析。

二者叠加使 `light fmt` 把**合法代码**改写成无法解析的形式
（复现：`examples/_test_nested_closure.light`）。

R97 收敛为**只做"绝不改变语义"的空白安全变换**：

  - 统一换行符为 \\n（CRLF 由 `run_formatter` 还原，见 `__init__.py`）；
  - 去除每一行的行尾空白；
  - 折叠 3 个及以上连续空行为 2 个；
  - 去除文件首尾多余空行；
  - 确保文件以恰好一个换行结尾。

**安全性证明**：光明是缩进敏感语言，块结构完全由「每行缩进 + 行内 token」
决定。本格式化器对这两类信息**逐行精确保留**（仅 `rstrip` 行尾空白，
不触碰行首缩进、不增删 token），因此产物的词法与块结构与输入**必然一致**——
不可能产生 R96-KI-01 那样的破坏性改写。

后续若需"缩进规范化 / 冒号对齐 / 导入排序"等增强，**必须接入真实解析器**
（复用 `src/` 的 lexer/parser），切勿退回到行前缀猜测启发式（R96 教训）。
========================================================================
"""

from typing import Dict, List


class LightFormatter:
    """光明代码安全格式化器（空白安全子集）"""

    def __init__(self, indent_size: int = 4, max_line_length: int = 80):
        # 保留构造参数以维持既有调用兼容性，但安全子集不依赖它们做语义变换。
        self.indent_size = indent_size
        self.max_line_length = max_line_length

    def format(self, source: str) -> str:
        """仅做空白安全变换；保证产物与原文件解析结果一致。

        变换步骤（均不改变 光明 的词法 / 块结构）：
          1. 统一换行符为 \\n；
          2. 去除每行行尾空白；
          3. 折叠 3+ 连续空行为 2 个；
          4. 去除首尾多余空行；
          5. 确保文件以单个换行结尾。
        """
        # 1. 统一换行符（run_formatter 已先做一遍，这里再做一遍无害）
        source = source.replace('\r\n', '\n').replace('\r', '\n')
        lines = source.split('\n')

        # 2 + 3. 去行尾空白 + 折叠连续空行
        out: List[str] = []
        blank = 0
        for line in lines:
            stripped = line.rstrip()
            if stripped == '':
                blank += 1
                if blank <= 2:
                    out.append('')
            else:
                blank = 0
                out.append(stripped)

        # 4. 去除首尾多余空行
        while out and out[0] == '':
            out.pop(0)
        while out and out[-1] == '':
            out.pop()

        text = '\n'.join(out)
        # 5. 确保文件以单个换行结尾（空文件返回空串）
        if text and not text.endswith('\n'):
            text += '\n'
        return text

    def format_file(self, file_path: str) -> str:
        """格式化文件（文本读写；CRLF 还原由调用方负责）。"""
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        formatted = self.format(source)
        if formatted != source:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(formatted)
        return formatted

    def format_token(self, tokens) -> str:
        """基于 token 序列格式化（降级为文本格式化，保持安全）。"""
        if isinstance(tokens, list):
            source = ' '.join(str(t) for t in tokens)
        else:
            source = str(tokens)
        return self.format(source)

    def check(self, source: str) -> List[Dict]:
        """检查格式问题，返回差异列表（仅空白 / 空行层面的差异）。

        返回空列表表示已合规（即 `format(source) == source`）。
        """
        formatted = self.format(source)
        if formatted == source:
            return []
        orig_lines = source.replace('\r\n', '\n').split('\n')
        fmt_lines = formatted.split('\n')
        issues: List[Dict] = []
        for i in range(max(len(orig_lines), len(fmt_lines))):
            o = orig_lines[i] if i < len(orig_lines) else ''
            f = fmt_lines[i] if i < len(fmt_lines) else ''
            if o != f:
                issues.append({'line': i + 1, 'original': o, 'formatted': f})
        return issues


def format_code(source: str, indent_size: int = 4, max_line_length: int = 80) -> str:
    """便捷函数：格式化光明代码（空白安全子集）。"""
    return LightFormatter(indent_size, max_line_length).format(source)


def check_format(source: str, indent_size: int = 4, max_line_length: int = 80) -> List[Dict]:
    """便捷函数：检查格式问题（返回差异列表）。"""
    return LightFormatter(indent_size, max_line_length).check(source)
