# MiniLog · Go 参考实现（第二 oracle）

> 任务：T-0360 · 用途：与 `04-reference/python/minilog.py` 互为独立实现，做交叉对拍，
> 排除「oracle 与用例共享同一 Python 心智模型」导致的同源错误。
> 语义唯一依据：`../../01-spec/MiniLog规格.md`。本实现刻意直译本规格，不做性能优化。

## 文件

| 文件 | 作用 |
|------|------|
| `minilog.go` | MiniLog 全部命令实现，`package main`，仅用标准库 |
| `build.sh` | 幂等构建脚本，产出同目录可执行文件 `minilog` |
| `README.md` | 本文件：Go/Python 差异点核对表与已知边界 |

## 构建与运行

```sh
# 在 benchmarks/light-lang-bench 目录下（与验收命令一致）
sh 04-reference/go/build.sh

# 对拍（仓库根目录）
python3 02-tests/run_suite.py --target ./04-reference/go/minilog --suite all --stage v2
```

- 工具链：Go 1.25（FreeBSD 门禁机实测 `go1.25.14 freebsd/amd64`），无第三方依赖、无 `go.mod`。
- `go vet ./...` 在本目录下无输出、退出码 0。
- 子命令与选项与规格 §1–§3 一致：`filter --level=<值>`、`tail --n=<正整数>`、
  `validate`、`stats --group-by=service`，通用选项 `--input=<文件|->`、`--output=<文件>`。

## 对拍结果

同一套 53 例（visible 33 + hidden 20，v2 含 v1 回归）在同一门禁机、同一临时目录策略下：

| 实现 | 结果 |
|------|------|
| Go（本实现） | 53 / 53 PASS |
| Python（既有 oracle） | 53 / 53 PASS |

## 差异点核对表（对应任务卡 §3，12 行逐条结论）

| # | 差异点 | 规格依据 | Go 侧处理 | Python 侧处理 | 一致？ |
|---|--------|----------|-----------|---------------|--------|
| 1 | 行尾 `\r` 去除 | §0.1 | 逐行判断 `HasSuffix("\r")`，裁掉一个尾部 `\r` | `line[:-1] if line.endswith("\r")` | 是 |
| 2 | 空行/空白行忽略且不编号 | §0.1 | `Trim(l, " \t\r\n")` 为空则跳过，不占记录索引 | `not line.strip()` 跳过，不计索引 | 是（规格空白限 ASCII；Go 不裁 Unicode 空白，见下方边界说明） |
| 3 | 非法 JSON → stderr 警告 + 跳过 + 不改退出码 | §0.3 | 解析失败记 invalid，追加 `WARN invalid_json index=<idx>\n` 到 stderr，退出码仍 0 | 同：警告写 stderr，跳过该记录，退出码 0 | 是 |
| 4 | JSON 合法但非对象（数组/标量/null）同样按非法处理 | §0.3 | Unmarshal 后值为 `nil`（null）或非 `map[string]any` 即判 invalid | 非 `isinstance(dict)`（含 `None`）即判 invalid | 是 |
| 5 | 「原样输出原始行」禁止重新序列化 | §0.1 | 命中行直接输出裁剪 `\r` 后的原始字节，不经 JSON 重编码 | 同样 append 原始 `line`，不重新序列化 | 是 |
| 6 | 时间戳比较用 20 字符字典序 | §0.2 | 字符串 `>` 比较（字节序），不解析时间；ASCII 时间戳下与码点序一致 | `ts > groups[svc][1]` 字符串比较，不解析时间 | 是 |
| 7 | `stats` 分组按 UTF-8 **字节序**升序 | §3.2 | `sort.Strings`（Go 字符串按 UTF-8 字节比较） | `sorted(groups, key=lambda s: s.encode("utf-8"))` | 是 |
| 8 | `--n` 拒绝 `+2`/`0`/`-1`/`abc` | §2.2 | 纯 ASCII 数字且 `Atoi >= 1`，否则用法错误（退出码 2） | `isascii() and isdigit()`、去前导 `+`、`int >= 1`，否则退出码 2 | 是 |
| 9 | 同选项重复 → 退出码 2 | §1.2 | 选项键已存在即 `usageError`，退出码 2 | 重复键抛 `UsageError`，退出码 2 | 是 |
| 10 | `--output` 时 stdout 必须 0 字节 | §3.1 | 给出 `--output` 时只写目标文件，不写 stdout | 同：输出重定向到文件，stdout 为 0 字节 | 是 |
| 11 | 1 MiB 单行不截断 | §0.4 | `io.ReadAll` 整文件入内存，无固定行缓冲区 | `buffer.read()` 整文件读取，无固定行缓冲区 | 是 |
| 12 | 字段值为 null/数字/布尔/数组/对象 → 视为缺失 | §0.2 | 类型断言 `v.(string)` 失败即记 `missing_<字段>` | `isinstance(str)` 否则记 `missing_<字段>` | 是 |

## 已知边界差异（套件未覆盖，不影响 53 例对拍）

1. **非 ASCII 空白行**：Python `strip()` 会识别 NBSP 等 Unicode 空白；Go 实现按规格 §0.1
   只裁 ASCII 空格/TAB/CR/LF。规格明确空白行只含 ASCII 空白，故以规格为准。
2. **字符串字面量内的非法 UTF-8**：Python 严格 UTF-8 解码失败即记非法；Go `encoding/json`
   会把非法字节替换为 U+FFFD。套件输入均为合法 UTF-8，不触发该路径。
3. **`--n` 超大整数**：Python `int` 无上限；Go `strconv.Atoi` 溢出时按用法错误处理（退出码 2）。
   套件 `--n` 均为小正整数。

## 用例与规格变更

- 本任务**未修改** `01-spec/` 与 `02-tests/`：53 例期望值、fixtures、runner 均沿用前置
  oracle 对拍通过的版本，无新增/改写用例，无需裁决记录。
- 未触碰本目录之外的任何文件；编译产物 `minilog` 为本地构建物，不入库。
