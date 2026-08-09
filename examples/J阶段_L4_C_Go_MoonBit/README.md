# J 阶段：L4 C / Go / MoonBit 真实编译封装

> 设计文档：[分层语法设计_v4.0.md](../../docs/分层语法设计_v4.0.md) · 代码生成：[src/code_generator.py](../../src/code_generator.py)

## 概述

J 阶段使光明的 L4 外语引用层支持 C、Go、MoonBit 三种语言的**真实编译调用**，而不仅仅是注释保留。

| 语言 | 关键字 | 实现机制 | 运行环境要求 |
|------|--------|----------|-------------|
| C | `引 C:` | gcc/clang/cc → .so/.dll → ctypes 加载 | gcc/clang/cc 任一 |
| Go | `引 Go:` | go build -buildmode=c-shared → .so/.dll → ctypes 加载 | Go 工具链 |
| MoonBit | `引 MoonBit:` | moon build --target wasm → wasmtime 执行 | MoonBit + wasmtime |

## 示例

### J1：C 快速求和

```光明
引 C:
    double 快速求和(double* arr, int n) {
        double s = 0.0;
        for (int i = 0; i < n; i++) s += arr[i];
        return s;
    }
打印 快速求和(1,2,3,4,5)    # 15.0
```

→ `run: light run examples/J阶段_L4_C_Go_MoonBit/J1_C_快速求和.light`

### J2：Go 斐波那契 + 求和

```光明
引 Go:
    //export 斐波那契
    func 斐波那契(n int) int {
        if n <= 1 { return n }
        return 斐波那契(n-1) + 斐波那契(n-2)
    }
打印 斐波那契(10)    # 55
```

→ `run: light run examples/J阶段_L4_C_Go_MoonBit/J2_Go_斐波那契.light`

### J3：MoonBit 快速排序

```光明
引 MoonBit:
    fn main {
        let arr = [3, 1, 4, 1, 5, 9, 2, 6]
        let sorted = quick_sort(arr)
        println("Sorted: \{sorted}")
    }
```

→ `run: light run examples/J阶段_L4_C_Go_MoonBit/J3_MoonBit_快速排序.light`

## 技术细节

### C 嵌入
- 自动检测编译器：gcc → cc → clang
- 平台自适应：Windows `.dll`, Linux/macOS `.so`
- 自动添加 `#include <stdlib.h> <string.h> <math.h>`
- 自动解析 C 函数签名，生成 ctypes 可调用封装
- 编译失败时返回占位错误字符串

### Go 嵌入
- 自动包装为 `package main` + `import "C"`
- 自动初始化 `go.mod`
- 通过 `//export FuncName` 注释识别导出函数
- 编译为 c-shared 库后通过 ctypes 加载

### MoonBit 嵌入
- 自动创建临时项目 + `moon.pkg.json`
- 编译为 wasm 目标
- 通过 `wasmtime` 执行
- 支持多路径 wasm 查找（release/debug）