# T-0197 交付摘要 —— 内置层对拍七条（LH-02/03/04/07/08/11/14）

agent: doubao-win ｜ 日期: 2026-10-29 ｜ 验收: `python3 -m pytest -q tests/unit/test_LH08_内置名与语义.py` → **7 passed**

## 七条落点与复测结论

| 条 | 现状 | 处置 |
|---|---|---|
| LH-08 是数字 | HEAD 上仍是旧映射（关键字 是数字→是数值），未自行修好 | **反转**：关键字 是数字→宽松谓词（int/float 排 bool，或单数字字符）；是数值单独可达；是数字符=等价别名。命名层不兼容变更，CHANGELOG 已写迁移口径 |
| LH-07 试转整数/字符串全数字 | 均缺失 | 新增 试转整数/试转浮点（不抛、支持正负号与首尾空白）；字符串全数字 补 builtin_map 达源码可达 |
| LH-02 皆空 | 无 | 新增 皆空（null/""/空列表/空字典）；是空 语义一行未动 |
| LH-03 字典取值 | 无 | 新增 字典取值（缺键或值为空都回落默认）；字典获取 保留 Python 语义 |
| LH-11 去空白/反转 | 去空白 NameError、反转 返回迭代器 | 去空白=去除空白 真实别名（本地段落由 _user_defined_functions 守卫压住不被劫持）；反转 返回新列表；枚举 维持现状（卡允许，验收未含） |
| LH-14 字节长度 | 无；编码.字节长度 实为十六进制字节数（与卡上猜测一致） | 新增内置 字节长度(文本,编码="utf-8") 真实字节数；撞名口径 CHANGELOG 已注明 |
| LH-04 排序 key | 第三参不存在 | 排序列表 加 键=空 参（收段落）；不传 key 行为不变 |

## 改动文件
- src/code_generator.py：builtin_map 追加（是数字/是数值/皆空/字典取值/试转整数/试转浮点/字节长度/去空白/字符串全数字/反转），未重排已有条目；stdlib 缺失兜底 lambda 同步
- src/keywords.py：STDLIB_VERB_ARITY 补 9 条
- stdlib/builtins.py：是数字/是数值 重写转发、新增 皆空/字典取值/试转整数/试转浮点/字节长度/反转/去空白别名；排序列表加 键；__all__ 同步
- stdlib/内置核心判型.light：是数字 改宽松谓词、新增 皆空
- tests/unit/test_LH08_内置名与语义.py：新增 7 独立用例
- tests/test_lpd_016_判型族.py：随 LH-08 反转更新断言（是数字("7") False→True）
- tests/integration/test_missing_stdlib.py：legacy src 兜底腿断言同步
- CHANGELOG.md：T-0197 条目 + 迁移口径

## 验证
- 新验收 7 passed；旧判型族测试通过；stdlib 缺失兜底 12 passed；空壳护栏 6 passed。
- 预存在的环境缺口（与本卡无关）：tests/unit/test_builtins_drift.py 7 个 FileNotFound，因其比对兄弟仓 lightharness 的 worktree（本机未签出）。

## 边界与后续
- 只加不改存量：是空 语义未动、不传 key 排序行为未动。
- **后续另立卡**：src/code_generator_unified.py 的 builtin_map 仍按旧 是数字=是数值 映射（unified 腿用例仍出旧值），跨后端（含 antlrparser/native 腿）名实一致化未在本卡 paths 内，已在 CHANGELOG 标注。
