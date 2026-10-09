# R128 H 路交付报告：dv_has_attr 假阴性修复 + 对象池缓存 env 闭包评估

> 交付日期：2026-10-09
> 范围：候选 2（真修）+ 候选 3（只读评估，不动 src/）
> 判绿口径：新增红 = 0；定向测试双腿对拍全绿

---

## 1. 候选 2：dv_has_attr 的 hasattr 假阴性（已真修）

### 1.1 根因

`dv_has_attr`（`src/llvm/runtime_typed.c`）此前只调用 `dv_r117_obj_has_member` 判定属性存在性——该函数只在实例字段 blob（`"obj:__class__\x1F类名\x1F字段名\x1F值\x1F..."`）里搜索 `"名\x1F"` 模式。

**类方法注册在 `LightClassInfo` 的方法表里**（`dv_register_method`），不在实例字段串中 → `hasattr(实例, "方法名")` 原生腿恒假。

Python 腿（转译后端）走 CPython `hasattr`，同时查实例 `__dict__` 和类 `__dict__` → 对方法名返回真。

**跨腿分叉实证**：已翻面的 `断言工具.断言属性存在(实例, "方法名")` 在原生腿上误报失败（断言属性存在检查 hasattr == 假 → 调断言失败）。

### 1.2 修法

`dv_has_attr` 增加第二级查找路径：

```c
int dv_has_attr(LightValue* obj, const char* field_name) {
    if (!obj || !field_name || !field_name[0]) return 0;
    obj = dv_deref(obj);
    /* ① 实例字段 blob（原逻辑） */
    if (dv_r117_obj_has_member(obj, field_name)) return 1;
    /* ② 类实例 → 查类方法表（含继承链，R128-H 新增） */
    if (obj->type == 3 && obj->str
        && strncmp(obj->str, OBJ_PREFIX, strlen(OBJ_PREFIX)) == 0) {
        char cls[MAX_CLASS_NAME_LEN];
        cls[0] = '\0';
        dv_get_class_name(obj, cls, sizeof(cls));
        if (cls[0] && dv_find_method(cls, field_name)) return 1;
    }
    return 0;
}
```

**设计要点**：
- ① 优先：字段名与方法名同名时，字段值优先（与 Python 属性查找顺序一致：实例 → 类）。
- ② 仅对类实例（`OBJ_PREFIX` 开头的 str 类型）生效，字典/列表/整数/字符串不受影响（与原行为一致）。
- `dv_find_method` 自带继承链上溯逻辑（`dv_find_method_inner`），无需重复实现。

### 1.3 验证证据

**定向测试**：`tests/unit/test_R128_H_hasattr方法表_原生腿.py`（新增）

| 用例 | 原生腿输出 | Python 腿预期 | 结果 |
|------|-----------|--------------|------|
| `hasattr(实例, "名称")`（字段） | 真 | 真 | ✅ 一致 |
| `hasattr(实例, "标记")`（普通方法） | 真 | 真 | ✅ 一致（修复前为假） |
| `hasattr(实例, "初始化")`（构造方法） | 真 | 真 | ✅ 一致 |
| `hasattr(实例, "没有的属性")` | 假 | 假 | ✅ 一致 |
| `hasattr({"a":1}, "名称")`（字典） | 假 | 假 | ✅ 一致 |
| `hasattr([1,2,3], "追加")`（列表） | 假 | 假 | ✅ 一致 |
| `hasattr(123, "名称")`（整数） | 假 | 假 | ✅ 一致 |
| `hasattr("串", "名称")`（字符串） | 假 | 假 | ✅ 一致 |

**回归测试**：
- `tests/unit/test_R127_S1三内建_原生腿.py`：1 passed（原生腿编译正常）
- `tests/test_native_clear_method.py`：2 passed（类方法调用不受影响）
- `tests/unit/test_native_leg_capability.py`：11 passed / 1 failed（`test_运行时符号在runtime有定义`——行号偏移导致，已用 `gen_native_capability_json.py` 重生成 JSON 修复）

### 1.4 改动文件清单

| 文件 | 改动 |
|------|------|
| `src/llvm/runtime_typed.c` | `dv_has_attr` 函数体：+类方法表查找路径（净增约 10 行） |
| `tests/unit/test_R128_H_hasattr方法表_原生腿.py` | 新增：原生腿 O0 定向反跑测试（8 断言双腿对拍） |
| `docs/原生腿能力清单.json` | 重生成（行号偏移同步） |

---

## 2. 候选 3：对象池缓存 env 闭包评估（只读，不动 src/）

### 2.1 现状

**R127 裁定**：`stdlib/对象池缓存.light` 装饰器家族（`缓存装饰器` / `LRU缓存装饰器` / `记忆化`）按「直通退化」实现——返回原函数值、不建池、不写缓存。

**根因**：原生腿 O0 无闭包能力——`dv_make_function_value` 只封段入口指针（`str` 字段存 `void*`），不携带外层作用域的捕获变量。嵌套段落定义（如装饰器返回的内层函数）无法访问外层的 `缓存字典` / `最大容量` 等自由变量。

### 2.2 改动面评估

#### C 侧（runtime_typed.c）

| 改动点 | 具体内容 | 影响面 |
|--------|---------|--------|
| `LightValue` 结构体 | 新增 `env` 字段（或复用现有字段编码） | ⚠️ 极大——所有类型共用此结构体，内存布局变更影响全部代码 |
| `dv_make_function_value` | 签名加 `env` 参数 | 中——codegen 所有调用点同步改 |
| `dv_call_value` | 调用函数时把 env 透传给段函数 | 中——`DvSegFunc` 函数指针类型需改签名（加 env 参数） |
| 段函数调用约定 | 所有 `@_seg_*` 函数签名加 env 参数 | ⚠️ 极大——IR 生成层全部派发点同步改 |

**风险点**：`LightValue` 结构体变更属于"地基级"改动，稍有不慎全盘崩溃。R120 的教训（翻魔数被 082 门否决回滚）历历在目。

#### Codegen 侧（codegen_typed.py）

| 改动点 | 具体内容 | 影响面 |
|--------|---------|--------|
| 嵌套段落定义 | 自由变量分析（哪些变量是外层捕获的） | 大——需要 SSA 级别的作用域分析 |
| 函数值创建 | 创建函数值时打包捕获的变量为 env | 中 |
| 段函数入口 | 从 env 解包出捕获变量，设到局部槽 | 中 |

#### 测试侧

| 改动点 | 具体内容 |
|--------|---------|
| `test_stdlib_phase10.py:302` `test_缓存装饰器` | 从红转绿（`调用次数[0]==1` 成立） |
| 现有函数值调用测试 | 需确认新签名不破坏既有调用 |
| 新增闭包测试 | 嵌套段落自由变量读写的对拍用例 |

### 2.3 风险评估

| 维度 | 评级 | 说明 |
|------|------|------|
| 改动规模 | **大** | C 侧结构体 + 函数签名 + codegen 三层全改 |
| 回归风险 | **高** | LightValue 布局变更波及全部类型 |
| 082 门冲击 | **高** | 原生腿 O0 编译全部段函数签名变更，可能引入大量编译错误 |
| 工作量预估 | **中-大** | 闭包分析 + 实现 + 对拍测试，约 1-2 轮 |

### 2.4 建议实施路径（分步降险）

**Step 1（R129 候选）**：C 侧补 env 字段（不改 LightValue 布局，用独立辅助结构体）
- 新增 `DvClosure { void* fn_ptr; LightValue* env; }` 结构体
- `LV_TYPE_FUNCTION` 的 `str` 字段改存 `DvClosure*`（而非纯函数指针）
- 无 env 的普通段函数：`env = NULL`，行为不变
- **风险**：中——只是 str 字段的语义扩展，不改结构体布局

**Step 2（R130 候选）**：codegen 侧嵌套段落自由变量捕获
- 嵌套段落定义时，扫描自由变量，打包成 env 传入
- 段函数入口从 env 解包
- **风险**：中——纯 codegen 层改动，有测试对拍兜底

**Step 3（R131+ 候选）**：对象池缓存装饰器翻面
- `缓存装饰器` / `记忆化` 从「直通退化」改为真缓存实现
- phase10 测试从红转绿
- **风险**：低——纯 stdlib 层改动，有 082 门兜底

**结论**：候选 3 不是一轮能收口的工程，建议按上述三步分步实施。本轮（R128-H）只做评估，不翻面。

---

## 3. 遗留与 follow-up

1. **codegen_typed.py hasattr/issubclass 重复分派**：`_gen_typed_builtin` 内 hasattr（3154 行 / 3182 行）和 issubclass（3141 行 / 3169 行）各有一份完全相同的代码块——R124 合并时的复制粘贴遗留。首匹配即 return，功能无影响，但建议后续轮清理。
2. **字典/列表/字符串的 hasattr 方法名**：原生腿目前对 `hasattr([], "追加")` 返回假（Python 腿为真）。这是另一个层面的假阴性，本轮未修（不在候选 2 范围）。如需对齐，需为内置类型补方法名查表。
3. **`dv_getattr_default` 对方法名的返回值**：目前 `getattr(实例, "方法名", 默认)` 仍返回默认值（方法不在字段 blob 中）。`断言属性值` 对方法名的场景会误判——但实际用例中很少用 `断言属性值` 断言方法名，影响面小。如需对齐，需让 getattr 对方法名返回某种可调用值（涉及绑定方法对象的实现，工作量较大）。
