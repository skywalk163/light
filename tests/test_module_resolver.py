#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光明模块解析器测试

测试：
1. 模块查找
2. 模块解析
3. 依赖图构建
4. 循环依赖检测
5. 拓扑排序
"""

import sys
import os
from pathlib import Path

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from module_resolver import (
    ModuleResolver, ModuleLoader, ModuleInfo,
    ModuleNotFoundError, CircularDependencyError
)


def test_find_module():
    """测试模块查找"""
    print("="*60)
    print("测试1: 模块查找")
    print("="*60)
    
    test_dir = Path("examples/modules")
    resolver = ModuleResolver(search_paths=[str(test_dir)])
    
    # 测试存在的模块
    try:
        path = resolver.find_module("math_utils")
        print(f"[OK] 找到 math_utils: {path}")
        assert path.name == "math_utils.light"
    except ModuleNotFoundError as e:
        print(f"[FAIL] 未找到模块: {e}")
        return False
    
    # 测试不存在的模块
    try:
        path = resolver.find_module("nonexistent")
        print(f"[FAIL] 不应该找到 nonexistent 模块")
        return False
    except ModuleNotFoundError as e:
        print(f"[OK] 正确报错: 模块未找到")
    
    return True


def test_parse_module():
    """测试模块解析"""
    print("\n" + "="*60)
    print("测试2: 模块解析")
    print("="*60)
    
    test_dir = Path("examples/modules")
    resolver = ModuleResolver(search_paths=[str(test_dir)])
    
    # 解析 math_utils
    path = resolver.find_module("math_utils")
    module = resolver.parse_module(path)
    
    print(f"模块名: {module.name}")
    print(f"依赖: {module.dependencies}")
    print(f"导出: {module.exports}")
    
    # 验证
    assert module.name == "math_utils"
    assert module.dependencies == set()
    assert "平方" in module.exports
    assert "立方" in module.exports
    
    print("[OK] 模块解析正确")
    return True


def test_dependency_graph():
    """测试依赖图构建"""
    print("\n" + "="*60)
    print("测试3: 依赖图构建")
    print("="*60)
    
    test_dir = Path("examples/modules")
    resolver = ModuleResolver(search_paths=[str(test_dir)])
    
    # 构建依赖图
    graph = resolver.build_dependency_graph("main", str(test_dir))
    
    print(f"依赖图节点数: {len(graph.nodes)}")
    print("模块列表:")
    for name, info in graph.nodes.items():
        print(f"  - {name}")
        print(f"    依赖: {info.dependencies}")
        print(f"    导出: {info.exports}")
    
    # 验证
    assert "main" in graph.nodes
    assert "math_utils" in graph.nodes
    assert "string_utils" in graph.nodes
    
    # 检查依赖关系
    main_deps = graph.get_dependencies("main")
    print(f"\nmain 的依赖: {main_deps}")
    assert "math_utils" in main_deps or "string_utils" in main_deps
    
    print("[OK] 依赖图构建正确")
    return True


def test_circular_dependency():
    """测试循环依赖检测"""
    print("\n" + "="*60)
    print("测试4: 循环依赖检测")
    print("="*60)
    
    test_dir = Path("examples/modules")
    resolver = ModuleResolver(search_paths=[str(test_dir)])
    
    # 构建依赖图
    graph = resolver.build_dependency_graph("main", str(test_dir))
    
    # 检测循环依赖
    cycle = resolver.detect_circular_dependency(graph)
    
    if cycle:
        print(f"[FAIL] 检测到循环依赖: {' -> '.join(cycle)}")
        return False
    else:
        print("[OK] 无循环依赖")
        return True


def test_topological_sort():
    """测试拓扑排序"""
    print("\n" + "="*60)
    print("测试5: 拓扑排序")
    print("="*60)
    
    test_dir = Path("examples/modules")
    resolver = ModuleResolver(search_paths=[str(test_dir)])
    
    # 构建依赖图
    graph = resolver.build_dependency_graph("main", str(test_dir))
    
    # 拓扑排序
    order = resolver.topological_sort(graph)
    
    print(f"编译顺序: {' -> '.join(order)}")
    
    # 验证顺序
    # 被依赖的模块应该在依赖它的模块之前编译
    # math_utils 和 string_utils 应该在 main 之前
    
    if "main" in order:
        main_index = order.index("main")
        
        # 检查依赖是否在 main 之前
        main_deps = graph.get_dependencies("main")
        for dep in main_deps:
            if dep in order:
                dep_index = order.index(dep)
                if dep_index > main_index:
                    print(f"[FAIL] 依赖 {dep} 应该在 main 之前编译")
                    return False
    
    print("[OK] 拓扑排序正确")
    return True


def test_full_resolution():
    """测试完整解析流程"""
    print("\n" + "="*60)
    print("测试6: 完整解析流程")
    print("="*60)
    
    test_dir = Path("examples/modules")
    main_file = test_dir / "main.light"
    
    if not main_file.exists():
        print(f"[SKIP] 测试文件不存在: {main_file}")
        return True
    
    resolver = ModuleResolver(search_paths=[str(test_dir)])
    
    try:
        modules, graph = resolver.resolve(str(main_file))
        
        print(f"解析成功，共 {len(modules)} 个模块")
        print("\n编译顺序:")
        for i, module in enumerate(modules, 1):
            print(f"  {i}. {module.name}")
            print(f"     路径: {module.path}")
            print(f"     依赖: {module.dependencies}")
            print(f"     导出: {module.exports}")
        
        print("\n[OK] 完整解析流程成功")
        return True
        
    except Exception as e:
        print(f"[FAIL] 解析失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_module_loader():
    """测试模块加载器"""
    print("\n" + "="*60)
    print("测试7: 模块加载器")
    print("="*60)
    
    test_dir = Path("examples/modules")
    loader = ModuleLoader(resolver=ModuleResolver(search_paths=[str(test_dir)]))
    
    try:
        # 加载单个模块
        module = loader.load("math_utils", str(test_dir))
        print(f"加载模块: {module.name}")
        print(f"  导出: {module.exports}")
        
        # 加载项目
        main_file = test_dir / "main.light"
        if main_file.exists():
            modules = loader.load_project(str(main_file))
            print(f"\n加载项目成功，共 {len(modules)} 个模块")
            for m in modules:
                print(f"  - {m.name}")
        
        print("\n[OK] 模块加载器测试成功")
        return True
        
    except Exception as e:
        print(f"[FAIL] 加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """运行所有测试"""
    print("="*60)
    print("光明模块解析器测试套件")
    print("="*60)
    print()
    
    tests = [
        ("模块查找", test_find_module),
        ("模块解析", test_parse_module),
        ("依赖图构建", test_dependency_graph),
        ("循环依赖检测", test_circular_dependency),
        ("拓扑排序", test_topological_sort),
        ("完整解析流程", test_full_resolution),
        ("模块加载器", test_module_loader),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n[ERROR] 测试 {name} 异常: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    for name, result in results:
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} {name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print(f"\n通过: {passed}/{total}")
    
    if passed == total:
        print("\n恭喜！所有测试通过！")
        return True
    else:
        print(f"\n有 {total - passed} 个测试失败")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
