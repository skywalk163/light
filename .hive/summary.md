# T-0244 收口：原生腿 原子写入 门面归一（父目录 + bool 返回值）

**结论：卡面描述的「模块整体被拒」在 main 上已被 R164（提交 0a4e88c58）修掉；本卡实测
验收命令在未改代码时即 exit 0。真正残留的是两腿口径不一致，本卡在 .light 门面归一。**

## 做了什么（只改 stdlib/文件系统.light）

- 保留了 `_light_builtin.原子写入` 转发（原生腿已认这个模块点，dv_atomic_write 在
  runtime_typed.c:3282，能力清单里 原子写入 / atomic_write / dv_atomic_write 三条都在册）。
- 在门面层补两处归一，理由写在代码注释里：
  1. **父目录**：`dv_atomic_write` 用 `fopen(tmp,"wb")` 直写，父目录不存在就**静默返回 0**
     （无异常、无临时文件、目标不存在）；`.py` 真身与同模块 `写入文件` 都是先 makedirs。
     凭据表/游标这类路径常带子目录，静默写丢比报错更危险 → 门面先 `获取目录名` + `创建目录`。
  2. **返回值**：`dv_atomic_write` 返回 i32 0/1，原生腿下 `原子写入(...) == 真` 得 **假**；
     `.py` 返回 True。门面按 `.py` 契约归一回 bool（0 → 假，非 0 → 真）。
- 归一键选择：只动 .light 门面即可让两腿收敛，不必改 codegen/runtime（那在 paths 之外）。

## 为什么不是「原生侧补实现」

原生侧 R164 已经补过了（dv_atomic_write 存在且在册）。再往 codegen/runtime 补 makedirs 与
bool 归一要改 src/llvm/*，不在本卡 paths 内；而门面是两腿共用的语义层，改这里一处就两腿对齐。

## 验证（Windows 本机，clang 在 C:\Program Files\LLVM）

- 卡面判据 `python -m pytest -q tests/unit/test_原生腿_R11C_数据高级.py -k 复制文件_对拍`
  → **1 passed, exit 0**（改前改后都是绿的；改前绿证明 R164 已生效）。
- 整文件 `tests/unit/test_原生腿_R11C_数据高级.py` → **29 passed**（151s）。
- `python scripts/gen_native_capability_json.py --check` → **exit 0**（清单未动，仍自洽）。
- `tests/unit/test_native_leg_capability.py` → **11 passed**。
- `python tools/ci/llvm_stdlib_readiness.py --sample 文件系统` → **桶=可编，exit 0**。
- `test_R145_文件系统补齐.py` + `test_R148_文件系统补齐.py` → **11 passed**。
- `test_LH3_多级属性_原子写入_锁与告警.py` → 通过（Windows 跳过 1 条 chmod 专有用例，符合预期）。

## 遗留风险

- `tests/unit/test_R149_文件系统原语.py::*双腿对拍*` 与 `test_R150_文件系统锁.py::*双腿对拍*`
  共 4 条红：native 侧输出是乱码（`\ufffd`），属**本机控制台/编码环境**问题，与本次改动无关
  —— git stash 掉本卡改动后同样这 4 条红，已实测。
- `tests/test_pure_light_hook.py::test_magic_number_in_first_two_lines` 红，同样 stash 后仍红，
  是既有存量（报『光明』那段 .light 首行无魔数），不在 paths 内。
- 写丢父目录这条是**原生腿 runtime 的固有行为**，门面只兜住了 `原子写入` 这一个入口；
  其它直连 `_light_builtin.原子写入` 的调用方仍会踩到（当前 stdlib 内无第二处调用方）。
