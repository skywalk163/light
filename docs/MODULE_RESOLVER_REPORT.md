# 光明模块解析器实现报告

**日期**: 2026-06-10
**版本**: v0.9.1
**状态**: ✅ 核心功能实现完成

---

## 一、实现概览

### 1.1 已实现功能

| 功能 | 状态 | 说明 |
|------|------|------|
| 模块查找 | ✅ 完成 | 支持多路径搜索、环境变量 |
| 模块解析 | ✅ 完成 | 提取导入/导出信息 |
| 依赖图构建 | ✅ 完成 | 递归解析所有依赖 |
| 循环依赖检测 | ✅ 完成 | DFS算法检测环 |
| 拓扑排序 | ✅ 完成 | Kahn算法确定编译顺序 |
| 模块加载器 | ✅ 完成 | 统一加载接口 |

### 1.2 核心代码

```
src/module_resolver.py (约500行)
├── ModuleError             # 错误基类
├── ModuleNotFoundError     # 模块未找到错误
├── CircularDependencyError # 循环依赖错误
├── ModuleInfo              # 模块信息数据结构
├── DependencyGraph         # 依赖图数据结构
├── ModuleResolver          # 模块解析器（核心）
└── ModuleLoader            # 模块加载器
```

---

## 二、使用示例

### 2.1 查找模块

```python
from module_resolver import ModuleResolver

resolver = ModuleResolver(search_paths=['examples/modules'])

# 查找模块文件
path = resolver.find_module('math_utils')
print(path)  # /path/to/examples/modules/math_utils.light
```

### 2.2 解析模块

```python
# 解析模块文件
module = resolver.parse_module(path)

print(f"模块名: {module.name}")
print(f"依赖: {module.dependencies}")
print(f"导出: {module.exports}")
```

### 2.3 构建依赖图

```python
# 构建整个项目的依赖图
graph = resolver.build_dependency_graph('main', 'examples/modules')

# 查看所有模块
for name, info in graph.nodes.items():
    print(f"{name}: depends on {info.dependencies}")
```

### 2.4 检测循环依赖

```python
# 检测循环依赖
cycle = resolver.detect_circular_dependency(graph)

if cycle:
    print(f"检测到循环依赖: {' → '.join(cycle)}")
else:
    print("无循环依赖")
```

### 2.5 拓扑排序

```python
# 获取编译顺序
order = resolver.topological_sort(graph)
print(f"编译顺序: {' → '.join(order)}")
# 输出: math_utils → string_utils → main
```

### 2.6 完整解析

```python
# 一步完成所有操作
modules, graph = resolver.resolve('examples/modules/main.light')

for module in modules:
    print(f"{module.name}: {module.path}")
```

---

## 三、API参考

### 3.1 ModuleResolver

```python
class ModuleResolver:
    def __init__(self, search_paths: List[str] = None):
        """初始化解析器，可指定搜索路径"""
    
    def find_module(self, module_name: str, from_dir: str = None) -> Path:
        """查找模块文件路径"""
    
    def parse_module(self, module_path: Path) -> ModuleInfo:
        """解析模块文件，提取导入/导出信息"""
    
    def build_dependency_graph(self, main_module: str, from_dir: str = None) -> DependencyGraph:
        """构建依赖图"""
    
    def detect_circular_dependency(self, graph: DependencyGraph) -> Optional[List[str]]:
        """检测循环依赖，返回环路径或None"""
    
    def topological_sort(self, graph: DependencyGraph) -> List[str]:
        """拓扑排序，返回编译顺序"""
    
    def resolve(self, main_file: str) -> Tuple[List[ModuleInfo], DependencyGraph]:
        """完整解析，返回模块列表和依赖图"""
```

### 3.2 ModuleLoader

```python
class ModuleLoader:
    def __init__(self, resolver: ModuleResolver = None):
        """初始化加载器"""
    
    def load(self, module_name: str, from_dir: str = None) -> ModuleInfo:
        """加载单个模块及其依赖"""
    
    def load_project(self, main_file: str) -> List[ModuleInfo]:
        """加载整个项目"""
```

---

## 四、错误处理

### 4.1 ModuleNotFoundError

```python
try:
    path = resolver.find_module('nonexistent')
except ModuleNotFoundError as e:
    print(f"模块未找到: {e.module_name}")
    print(f"搜索路径: {e.search_paths}")
```

### 4.2 CircularDependencyError

```python
try:
    modules, graph = resolver.resolve('main.light')
except CircularDependencyError as e:
    print(f"检测到循环依赖: {' → '.join(e.cycle)}")
```

---

## 五、算法说明

### 5.1 模块查找算法

```
搜索顺序：
1. 当前目录（如果指定 from_dir）
2. search_paths 参数指定的路径
3. DUAN_PATH 环境变量指定的路径

文件定位：
- 模块名 math_utils → 文件名 math_utils.light
```

### 5.2 循环依赖检测算法

使用 DFS（深度优先搜索）和三色标记：
- WHITE (0): 未访问
- GRAY (1): 正在访问
- BLACK (2): 已完成访问

当遇到 GRAY 节点时，说明发现环。

### 5.3 拓扑排序算法

使用 Kahn 算法：
1. 计算每个节点的入度
2. 将入度为 0 的节点加入队列
3. 依次处理队列中的节点，更新依赖节点的入度
4. 如果队列为空但仍有未处理节点，说明有环

---

## 六、性能考虑

### 6.1 模块缓存

```python
# ModuleResolver 内置缓存
self.module_cache: Dict[str, ModuleInfo] = {}

# 避免重复解析同一个模块
if module_name in self.module_cache:
    return self.module_cache[module_name]
```

### 6.2 延迟加载

```python
# ModuleLoader 只在需要时加载依赖
for dep_name in module_info.dependencies:
    if dep_name not in self.loaded_modules:
        self.load(dep_name, module_dir)
```

---

## 七、测试验证

### 7.1 已验证功能

- ✅ 模块查找（单模块）
- ✅ 模块解析（提取导入/导出）
- ✅ 错误处理（模块未找到）

### 7.2 待优化问题

1. **性能优化** - 大型项目可能需要优化递归深度
2. **错误信息** - 提供更友好的错误提示
3. **相对导入** - 支持 `.` 和 `..` 相对路径导入

---

## 八、示例项目结构

```
examples/modules/
├── main.light          # 主程序
│   └── 导入: math_utils, string_utils
│
├── math_utils.light    # 数学工具模块
│   └── 导出: 平方, 立方
│
└── string_utils.light  # 字符串工具模块
    └── 导出: 连接
```

**编译顺序**:
1. math_utils.light
2. string_utils.light
3. main.light

---

## 九、下一步工作

### 9.1 短期优化

1. **性能优化** - 减少重复解析，提升速度
2. **错误增强** - 更友好的错误信息和位置提示
3. **相对导入** - 支持相对路径模块导入

### 9.2 集成编译器

将模块解析器集成到 CLI 工具：

```bash
# 编译整个项目
duanc main.light --project

# 显示依赖图
duanc main.light --deps

# 生成 Makefile
duanc main.light --makefile
```

---

## 十、参考资料

- [模块系统设计文档](docs/module_system_design.md)
- [模块系统验证报告](docs/MODULE_SYSTEM_VERIFICATION.md)
- Python importlib 源码
- Node.js require 实现
