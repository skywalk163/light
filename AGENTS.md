# AGENTS.md — 光明（Light）语言

> 给 AI Agent 的最短入口。看完这一页就能写、能跑、能自查。长内容不在这里搬，只给指针。

- **这是什么**：一门中文关键字的编程语言。解释器在 `src/`，CLI 在 `cli/`，标准库在 `stdlib/`，机器可读规格在 `spec/light.spec.json`。
- **一行 hello**：`打印("你好，世界")`
- **怎么跑**：`python cli/light.py run hello.light`（装好后：`light 运行 hello.light`）
- **怎么查**：`python cli/light.py ai card` 出速查卡；`python cli/light.py ai check --json hello.light` 出机器可读诊断
- **改完怎么验**：`python -m pytest -q tests/unit`

## 六条硬规则

1. 只用中文关键字：`段落`、`如果`、`否则`、`遍历`、`当`、`设`、`返回`、`类`、`导入`。
2. 块首行必须带冒号（`：` 或 `:` 都认），否则报语法错误。
3. `print` 一律写 `打印`；同理 `len` 写 `长` 或 `长度`。
4. `读取(x)` 是读 **stdin**，不是读文件。
5. 读文件用 `读取文件(路径)`；规范写法先 `从 文件系统 导入 读取文件, 写入文件`。
6. 代码块靠缩进划分，统一 4 空格，不混 tab。

值类型写 `真`/`假`/`空`；容器用 `[]`、`{}`、`()`；注释用 `#`。

## 常用导入

```光明
从 文件系统 导入 读取文件, 写入文件, 文件存在
从 字符串处理 导入 分割, 拼接
```

## 常用命令

| 命令 | 作用 |
|------|------|
| `light ai card` | 输出精简速查卡；`--full` 出完整版 |
| `light ai check --json 文件.light` | 机器可读诊断：stdout 单个 JSON，退出码 0 干净 / 1 有 error / 2 用法错 |
| `light ai snippets` | 列出片段模板，`light ai snippets 变量-整数` 看单个 |
| `light 运行 文件.light` | 解释执行 |

没装 `light` 命令时，把 `light` 换成 `python cli/light.py`，子命令不变。

## 能跑的完整示例

```光明
从 文件系统 导入 读取文件, 写入文件

段落 统计行数 接收 路径：
    设 文本 为 读取文件(路径)
    设 行 为 分割(文本, "\n")
    返回 长(行)

段落 主：
    打印(统计行数("README.md"))
    写入文件("out.txt", "完成")
```

## 别做

- 别按 Python 惯性写 `def`、`if`、`for`；值只写 `真`/`假`/`空`（`True`/`None` 即使能跑也不用）。
- 别用 `&&`、`||`、`+=`；逻辑用 `且`/`或`/`非`，累加用 `加上`。
- 列表追加统一写 `列表.追加(项)`，别用 `追加(列表, 项)` 的函数式写法。
- 别新增第三方依赖，也别为了通过检查放宽判据。

## 卡住了看哪里

- `docs/AI编程指南.md` —— §六 避坑 14 条、§十二-C `light ai check --json` 闭环
- `docs/STDLIB_REFERENCE.md` —— 标准库函数名权威表（109 个模块）
- `docs/language/l0-core.md` —— L0 核心字表（44 字）
- `spec/light.spec.json` —— 所有事实的单一来源：关键字、L0、stdlib 导出
- `docs/MVP_SURFACE.md` —— 最小可用面，先写这些保过
- `light ai snippets` —— 现成模板，改占位符就行

三层语法卡按需现出：`light ai card`（compact）、`light ai card --full`（全量）。静态副本随 T-0459 落地，届时以此为准。
