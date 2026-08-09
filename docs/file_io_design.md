# 光明文件I/O设计文档

**版本**: v1.0.0  
**日期**: 2026-06-10  
**状态**: 设计中

---

## 一、设计目标

1. **简洁易用** - 中文API，符合光明语法风格
2. **功能完整** - 覆盖编译器所需的文件操作
3. **安全可靠** - 提供错误处理机制
4. **跨平台** - 支持Windows/Linux/macOS

---

## 二、文件I/O API设计

### 2.1 文件读取

#### 读取整个文件

```光明
# 方式1：内置函数
定义内容等于读取文件参数"input.light"。

# 方式2：文件对象
定义文件等于打开文件参数"input.light"，"r"。
定义内容等于文件.读取全部。
文件.关闭。
```

#### 逐行读取

```光明
# 逐行读取
定义文件等于打开文件参数"input.light"，"r"。
遍历行于文件.行列表：
  打印行。
文件.关闭。
```

### 2.2 文件写入

#### 写入整个文件

```光明
# 方式1：内置函数
写入文件参数"output.py"，内容。

# 方式2：文件对象
定义文件等于打开文件参数"output.py"，"w"。
文件.写入参数内容。
文件.关闭。
```

#### 追加写入

```光明
定义文件等于打开文件参数"log.txt"，"a"。
文件.写入参数"新日志行\n"。
文件.关闭。
```

### 2.3 文件系统操作

#### 文件存在检查

```光明
如果文件存在参数"config.light"那么
  打印"配置文件存在"。
否则
  打印"配置文件不存在"。
```

#### 目录操作

```光明
# 创建目录
创建目录参数"output"。

# 检查目录存在
如果目录存在参数"output"那么
  打印"目录已存在"。

# 列出目录内容
定义文件列表等于列出目录参数"."。
遍历文件名于文件列表：
  打印文件名。
```

#### 文件信息

```光明
# 文件大小
定义大小等于文件大小参数"data.txt"。
打印大小。

# 文件路径操作
定义绝对路径等于绝对路径参数"./data.txt"。
定义文件名等于文件名参数"/path/to/file.txt"。
定义目录名等于目录名参数"/path/to/file.txt"。
```

---

## 三、标准库设计

### 3.1 系统模块（系统）

```光明
导入《系统》。

# 文件操作
定义内容等于《系统.读取文件》参数"input.txt"。
《系统.写入文件》参数"output.txt"，内容。

# 路径操作
定义路径等于《系统.绝对路径》参数"."

# 环境变量
定义家目录等于《系统.环境变量》参数"HOME"。

# 命令行参数
定义参数列表等于《系统.参数列表》。
```

### 3.2 文件模块（文件）

```光明
导入《文件》。

# 打开文件
定义文件等于《文件.打开》参数"data.txt"，"r"。

# 读取操作
定义内容等于文件.读取全部。
定义行列表等于文件.行列表。
定义首行等于文件.读取行。

# 写入操作
文件.写入参数"Hello\n"。
文件.写入行参数"World"。

# 关闭文件
文件.关闭。
```

### 3.3 路径模块（路径）

```光明
导入《路径》。

# 路径拼接
定义完整路径等于《路径.连接》参数"dir"，"file.txt"。

# 路径分解
定义目录等于《路径.目录》参数"/a/b/c.txt"。
定义文件名等于《路径.文件名》参数"/a/b/c.txt"。
定义扩展名等于《路径.扩展名》参数"/a/b/c.txt"。

# 路径检查
如果《路径.存在》参数"/a/b"那么
  打印"路径存在"。
```

---

## 四、内置函数实现

### 4.1 文件读取函数

**光明代码**:
```光明
《读取文件》段(路径)：
  定义文件等于打开文件参数路径，"r"。
  定义内容等于文件.读取全部。
  文件.关闭。
  返回内容。
```

**生成的Python代码**:
```python
def 读取文件(路径):
    with open(路径, 'r', encoding='utf-8') as 文件:
        内容 = 文件.read()
    return 内容
```

### 4.2 文件写入函数

**光明代码**:
```光明
《写入文件》段(路径, 内容)：
  定义文件等于打开文件参数路径，"w"。
  文件.写入参数内容。
  文件.关闭。
```

**生成的Python代码**:
```python
def 写入文件(路径, 内容):
    with open(路径, 'w', encoding='utf-8') as 文件:
        文件.write(内容)
```

### 4.3 文件存在检查

**光明代码**:
```光明
《文件存在》段(路径)：
  返回路径存在检查参数路径。
```

**生成的Python代码**:
```python
import os

def 文件存在(路径):
    return os.path.exists(路径)
```

---

## 五、运行时库实现

### 5.1 内置函数映射

在 `code_generator.py` 中添加：

```python
# 内置函数映射
self.builtin_map = {
    # 现有映射
    '打印': 'print',
    '读取': 'input',
    '长': 'len',
    
    # 文件I/O映射
    '读取文件': '_light_read_file',
    '写入文件': '_light_write_file',
    '文件存在': '_light_file_exists',
    '目录存在': '_light_dir_exists',
    '创建目录': '_light_mkdir',
    '列出目录': '_light_listdir',
    '文件大小': '_light_file_size',
    '删除文件': '_light_remove_file',
    '删除目录': '_light_rmdir',
}
```

### 5.2 运行时库文件

创建 `src/stdlib/builtins.py`:

```python
"""
光明标准库 - 内置函数实现
"""

import os
import sys
from pathlib import Path
from typing import List, Optional


# =============================================================================
# 文件I/O函数
# =============================================================================

def _light_read_file(path: str, encoding: str = 'utf-8') -> str:
    """读取文件内容"""
    try:
        with open(path, 'r', encoding=encoding) as f:
            return f.read()
    except Exception as e:
        raise RuntimeError(f"读取文件失败 '{path}': {e}")


def _light_write_file(path: str, content: str, encoding: str = 'utf-8') -> None:
    """写入文件内容"""
    try:
        # 确保目录存在
        dir_path = os.path.dirname(path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)
        
        with open(path, 'w', encoding=encoding) as f:
            f.write(content)
    except Exception as e:
        raise RuntimeError(f"写入文件失败 '{path}': {e}")


def _light_file_exists(path: str) -> bool:
    """检查文件是否存在"""
    return os.path.isfile(path)


def _light_dir_exists(path: str) -> bool:
    """检查目录是否存在"""
    return os.path.isdir(path)


def _light_mkdir(path: str) -> None:
    """创建目录"""
    try:
        os.makedirs(path, exist_ok=True)
    except Exception as e:
        raise RuntimeError(f"创建目录失败 '{path}': {e}")


def _light_listdir(path: str = '.') -> List[str]:
    """列出目录内容"""
    try:
        return os.listdir(path)
    except Exception as e:
        raise RuntimeError(f"列出目录失败 '{path}': {e}")


def _light_file_size(path: str) -> int:
    """获取文件大小（字节）"""
    try:
        return os.path.getsize(path)
    except Exception as e:
        raise RuntimeError(f"获取文件大小失败 '{path}': {e}")


def _light_remove_file(path: str) -> None:
    """删除文件"""
    try:
        os.remove(path)
    except Exception as e:
        raise RuntimeError(f"删除文件失败 '{path}': {e}")


def _light_rmdir(path: str) -> None:
    """删除目录"""
    try:
        os.rmdir(path)
    except Exception as e:
        raise RuntimeError(f"删除目录失败 '{path}': {e}")


# =============================================================================
# 路径操作函数
# =============================================================================

def _light_abs_path(path: str) -> str:
    """获取绝对路径"""
    return os.path.abspath(path)


def _light_join_path(*paths: str) -> str:
    """连接路径"""
    return os.path.join(*paths)


def _light_dirname(path: str) -> str:
    """获取目录名"""
    return os.path.dirname(path)


def _light_basename(path: str) -> str:
    """获取文件名"""
    return os.path.basename(path)


def _light_splitext(path: str) -> tuple:
    """分割文件名和扩展名"""
    return os.path.splitext(path)


# =============================================================================
# 系统函数
# =============================================================================

def _light_getenv(name: str, default: str = None) -> Optional[str]:
    """获取环境变量"""
    return os.environ.get(name, default)


def _light_setenv(name: str, value: str) -> None:
    """设置环境变量"""
    os.environ[name] = value


def _light_argv() -> List[str]:
    """获取命令行参数"""
    return sys.argv


def _light_exit(code: int = 0) -> None:
    """退出程序"""
    sys.exit(code)
```

---

## 六、使用示例

### 6.1 编译器自举示例

```光明
# 简单编译器示例

从《系统》导入《读取文件》，《写入文件》，《文件存在》。

《编译》段(输入路径, 输出路径)：
  # 检查输入文件
  如果非《文件存在》参数输入路径那么
    打印"错误：输入文件不存在"。
    返回假。
  
  # 读取源代码
  定义源代码等于《读取文件》参数输入路径。
  
  # 编译（简化示例）
  打印"编译中..."。
  定义目标代码等于源代码。
  
  # 写入输出文件
  《写入文件》参数输出路径，目标代码。
  
  打印"编译完成"。
  返回真。


# 主程序
定义输入等于"main.light"。
定义输出等于"main.py"。

定义成功等于《编译》参数输入，输出。
如果成功那么
  打印"成功！"。
否则
  打印"失败！"。
```

### 6.2 文件处理示例

```光明
# 日志文件处理

导入《系统》。

《处理日志》段(日志路径)：
  # 检查文件存在
  如果非《系统.文件存在》参数日志路径那么
    打印"日志文件不存在"。
    返回。
  
  # 读取日志
  定义内容等于《系统.读取文件》参数日志路径。
  
  # 处理日志（示例：统计行数）
  定义行数等于零。
  定义计数等于零。
  遍历字符于内容：
    如果字符等于"\n"那么
      定义行数等于行数加一。
  
  打印"总行数："。
  打印行数。
  
  # 写入统计结果
  《系统.写入文件》参数"统计.txt"，行数。
```

---

## 七、实现步骤

### 步骤1：创建运行时库（1天）

- 创建 `src/stdlib/builtins.py`
- 实现所有文件I/O函数
- 添加错误处理

### 步骤2：集成到代码生成器（1天）

- 扩展 `code_generator.py` 的内置函数映射
- 添加运行时库导入语句
- 测试文件I/O代码生成

### 步骤3：编写测试（1天）

- 文件读写测试
- 目录操作测试
- 错误处理测试

### 步骤4：文档和示例（1天）

- 编写用户手册
- 创建示例程序
- 更新API文档

---

## 八、安全考虑

### 8.1 路径安全

- 防止路径遍历攻击
- 限制访问范围（可选）

### 8.2 文件权限

- 检查文件权限
- 提供友好的错误提示

### 8.3 错误处理

- 所有文件操作都应该有try-except
- 提供清晰的错误信息
- 支持自定义错误处理

---

## 九、性能优化

### 9.1 大文件处理

- 支持流式读取
- 分块处理

### 9.2 缓冲机制

- 文件对象缓冲
- 批量写入

---

## 十、参考

- Python `os` 和 `pathlib` 模块
- Node.js `fs` 模块
- Rust `std::fs` 模块
