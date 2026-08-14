# 段言 Markdown 编辑器

一个使用段言语言编写的 Markdown 到 HTML 转换器。

## 功能

- 支持标题（# 到 ######）
- 支持无序列表（- 和 *）
- 支持有序列表（1. 2. 3.）
- 支持代码块（```）
- 支持内联格式（**粗体**、*斜体*、`代码`）
- 支持链接 [text](url)
- 自动生成完整 HTML 页面
- 输出到 output.html 文件

## 运行

```bash
python -m cli.duan run examples/markdown_editor/主.duan
```

## 使用

1. 运行程序
2. 输入 Markdown 内容
3. 在单独一行输入 `END` 结束
4. 查看转换结果和保存的 HTML 文件