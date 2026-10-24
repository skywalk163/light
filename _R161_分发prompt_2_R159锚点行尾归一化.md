# 【分发 Prompt 2/4】修复 R159 depth-aware 锚点测试红（行尾 artifact，改测试锚点）

## 任务

把 `tests/unit/test_R159_E3_容器布尔repr.py::test_源码级_病灶depth感知锚点存在` 从「非 Windows 必红」
修为「行尾无关」。这是 R161 收口后剩余的 5 个红之一（#8），定性为**行尾 artifact，非代码缺陷**
（runtime 的 depth-aware 修复本身在，LF 归一化后锚点命中）。

## 背景（上下文，勿重新探查）

- 仓库：`G:\dswork\duan-light-merge\light-merge`（Windows 本机开发树）。
- 当前 HEAD：`9f7f81c6e`（R161 收口修复，已推 gitea）。R161 本体 = `307af7932`。
- 权威测试机：**0.82**（192.168.0.82，FreeBSD 15.1，用户 `ai`）。干净树 `~/r161clean`
  已 ff 到 `9f7f81c6e` 且 `git status` 干净。解释器 `/home/ai/lm082_venv/bin/python`。
- **0.86 已关机，不要尝试。**
- 本机 Windows **不跑 pytest**。一切测试在 0.82 跑。
- 本机 ssh 助手：`light-merge/_r161_scratch/d_remote.py`，用法 `d_remote.run('82', cmd, timeout)`。

## 问题定位

- 文件：`tests/unit/test_R159_E3_容器布尔repr.py`
- 行 252-256，两个锚点常量**硬编码裸 `\r\n`**：

```python
_BUG_LINE = (b'        case 5: return dv_strdup(v->boolean ? "真" : "假");\r\n')
_FIX_LINE = (b'        case 5: return dv_strdup(v->boolean ? (depth > 0 ? "true" : "真")\r\n'
             b'                                            : (depth > 0 ? "false" : "假"));\r\n')
```

- 失败点（约 L400）：`test_源码级_病灶depth感知锚点存在` 直接 `open(_RT,'rb').read()` 后
  `assert _FIX_LINE in txt`。git 索引存 LF、FreeBSD 干净 clone 工作树为 LF ⇒ 必失败。
- 该红在**真 R160（`444d765a9`）树上同样失败**（已实测），非 R161 引入。
- 附带事实：把 `runtime_typed.c` 行尾归一化为 LF 后，`case 5` 的 depth-aware 形态**存在**、
  `dv_to_string_depth(e, 1)` 恰 2 处 —— 源码本身完好。

## 建议改法（只改测试，不动 runtime）

1. 两个常量去掉 `\r\n` 后缀（改 LF 版），并在注释里注明「匹配前做行尾归一化」。
2. **所有读取 runtime 做锚点断言的地方**，读取后先归一化再比：
   `txt = f.read().replace(b'\r\n', b'\n')`。涉及：
   - `test_源码级_病灶depth感知锚点存在`（约 L400 的守单点用例）；
   - 反跑有牙用例（`_RTWriteLock` 那个，约 L352-391）——它用
     `original.replace(_FIX_LINE, _BUG_LINE)` 打补丁再写回，**必须一并处理**。
3. 反跑用例的两个坑必须避开（否则修成假绿）：
   - `assert patched != original` 要用**归一化后的 original** 比较，否则 CRLF 文件上恒真、反跑无牙；
   - `finally` 里恢复时必须写回**原始字节**（保留原行尾形态），不能写回归一化后的内容。
4. 不动 `src/llvm/runtime_typed.c`、不动 `.gitattributes`。

## 验收（0.82 实测，据实报告）

```bash
cd /home/ai/r161clean && /home/ai/lm082_venv/bin/python -m pytest \
    tests/unit/test_R159_E3_容器布尔repr.py -n 0 -p no:randomly -q
# 期望：全绿（修复前 test_源码级_病灶depth感知锚点存在 1 failed）
```

追加自查（证明没修成假绿）：确认反跑用例的「补丁未生效」分支仍可达——
即把 `_FIX_LINE` 临时改错一个字符后，该文件应出现断言失败而非通过。

## 纪律红线

- **不 commit、不 push**。改完把 diff 交回。
- `git add` 只用显式文件名。
- 只改 `tests/unit/test_R159_E3_容器布尔repr.py` 一个文件；不动 runtime。
- 该用例在 xdist 下会 skip（设计如此）；验收用 `-n 0` 串行。

## 交付物

1. `tests/unit/test_R159_E3_容器布尔repr.py` 的修改（git diff）。
2. 简短报告：改法、验收命令原始输出、反跑有牙自查结果。
