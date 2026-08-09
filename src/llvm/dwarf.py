"""DWARF 调试信息生成

为 LLVM IR 添加 DWARF 调试元数据，支持：
- 源文件信息（文件路径、行号、列号）
- 变量信息（变量名、类型、作用域）
- 函数信息（函数名、参数、行号范围）
- 类型信息（基础类型、结构体、指针）
- 变量作用域（词法块嵌套）
- 行号映射（源码行号到 IR 的映射）
- 类型描述（复合类型、数组、指针）
"""

import os
from typing import List, Optional, Dict, Tuple


class DwarfScope:
    """DWARF 作用域

    表示一个词法作用域，支持嵌套。
    """

    def __init__(self, scope_id: str, parent_scope: Optional['DwarfScope'] = None,
                 line: int = 0, col: int = 0, file_id: str = None):
        self.scope_id = scope_id
        self.parent_scope = parent_scope
        self.line = line
        self.col = col
        self.file_id = file_id
        self.variables: List[str] = []  # 作用域中的变量名列表

    def add_variable(self, var_name: str):
        """添加变量到作用域"""
        if var_name not in self.variables:
            self.variables.append(var_name)


class DwarfDebugInfo:
    """DWARF 调试信息生成器

    为 LLVM IR 生成 DWARF 调试元数据，
    通过 LLVM 的 !dbg 元数据和 DI* 元数据节点实现。

    Attributes:
        source_file: 源文件路径
        _metadata: 元数据行列表
        _metadata_counter: 元数据节点计数器
        _compile_unit_id: 编译单元元数据 ID
        _file_id: 文件元数据 ID
        _func_metadata: 函数元数据映射
        _var_metadata: 变量元数据映射
        _type_metadata: 类型元数据映射
        _scope_stack: 作用域栈
        _line_mapping: 行号映射表
        _scope_map: 作用域映射
    """

    def __init__(self, source_file: str):
        """初始化 DWARF 调试信息生成器

        Args:
            source_file: 源文件路径
        """
        self.source_file = source_file
        self._metadata: List[str] = []
        self._metadata_counter = 0
        self._compile_unit_id = None
        self._file_id = None
        self._func_metadata: Dict[str, str] = {}
        self._var_metadata: Dict[str, str] = {}
        self._type_metadata: Dict[str, str] = {}
        self._scope_stack: List[DwarfScope] = []
        self._line_mapping: List[Tuple[int, int, str]] = []  # (line, col, dbg_ref)
        self._scope_map: Dict[str, DwarfScope] = {}
        self._current_func_line = 0
        self._current_func_name = ''

    def _new_metadata_id(self) -> int:
        """生成新的元数据 ID"""
        self._metadata_counter += 1
        return self._metadata_counter

    def add_compile_unit(self):
        """添加编译单元

        生成 DWARF 编译单元元数据，包含源文件信息。
        """
        self._metadata_counter = 0
        file_id = self._new_metadata_id()
        cu_id = self._new_metadata_id()

        self._file_id = file_id
        self._compile_unit_id = cu_id

        # 文件条目
        escaped_path = self.source_file.replace('\\', '/')
        escaped_dir = os.path.dirname(self.source_file).replace('\\', '/')
        self._metadata.append(f'!{file_id} = !DIFile(filename: "{escaped_path}", directory: "{escaped_dir}")')

        # 编译单元
        self._metadata.append(
            f'!{cu_id} = !DICompileUnit('
            f'language: DW_LANG_C, '
            f'file: !{file_id}, '
            f'producer: "光明编译器 1.0", '
            f'isOptimized: true, '
            f'flags: "", '
            f'runtimeVersion: 0, '
            f'splitDebugInlining: false, '
            f'nameTableKind: None'
            f')'
        )

        # 创建根作用域
        root_scope = DwarfScope(
            scope_id=f'!{cu_id}',
            line=1,
            col=0,
            file_id=f'!{file_id}'
        )
        self._scope_map[f'!{cu_id}'] = root_scope

    def add_function(self, name: str, line: int, filename: str = None) -> str:
        """添加函数调试信息

        Args:
            name: 函数名
            line: 函数定义所在行号
            filename: 源文件名（可选，默认使用编译单元的文件）

        Returns:
            函数元数据 ID 字符串（如 "!3"）
        """
        if self._file_id is None:
            self.add_compile_unit()

        subprogram_id = self._new_metadata_id()
        func_file_id = self._file_id

        if filename and filename != self.source_file:
            func_file_id = self._new_metadata_id()
            escaped = filename.replace('\\', '/')
            self._metadata.append(f'!{func_file_id} = !DIFile(filename: "{escaped}", directory: "")')

        # 创建函数类型（简化版）
        func_type_id = self._create_function_type()

        self._metadata.append(
            f'!{subprogram_id} = !DISubprogram('
            f'name: "{name}", '
            f'linkageName: "{name}", '
            f'scope: !{self._compile_unit_id}, '
            f'file: !{func_file_id}, '
            f'line: {line}, '
            f'type: {func_type_id}, '
            f'scopeLine: {line}, '
            f'spFlags: DISPFlagDefinition, '
            f'unit: !{self._compile_unit_id}'
            f')'
        )

        self._func_metadata[name] = f'!{subprogram_id}'
        self._current_func_name = name
        self._current_func_line = line

        # 创建函数级作用域
        func_scope = DwarfScope(
            scope_id=f'!{subprogram_id}',
            parent_scope=self._scope_map.get(f'!{self._compile_unit_id}'),
            line=line,
            col=1,
            file_id=f'!{func_file_id}'
        )
        self._scope_map[f'!{subprogram_id}'] = func_scope
        self._scope_stack.append(func_scope)

        return f'!{subprogram_id}'

    def _create_function_type(self) -> str:
        """创建函数类型元数据

        Returns:
            函数类型元数据 ID 字符串
        """
        type_id = self._new_metadata_id()
        ret_type_id = self._new_metadata_id()
        # 返回类型 void
        self._metadata.append(
            f'!{ret_type_id} = !DIBasicType('
            f'name: "void", '
            f'size: 0, '
            f'encoding: DW_ATE_unsigned'
            f')'
        )
        self._metadata.append(
            f'!{type_id} = !DISubroutineType('
            f'types: !{{{ret_type_id}}}'
            f')'
        )
        return f'!{type_id}'

    def add_variable(self, name: str, type_name: str, line: int, col: int = 0) -> str:
        """添加变量调试信息

        Args:
            name: 变量名
            type_name: 类型名
            line: 变量声明所在行号
            col: 列号

        Returns:
            变量元数据 ID 字符串
        """
        var_id = self._new_metadata_id()
        type_id = self._get_or_create_type(type_name)

        # 获取当前作用域
        current_scope = self._scope_stack[-1] if self._scope_stack else None
        scope_ref = f'!{self._compile_unit_id}'
        if current_scope:
            scope_ref = current_scope.scope_id
            current_scope.add_variable(name)

        # 获取文件 ID
        file_ref = f'!{self._file_id}'
        if current_scope and current_scope.file_id:
            file_ref = current_scope.file_id

        self._metadata.append(
            f'!{var_id} = !DILocalVariable('
            f'name: "{name}", '
            f'scope: {scope_ref}, '
            f'file: {file_ref}, '
            f'line: {line}, '
            f'type: {type_id}, '
            f'arg: 0, '
            f'align: 8'
            f')'
        )

        self._var_metadata[name] = f'!{var_id}'
        return f'!{var_id}'

    def add_parameter(self, name: str, type_name: str, line: int, arg_no: int, col: int = 0) -> str:
        """添加函数参数调试信息

        Args:
            name: 参数名
            type_name: 类型名
            line: 参数所在行号
            arg_no: 参数序号（从 1 开始）
            col: 列号

        Returns:
            参数元数据 ID 字符串
        """
        var_id = self._new_metadata_id()
        type_id = self._get_or_create_type(type_name)

        # 获取当前作用域
        current_scope = self._scope_stack[-1] if self._scope_stack else None
        scope_ref = f'!{self._compile_unit_id}'
        if current_scope:
            scope_ref = current_scope.scope_id
            current_scope.add_variable(name)

        file_ref = f'!{self._file_id}'
        if current_scope and current_scope.file_id:
            file_ref = current_scope.file_id

        self._metadata.append(
            f'!{var_id} = !DILocalVariable('
            f'name: "{name}", '
            f'scope: {scope_ref}, '
            f'file: {file_ref}, '
            f'line: {line}, '
            f'type: {type_id}, '
            f'arg: {arg_no}, '
            f'align: 8'
            f')'
        )

        self._var_metadata[name] = f'!{var_id}'
        return f'!{var_id}'

    def add_lexical_block(self, line: int, col: int = 0) -> str:
        """添加词法块（作用域块）

        用于表示 if、while、for 等语句的内部作用域。

        Args:
            line: 块开始行号
            col: 列号

        Returns:
            词法块元数据 ID 字符串
        """
        lex_block_id = self._new_metadata_id()

        # 获取父作用域
        parent_scope = self._scope_stack[-1] if self._scope_stack else self._scope_map.get(
            f'!{self._compile_unit_id}')
        parent_ref = parent_scope.scope_id if parent_scope else f'!{self._compile_unit_id}'

        file_ref = f'!{self._file_id}'
        if parent_scope and parent_scope.file_id:
            file_ref = parent_scope.file_id

        self._metadata.append(
            f'!{lex_block_id} = !DILexicalBlock('
            f'scope: {parent_ref}, '
            f'file: {file_ref}, '
            f'line: {line}, '
            f'column: {col}'
            f')'
        )

        # 创建并压入作用域栈
        new_scope = DwarfScope(
            scope_id=f'!{lex_block_id}',
            parent_scope=parent_scope,
            line=line,
            col=col,
            file_id=file_ref
        )
        self._scope_map[f'!{lex_block_id}'] = new_scope
        self._scope_stack.append(new_scope)

        return f'!{lex_block_id}'

    def add_type(self, name: str, size: int, encoding: str = 'DW_ATE_unsigned') -> str:
        """添加类型调试信息

        Args:
            name: 类型名
            size: 类型大小（字节）
            encoding: DWARF 编码方式

        Returns:
            类型元数据 ID 字符串
        """
        type_id = self._new_metadata_id()
        self._metadata.append(
            f'!{type_id} = !DIBasicType('
            f'name: "{name}", '
            f'size: {size * 8}, '  # 位
            f'encoding: {encoding}'
            f')'
        )
        self._type_metadata[name] = f'!{type_id}'
        return f'!{type_id}'

    def add_pointer_type(self, name: str, pointee_type: str) -> str:
        """添加指针类型调试信息

        Args:
            name: 指针类型名
            pointee_type: 指向的类型名

        Returns:
            类型元数据 ID 字符串
        """
        type_id = self._new_metadata_id()
        base_type = self._get_or_create_type(pointee_type)

        self._metadata.append(
            f'!{type_id} = !DIDerivedType('
            f'tag: DW_TAG_pointer_type, '
            f'name: "{name}", '
            f'size: 64, '
            f'baseType: {base_type}'
            f')'
        )
        self._type_metadata[name] = f'!{type_id}'
        return f'!{type_id}'

    def add_array_type(self, name: str, element_type: str, count: int) -> str:
        """添加数组类型调试信息

        Args:
            name: 数组类型名
            element_type: 元素类型名
            count: 元素个数

        Returns:
            类型元数据 ID 字符串
        """
        type_id = self._new_metadata_id()
        base_type = self._get_or_create_type(element_type)
        subrange_id = self._new_metadata_id()

        self._metadata.append(
            f'!{subrange_id} = !DISubrange(count: {count})'
        )

        self._metadata.append(
            f'!{type_id} = !DICompositeType('
            f'tag: DW_TAG_array_type, '
            f'name: "{name}", '
            f'baseType: {base_type}, '
            f'size: {count * 64}, '
            f'elements: !{{{subrange_id}}}'
            f')'
        )
        self._type_metadata[name] = f'!{type_id}'
        return f'!{type_id}'

    def add_struct_type(self, name: str, members: List[Tuple[str, str, int]]) -> str:
        """添加结构体类型调试信息

        Args:
            name: 结构体类型名
            members: 成员列表，每个元素为 (成员名, 类型名, 偏移量)

        Returns:
            类型元数据 ID 字符串
        """
        type_id = self._new_metadata_id()
        member_ids = []

        for member_name, member_type, offset in members:
            member_id = self._new_metadata_id()
            member_type_ref = self._get_or_create_type(member_type)
            member_ids.append(member_id)
            self._metadata.append(
                f'!{member_id} = !DIDerivedType('
                f'tag: DW_TAG_member, '
                f'name: "{member_name}", '
                f'scope: !{type_id}, '
                f'file: !{self._file_id}, '
                f'baseType: {member_type_ref}, '
                f'size: 64, '
                f'offset: {offset * 8}'
                f')'
            )

        member_list = ', '.join(member_ids)
        self._metadata.append(
            f'!{type_id} = !DICompositeType('
            f'tag: DW_TAG_structure_type, '
            f'name: "{name}", '
            f'size: {len(members) * 64}, '
            f'elements: !{{{member_list}}}'
            f')'
        )
        self._type_metadata[name] = f'!{type_id}'
        return f'!{type_id}'

    def add_line_entry(self, line: int, col: int, dbg_ref: str):
        """添加行号映射条目

        记录源码行号到 IR 调试信息的映射。

        Args:
            line: 源码行号
            col: 列号
            dbg_ref: 调试信息引用
        """
        self._line_mapping.append((line, col, dbg_ref))

    def get_line_mapping(self, line: int) -> Optional[str]:
        """获取指定行号的调试信息引用

        Args:
            line: 源码行号

        Returns:
            调试信息引用字符串，如 "!dbg !3"
        """
        for l, c, ref in reversed(self._line_mapping):
            if l == line:
                return ref
        return None

    def generate_metadata(self) -> str:
        """生成 LLVM 元数据字符串

        Returns:
            完整的 LLVM 元数据声明块
        """
        # 确保有编译单元
        if self._compile_unit_id is None:
            self.add_compile_unit()

        # 生成元数据行
        lines = []
        lines.append('!llvm.dbg.cu = !{!' + str(self._compile_unit_id) + '}')
        lines.append('!llvm.module.flags = !{!0, !1, !2}')
        lines.append('!0 = !{i32 2, !"Dwarf Version", i32 4}')
        lines.append('!1 = !{i32 2, !"Debug Info Version", i32 3}')
        lines.append('!2 = !{i32 2, !"CodeView", i32 1}')

        # 添加类型元数据
        for name, type_id in self._type_metadata.items():
            if 'DIBasicType' not in str(type_id):
                lines.append(f'{type_id} = !DIBasicType(name: "{name}", size: 64, encoding: DW_ATE_unsigned)')

        # 添加所有注册的元数据
        for meta_line in self._metadata:
            lines.append(meta_line)

        # 添加行号映射表作为注释
        if self._line_mapping:
            lines.append('')
            lines.append('; DWARF 行号映射表:')
            for line, col, ref in self._line_mapping:
                lines.append(f'  ; line {line}:{col} -> {ref}')

        return '\n'.join(lines)

    def emit_location(self, line: int, col: int) -> str:
        """生成 !dbg 位置标注

        Args:
            line: 行号
            col: 列号

        Returns:
            !dbg 标注字符串，如 "!dbg !3"
        """
        # 创建位置元数据
        loc_id = self._new_metadata_id()

        # 获取当前作用域
        current_scope = self._scope_stack[-1] if self._scope_stack else None
        scope_ref = f'!{self._compile_unit_id}'
        if current_scope:
            scope_ref = current_scope.scope_id

        self._metadata.append(
            f'!{loc_id} = !DILocation('
            f'line: {line}, '
            f'column: {col}, '
            f'scope: {scope_ref}, '
            f'inlinedAt: null'
            f')'
        )

        dbg_ref = f'!dbg !{loc_id}'
        self._line_mapping.append((line, col, dbg_ref))
        return dbg_ref

    def emit_location_for_func(self, func_name: str, line: int, col: int = 0) -> str:
        """为函数生成位置标注

        Args:
            func_name: 函数名
            line: 行号
            col: 列号

        Returns:
            !dbg 标注字符串
        """
        loc_id = self._new_metadata_id()

        # 使用函数的作用域
        func_scope = self._func_metadata.get(func_name, f'!{self._compile_unit_id}')

        self._metadata.append(
            f'!{loc_id} = !DILocation('
            f'line: {line}, '
            f'column: {col}, '
            f'scope: {func_scope}, '
            f'inlinedAt: null'
            f')'
        )

        dbg_ref = f'!dbg !{loc_id}'
        self._line_mapping.append((line, col, dbg_ref))
        return dbg_ref

    def push_scope(self, scope_id: str):
        """手动压入作用域

        Args:
            scope_id: 作用域 ID 字符串
        """
        scope = self._scope_map.get(scope_id)
        if scope:
            self._scope_stack.append(scope)

    def pop_scope(self):
        """弹出作用域"""
        if self._scope_stack:
            self._scope_stack.pop()

    def get_current_scope(self) -> Optional[str]:
        """获取当前作用域 ID

        Returns:
            当前作用域 ID 字符串
        """
        if self._scope_stack:
            return self._scope_stack[-1].scope_id
        return None

    def _get_or_create_type(self, type_name: str) -> str:
        """获取或创建类型元数据

        Args:
            type_name: 类型名

        Returns:
            类型元数据 ID 字符串
        """
        if type_name in self._type_metadata:
            return self._type_metadata[type_name]

        # 基础类型映射
        basic_types = {
            'i8': (1, 'DW_ATE_signed'),
            'i16': (2, 'DW_ATE_signed'),
            'i32': (4, 'DW_ATE_signed'),
            'i64': (8, 'DW_ATE_signed'),
            'i8*': (8, 'DW_ATE_address'),
            'float': (4, 'DW_ATE_float'),
            'double': (8, 'DW_ATE_float'),
            'void': (0, 'DW_ATE_unsigned'),
        }

        if type_name in basic_types:
            size, encoding = basic_types[type_name]
            return self.add_type(type_name, size, encoding)

        # 默认创建指针类型
        return self.add_type(type_name, 8, 'DW_ATE_unsigned')

    def get_function_metadata(self, func_name: str) -> Optional[str]:
        """获取函数元数据 ID

        Args:
            func_name: 函数名

        Returns:
            元数据 ID 字符串，如 "!3"
        """
        return self._func_metadata.get(func_name)

    def get_var_metadata(self, var_name: str) -> Optional[str]:
        """获取变量元数据 ID

        Args:
            var_name: 变量名

        Returns:
            元数据 ID 字符串
        """
        return self._var_metadata.get(var_name)