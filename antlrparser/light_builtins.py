"""光明解释器 - 内置函数混入模块"""

from typing import List

from interpreter_core import InterpreterCore, LightValue, LightBuiltinFunction


class BuiltinsMixin:
    """内置函数混入类"""

    def _register_builtins(self):
        """注册内置函数"""
        builtins = [
            # I/O操作
            LightBuiltinFunction('打印', self._builtin_print, min_args=1),
            LightBuiltinFunction('输出', self._builtin_print, min_args=1),
            # 典操作
            LightBuiltinFunction('_典', self._builtin_dict, min_args=0),
            # 类型转换
            LightBuiltinFunction('转字符串', self._builtin_to_string, min_args=1, max_args=1),
            LightBuiltinFunction('_串化', self._builtin_to_string, min_args=1, max_args=1),
            LightBuiltinFunction('_数化', self._builtin_to_number, min_args=1, max_args=1),
            LightBuiltinFunction('_布尔化', self._builtin_to_bool, min_args=1, max_args=1),
            # 字符分类
            LightBuiltinFunction('_是中文', self._builtin_is_cjk, min_args=1, max_args=1),
            LightBuiltinFunction('_是字母', self._builtin_is_letter, min_args=1, max_args=1),
            LightBuiltinFunction('_是数字', self._builtin_is_digit, min_args=1, max_args=1),
            # 文件IO
            LightBuiltinFunction('_读文件', self._builtin_read_file, min_args=1, max_args=1),
            LightBuiltinFunction('_写文件', self._builtin_write_file, min_args=2, max_args=2),
            LightBuiltinFunction('_文件存在', self._builtin_file_exists, min_args=1, max_args=1),
            # 数学函数
            LightBuiltinFunction('abs', self._builtin_abs, min_args=1, max_args=1),
            LightBuiltinFunction('max', self._builtin_max, min_args=2),
            LightBuiltinFunction('min', self._builtin_min, min_args=2),
            LightBuiltinFunction('sqrt', self._builtin_sqrt, min_args=1, max_args=1),
            LightBuiltinFunction('pow', self._builtin_pow, min_args=2, max_args=2),
            LightBuiltinFunction('round', self._builtin_round, min_args=1, max_args=1),
            LightBuiltinFunction('sin', self._builtin_sin, min_args=1, max_args=1),
            LightBuiltinFunction('cos', self._builtin_cos, min_args=1, max_args=1),
            LightBuiltinFunction('tan', self._builtin_tan, min_args=1, max_args=1),
            LightBuiltinFunction('log', self._builtin_log, min_args=1, max_args=1),
            LightBuiltinFunction('exp', self._builtin_exp, min_args=1, max_args=1),
            LightBuiltinFunction('floor', self._builtin_floor, min_args=1, max_args=1),
            LightBuiltinFunction('ceil', self._builtin_ceil, min_args=1, max_args=1),
            # 字符串函数
            LightBuiltinFunction('len', self._builtin_len, min_args=1, max_args=1),
            LightBuiltinFunction('trim', self._builtin_trim, min_args=1, max_args=1),
            LightBuiltinFunction('substring', self._builtin_substring, min_args=3, max_args=3),
            LightBuiltinFunction('lower', self._builtin_lower, min_args=1, max_args=1),
            LightBuiltinFunction('upper', self._builtin_upper, min_args=1, max_args=1),
            LightBuiltinFunction('replace', self._builtin_replace, min_args=3, max_args=3),
            LightBuiltinFunction('split', self._builtin_split, min_args=2, max_args=2),
            LightBuiltinFunction('join', self._builtin_join, min_args=2, max_args=2),
            LightBuiltinFunction('indexOf', self._builtin_index_of, min_args=2, max_args=2),
            LightBuiltinFunction('contains', self._builtin_contains, min_args=2, max_args=2),
            LightBuiltinFunction('结尾', self._builtin_endswith, min_args=2, max_args=2),
            LightBuiltinFunction('startswith', self._builtin_endswith, min_args=2, max_args=2),
            LightBuiltinFunction('开头', self._builtin_startswith, min_args=2, max_args=2),
            LightBuiltinFunction('endswith', self._builtin_endswith, min_args=2, max_args=2),
            # 列表函数
            LightBuiltinFunction('列表长度', self._builtin_list_len, min_args=1, max_args=1),
            LightBuiltinFunction('listLen', self._builtin_list_len, min_args=1, max_args=1),
            LightBuiltinFunction('listAppend', self._builtin_list_append, min_args=2, max_args=2),
            LightBuiltinFunction('listReverse', self._builtin_list_reverse, min_args=1, max_args=1),
            LightBuiltinFunction('listIndexOf', self._builtin_list_index_of, min_args=2, max_args=2),
            LightBuiltinFunction('listContains', self._builtin_list_contains, min_args=2, max_args=2),
            LightBuiltinFunction('listSlice', self._builtin_list_slice, min_args=3, max_args=3),
            LightBuiltinFunction('listConcat', self._builtin_list_concat, min_args=2, max_args=2),
            LightBuiltinFunction('listSort', self._builtin_list_sort, min_args=1, max_args=1),
            LightBuiltinFunction('listInsert', self._builtin_list_insert, min_args=3, max_args=3),
            LightBuiltinFunction('listRemove', self._builtin_list_remove, min_args=2, max_args=2),
            LightBuiltinFunction('listPop', self._builtin_list_pop, min_args=1, max_args=2),
            # 时间函数
            LightBuiltinFunction('now', self._builtin_now, min_args=0, max_args=0),
            LightBuiltinFunction('sleep', self._builtin_sleep, min_args=1, max_args=1),
            # 其他实用函数
            LightBuiltinFunction('range', self._builtin_range, min_args=1, max_args=3),
            LightBuiltinFunction('type', self._builtin_type, min_args=1, max_args=1),
            LightBuiltinFunction('id', self._builtin_id, min_args=1, max_args=1),
            # 调试函数
            LightBuiltinFunction('printDebug', self._builtin_print_debug, min_args=2, max_args=2),
            LightBuiltinFunction('assert', self._builtin_assert, min_args=2, max_args=2),
            # 新数学函数
            LightBuiltinFunction('随机整数', self._builtin_random_int, min_args=2, max_args=2),
            LightBuiltinFunction('randomInt', self._builtin_random_int, min_args=2, max_args=2),
            LightBuiltinFunction('随机浮点', self._builtin_random_float, min_args=0, max_args=0),
            LightBuiltinFunction('randomFloat', self._builtin_random_float, min_args=0, max_args=0),
            LightBuiltinFunction('阶乘', self._builtin_factorial, min_args=1, max_args=1),
            LightBuiltinFunction('factorial', self._builtin_factorial, min_args=1, max_args=1),
            LightBuiltinFunction('平均数', self._builtin_mean, min_args=1, max_args=1),
            LightBuiltinFunction('mean', self._builtin_mean, min_args=1, max_args=1),
            LightBuiltinFunction('中位数', self._builtin_median, min_args=1, max_args=1),
            LightBuiltinFunction('median', self._builtin_median, min_args=1, max_args=1),
            LightBuiltinFunction('求和', self._builtin_sum, min_args=1, max_args=1),
            LightBuiltinFunction('sum', self._builtin_sum, min_args=1, max_args=1),
            LightBuiltinFunction('圆周率', self._builtin_pi, min_args=0, max_args=0),
            LightBuiltinFunction('pi', self._builtin_pi, min_args=0, max_args=0),
            LightBuiltinFunction('自然常数', self._builtin_e, min_args=0, max_args=0),
            LightBuiltinFunction('e', self._builtin_e, min_args=0, max_args=0),
            # JSON 函数
            LightBuiltinFunction('解析JSON', self._builtin_parse_json, min_args=1, max_args=1),
            LightBuiltinFunction('解析字典', self._builtin_parse_json, min_args=1, max_args=1),
            LightBuiltinFunction('parseJSON', self._builtin_parse_json, min_args=1, max_args=1),
            LightBuiltinFunction('序列化JSON', self._builtin_stringify_json, min_args=1, max_args=2),
            LightBuiltinFunction('序列化字典', self._builtin_stringify_json, min_args=1, max_args=2),
            LightBuiltinFunction('stringifyJSON', self._builtin_stringify_json, min_args=1, max_args=2),
            # 日期时间函数
            LightBuiltinFunction('当前时间', self._builtin_current_time, min_args=0, max_args=1),
            LightBuiltinFunction('formatTime', self._builtin_current_time, min_args=0, max_args=1),
            LightBuiltinFunction('当前日期', self._builtin_current_date, min_args=0, max_args=1),
            LightBuiltinFunction('formatDate', self._builtin_current_date, min_args=0, max_args=1),
            LightBuiltinFunction('时间戳', self._builtin_timestamp, min_args=0, max_args=0),
            LightBuiltinFunction('timestamp', self._builtin_timestamp, min_args=0, max_args=0),
            LightBuiltinFunction('格式化时间', self._builtin_format_time, min_args=2, max_args=2),
            LightBuiltinFunction('formatTime', self._builtin_format_time, min_args=2, max_args=2),
            LightBuiltinFunction('日期差', self._builtin_date_diff, min_args=2, max_args=2),
            LightBuiltinFunction('dateDiff', self._builtin_date_diff, min_args=2, max_args=2),
            # 哈希函数
            LightBuiltinFunction('MD5', self._builtin_md5, min_args=1, max_args=1),
            LightBuiltinFunction('md5', self._builtin_md5, min_args=1, max_args=1),
            LightBuiltinFunction('SHA256', self._builtin_sha256, min_args=1, max_args=1),
            LightBuiltinFunction('sha256', self._builtin_sha256, min_args=1, max_args=1),
            LightBuiltinFunction('Base64编码', self._builtin_base64_encode, min_args=1, max_args=1),
            LightBuiltinFunction('base64Encode', self._builtin_base64_encode, min_args=1, max_args=1),
            LightBuiltinFunction('Base64解码', self._builtin_base64_decode, min_args=1, max_args=1),
            LightBuiltinFunction('base64Decode', self._builtin_base64_decode, min_args=1, max_args=1),
            # 正则表达式函数
            LightBuiltinFunction('匹配', self._builtin_regex_match, min_args=2, max_args=2),
            LightBuiltinFunction('regexMatch', self._builtin_regex_match, min_args=2, max_args=2),
            LightBuiltinFunction('搜索', self._builtin_regex_search, min_args=2, max_args=2),
            LightBuiltinFunction('regexSearch', self._builtin_regex_search, min_args=2, max_args=2),
            LightBuiltinFunction('查找所有', self._builtin_regex_find_all, min_args=2, max_args=2),
            LightBuiltinFunction('regexFindAll', self._builtin_regex_find_all, min_args=2, max_args=2),
            LightBuiltinFunction('替换', self._builtin_regex_replace, min_args=3, max_args=3),
            LightBuiltinFunction('regexReplace', self._builtin_regex_replace, min_args=3, max_args=3),
            LightBuiltinFunction('分割', self._builtin_regex_split, min_args=2, max_args=2),
            LightBuiltinFunction('regexSplit', self._builtin_regex_split, min_args=2, max_args=2),
        ]
        for b in builtins:
            self.global_env.define(b.name, LightValue(b, '内置段'))
    
    # ----- 内置函数实现 -----

    def _builtin_print(self, args: List[LightValue]) -> LightValue:
        """打印输出"""
        text = ' '.join(str(a) for a in args)
        self.output_lines.append(text)
        print(text)
        return LightValue(None, '空')

    def _builtin_dict(self, args: List[LightValue]) -> LightValue:
        """创建典：_典(键1, 值1, 键2, 值2, ...)"""
        result = {}
        for i in range(0, len(args), 2):
            if i + 1 >= len(args):
                raise RuntimeError("_典 需要偶数个参数（键值对）")
            key = args[i]
            if key.type_name not in ('串', '数', '布尔'):
                raise RuntimeError(f"典键不支持类型: '{key.type_name}'")
            result[key.value] = args[i + 1]
        return LightValue(result, '典')
    
    def _builtin_to_string(self, args: List[LightValue]) -> LightValue:
        """转换为字符串"""
        return LightValue(str(args[0]), '串')
    
    def _builtin_to_number(self, args: List[LightValue]) -> LightValue:
        """转换为数字"""
        try:
            val = args[0].value
            if isinstance(val, str):
                if '.' in val:
                    return LightValue(float(val), '数')
                return LightValue(int(val), '数')
            if isinstance(val, bool):
                return LightValue(1 if val else 0, '数')
            if isinstance(val, (int, float)):
                return LightValue(val, '数')
            raise ValueError()
        except (ValueError, TypeError):
            raise RuntimeError(f"无法转换为数字: '{args[0].value}'")
    
    def _builtin_is_cjk(self, args: List[LightValue]) -> LightValue:
        """判断是否为中文字符"""
        s = str(args[0])
        if len(s) != 1:
            return LightValue(False, '布尔')
        cp = ord(s)
        return LightValue(
            0x4E00 <= cp <= 0x9FFF or
            0x3400 <= cp <= 0x4DBF or
            0xF900 <= cp <= 0xFAFF,
            '布尔'
        )
    
    def _builtin_is_letter(self, args: List[LightValue]) -> LightValue:
        """判断是否为英文字母"""
        s = str(args[0])
        if len(s) != 1:
            return LightValue(False, '布尔')
        return LightValue(('a' <= s <= 'z') or ('A' <= s <= 'Z') or s == '_', '布尔')
    
    def _builtin_is_digit(self, args: List[LightValue]) -> LightValue:
        """判断是否为数字字符"""
        s = str(args[0])
        if len(s) != 1:
            return LightValue(False, '布尔')
        return LightValue('0' <= s <= '9', '布尔')
    
    def _builtin_read_file(self, args: List[LightValue]) -> LightValue:
        """读取文件内容"""
        path = str(args[0])
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return LightValue(content, '串')
        except Exception as e:
            raise RuntimeError(f"读取文件失败: {e}")
    
    def _builtin_write_file(self, args: List[LightValue]) -> LightValue:
        """写入文件内容"""
        path = str(args[0])
        content = str(args[1])
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return LightValue(None, '空')
        except Exception as e:
            raise RuntimeError(f"写入文件失败: {e}")
    
    def _builtin_file_exists(self, args: List[LightValue]) -> LightValue:
        """检查文件是否存在"""
        path = str(args[0])
        import os
        return LightValue(os.path.exists(path), '布尔')
    
    def _builtin_to_bool(self, args: List[LightValue]) -> LightValue:
        """转换为布尔值"""
        val = args[0].value
        if val is None:
            return LightValue(False, '布尔')
        if isinstance(val, bool):
            return LightValue(val, '布尔')
        if isinstance(val, (int, float)):
            return LightValue(val != 0, '布尔')
        if isinstance(val, str):
            return LightValue(len(val) > 0, '布尔')
        if isinstance(val, (list, dict)):
            return LightValue(len(val) > 0, '布尔')
        return LightValue(bool(val), '布尔')
    
    # ----- 数学函数 -----
    
    def _builtin_abs(self, args: List[LightValue]) -> LightValue:
        """绝对值"""
        val = args[0].value
        if isinstance(val, (int, float)):
            return LightValue(abs(val), '数')
        raise RuntimeError("abs 需要数字参数")
    
    def _builtin_max(self, args: List[LightValue]) -> LightValue:
        """最大值"""
        max_val = None
        for arg in args:
            val = arg.value
            if not isinstance(val, (int, float)):
                raise RuntimeError("max 需要数字参数")
            if max_val is None or val > max_val:
                max_val = val
        return LightValue(max_val, '数')
    
    def _builtin_min(self, args: List[LightValue]) -> LightValue:
        """最小值"""
        min_val = None
        for arg in args:
            val = arg.value
            if not isinstance(val, (int, float)):
                raise RuntimeError("min 需要数字参数")
            if min_val is None or val < min_val:
                min_val = val
        return LightValue(min_val, '数')
    
    def _builtin_sqrt(self, args: List[LightValue]) -> LightValue:
        """平方根"""
        val = args[0].value
        if isinstance(val, (int, float)):
            if val < 0:
                raise RuntimeError("sqrt 参数不能为负数")
            return LightValue(val ** 0.5, '数')
        raise RuntimeError("sqrt 需要数字参数")
    
    def _builtin_pow(self, args: List[LightValue]) -> LightValue:
        """幂运算"""
        base = args[0].value
        exp = args[1].value
        if isinstance(base, (int, float)) and isinstance(exp, (int, float)):
            return LightValue(base ** exp, '数')
        raise RuntimeError("pow 需要数字参数")
    
    def _builtin_round(self, args: List[LightValue]) -> LightValue:
        """四舍五入"""
        val = args[0].value
        if isinstance(val, (int, float)):
            return LightValue(round(val), '数')
        raise RuntimeError("round 需要数字参数")
    
    def _builtin_sin(self, args: List[LightValue]) -> LightValue:
        """正弦函数"""
        import math
        val = args[0].value
        if isinstance(val, (int, float)):
            return LightValue(math.sin(val), '数')
        raise RuntimeError("sin 需要数字参数")
    
    def _builtin_cos(self, args: List[LightValue]) -> LightValue:
        """余弦函数"""
        import math
        val = args[0].value
        if isinstance(val, (int, float)):
            return LightValue(math.cos(val), '数')
        raise RuntimeError("cos 需要数字参数")
    
    def _builtin_tan(self, args: List[LightValue]) -> LightValue:
        """正切函数"""
        import math
        val = args[0].value
        if isinstance(val, (int, float)):
            return LightValue(math.tan(val), '数')
        raise RuntimeError("tan 需要数字参数")
    
    def _builtin_log(self, args: List[LightValue]) -> LightValue:
        """自然对数"""
        import math
        val = args[0].value
        if isinstance(val, (int, float)):
            if val <= 0:
                raise RuntimeError("log 参数必须大于0")
            return LightValue(math.log(val), '数')
        raise RuntimeError("log 需要数字参数")
    
    def _builtin_exp(self, args: List[LightValue]) -> LightValue:
        """指数函数"""
        import math
        val = args[0].value
        if isinstance(val, (int, float)):
            return LightValue(math.exp(val), '数')
        raise RuntimeError("exp 需要数字参数")
    
    def _builtin_floor(self, args: List[LightValue]) -> LightValue:
        """向下取整"""
        import math
        val = args[0].value
        if isinstance(val, (int, float)):
            return LightValue(math.floor(val), '数')
        raise RuntimeError("floor 需要数字参数")
    
    def _builtin_ceil(self, args: List[LightValue]) -> LightValue:
        """向上取整"""
        import math
        val = args[0].value
        if isinstance(val, (int, float)):
            return LightValue(math.ceil(val), '数')
        raise RuntimeError("ceil 需要数字参数")
    
    # ----- 字符串函数 -----
    
    def _builtin_len(self, args: List[LightValue]) -> LightValue:
        """长度"""
        val = args[0].value
        if isinstance(val, str):
            return LightValue(len(val), '数')
        if isinstance(val, list):
            return LightValue(len(val), '数')
        raise RuntimeError("len 需要字符串或列表参数")
    
    def _builtin_trim(self, args: List[LightValue]) -> LightValue:
        """去除首尾空白"""
        val = args[0].value
        if isinstance(val, str):
            return LightValue(val.strip(), '串')
        raise RuntimeError("trim 需要字符串参数")
    
    def _builtin_substring(self, args: List[LightValue]) -> LightValue:
        """子串"""
        s = args[0].value
        start = args[1].value
        end = args[2].value
        if isinstance(s, str) and isinstance(start, int) and isinstance(end, int):
            return LightValue(s[start:end], '串')
        raise RuntimeError("substring 参数类型错误")
    
    def _builtin_lower(self, args: List[LightValue]) -> LightValue:
        """转换为小写"""
        s = args[0].value
        if isinstance(s, str):
            return LightValue(s.lower(), '串')
        raise RuntimeError("lower 需要字符串参数")
    
    def _builtin_upper(self, args: List[LightValue]) -> LightValue:
        """转换为大写"""
        s = args[0].value
        if isinstance(s, str):
            return LightValue(s.upper(), '串')
        raise RuntimeError("upper 需要字符串参数")
    
    def _builtin_replace(self, args: List[LightValue]) -> LightValue:
        """字符串替换"""
        s = args[0].value
        old = args[1].value
        new = args[2].value
        if isinstance(s, str) and isinstance(old, str) and isinstance(new, str):
            return LightValue(s.replace(old, new), '串')
        raise RuntimeError("replace 参数类型错误")
    
    def _builtin_split(self, args: List[LightValue]) -> LightValue:
        """字符串分割"""
        s = args[0].value
        sep = args[1].value
        if isinstance(s, str) and isinstance(sep, str):
            return LightValue(s.split(sep), '列')
        raise RuntimeError("split 参数类型错误")
    
    def _builtin_join(self, args: List[LightValue]) -> LightValue:
        """列表拼接为字符串"""
        lst = args[0].value
        sep = args[1].value
        if isinstance(lst, list) and isinstance(sep, str):
            str_list = []
            for item in lst:
                if isinstance(item, LightValue):
                    str_list.append(str(item.value))
                else:
                    str_list.append(str(item))
            return LightValue(sep.join(str_list), '串')
        raise RuntimeError("join 参数类型错误")
    
    def _builtin_index_of(self, args: List[LightValue]) -> LightValue:
        """字符串索引查找"""
        s = args[0].value
        substr = args[1].value
        if isinstance(s, str) and isinstance(substr, str):
            return LightValue(s.find(substr), '数')
        raise RuntimeError("indexOf 参数类型错误")
    
    def _builtin_contains(self, args: List[LightValue]) -> LightValue:
        """字符串包含检查"""
        s = args[0].value
        substr = args[1].value
        if isinstance(s, str) and isinstance(substr, str):
            return LightValue(substr in s, '布尔')
        raise RuntimeError("contains 参数类型错误")
    
    def _builtin_endswith(self, args: List[LightValue]) -> LightValue:
        """字符串结尾检查"""
        s = args[0].value
        suffix = args[1].value
        if isinstance(s, str) and isinstance(suffix, str):
            return LightValue(s.endswith(suffix), '布尔')
        raise RuntimeError("结尾 参数类型错误")
    
    def _builtin_startswith(self, args: List[LightValue]) -> LightValue:
        """字符串开头检查"""
        s = args[0].value
        prefix = args[1].value
        if isinstance(s, str) and isinstance(prefix, str):
            return LightValue(s.startswith(prefix), '布尔')
        raise RuntimeError("开头 参数类型错误")
    
    # ----- 列表函数 -----
    
    def _builtin_list_len(self, args: List[LightValue]) -> LightValue:
        """列表长度"""
        val = args[0].value
        if isinstance(val, list):
            return LightValue(len(val), '数')
        raise RuntimeError("listLen 需要列表参数")
    
    def _builtin_list_append(self, args: List[LightValue]) -> LightValue:
        """列表追加"""
        lst = args[0].value
        item = args[1]
        if isinstance(lst, list):
            lst.append(item)
            return LightValue(None, '空')
        raise RuntimeError("listAppend 需要列表参数")
    
    def _builtin_list_reverse(self, args: List[LightValue]) -> LightValue:
        """列表反转"""
        lst = args[0].value
        if isinstance(lst, list):
            lst.reverse()
            return LightValue(None, '空')
        raise RuntimeError("listReverse 需要列表参数")
    
    def _builtin_list_index_of(self, args: List[LightValue]) -> LightValue:
        """列表索引查找"""
        lst = args[0].value
        item = args[1]
        if isinstance(lst, list):
            for i, val in enumerate(lst):
                # 比较值而非对象引用
                val_val = val.value if isinstance(val, LightValue) else val
                item_val = item.value if isinstance(item, LightValue) else item
                if val_val == item_val:
                    return LightValue(i, '数')
            return LightValue(-1, '数')
        raise RuntimeError("listIndexOf 需要列表参数")
    
    def _builtin_list_contains(self, args: List[LightValue]) -> LightValue:
        """列表包含检查"""
        lst = args[0].value
        item = args[1]
        if isinstance(lst, list):
            item_val = item.value if isinstance(item, LightValue) else item
            for val in lst:
                val_val = val.value if isinstance(val, LightValue) else val
                if val_val == item_val:
                    return LightValue(True, '布尔')
            return LightValue(False, '布尔')
        raise RuntimeError("listContains 需要列表参数")
    
    def _builtin_list_slice(self, args: List[LightValue]) -> LightValue:
        """列表切片"""
        lst = args[0].value
        start = args[1].value
        end = args[2].value
        if isinstance(lst, list) and isinstance(start, int) and isinstance(end, int):
            return LightValue(lst[start:end], '列')
        raise RuntimeError("listSlice 参数类型错误")
    
    def _builtin_list_concat(self, args: List[LightValue]) -> LightValue:
        """列表拼接"""
        lst1 = args[0].value
        lst2 = args[1].value
        if isinstance(lst1, list) and isinstance(lst2, list):
            return LightValue(lst1 + lst2, '列')
        raise RuntimeError("listConcat 需要两个列表参数")
    
    def _builtin_list_sort(self, args: List[LightValue]) -> LightValue:
        """列表排序"""
        lst = args[0].value
        if isinstance(lst, list):
            lst.sort(key=lambda x: x.value if isinstance(x, LightValue) else x)
            return LightValue(None, '空')
        raise RuntimeError("listSort 需要列表参数")
    
    def _builtin_list_insert(self, args: List[LightValue]) -> LightValue:
        """列表插入"""
        lst = args[0].value
        index = args[1].value
        item = args[2]
        if isinstance(lst, list) and isinstance(index, int):
            lst.insert(index, item)
            return LightValue(None, '空')
        raise RuntimeError("listInsert 参数类型错误")
    
    def _builtin_list_remove(self, args: List[LightValue]) -> LightValue:
        """列表移除元素"""
        lst = args[0].value
        item = args[1]
        if isinstance(lst, list):
            item_val = item.value if isinstance(item, LightValue) else item
            for i, val in enumerate(lst):
                val_val = val.value if isinstance(val, LightValue) else val
                if val_val == item_val:
                    del lst[i]
                    return LightValue(None, '空')
            raise RuntimeError("元素不在列表中")
        raise RuntimeError("listRemove 需要列表参数")
    
    def _builtin_list_pop(self, args: List[LightValue]) -> LightValue:
        """列表弹出元素"""
        lst = args[0].value
        if isinstance(lst, list):
            if len(args) > 1:
                index = args[1].value
                if isinstance(index, int):
                    return lst.pop(index)
                raise RuntimeError("pop 索引必须是整数")
            return lst.pop()
        raise RuntimeError("listPop 需要列表参数")
    
    # ----- 时间函数 -----
    
    def _builtin_now(self, args: List[LightValue]) -> LightValue:
        """获取当前时间戳"""
        import time
        return LightValue(time.time(), '数')
    
    def _builtin_sleep(self, args: List[LightValue]) -> LightValue:
        """暂停执行"""
        import time
        val = args[0].value
        if isinstance(val, (int, float)):
            time.sleep(val)
            return LightValue(None, '空')
        raise RuntimeError("sleep 需要数字参数")
    
    # ----- 其他函数 -----
    
    def _builtin_range(self, args: List[LightValue]) -> LightValue:
        """生成范围列表"""
        if len(args) == 1:
            end = args[0].value
            if isinstance(end, int):
                return LightValue(list(range(end)), '列')
        elif len(args) == 2:
            start = args[0].value
            end = args[1].value
            if isinstance(start, int) and isinstance(end, int):
                return LightValue(list(range(start, end)), '列')
        elif len(args) == 3:
            start = args[0].value
            end = args[1].value
            step = args[2].value
            if isinstance(start, int) and isinstance(end, int) and isinstance(step, int):
                return LightValue(list(range(start, end, step)), '列')
        raise RuntimeError("range 参数类型错误")
    
    def _builtin_type(self, args: List[LightValue]) -> LightValue:
        """获取类型名称"""
        val = args[0]
        return LightValue(val.type_name, '串')
    
    def _builtin_id(self, args: List[LightValue]) -> LightValue:
        """获取对象ID"""
        val = args[0].value
        return LightValue(id(val), '数')
    
    # ----- 调试函数 -----
    
    def _builtin_print_debug(self, args: List[LightValue]) -> LightValue:
        """调试打印"""
        msg = str(args[0].value)
        val = str(args[1].value)
        self.output_lines.append(f"DEBUG: {msg} = {val}")
        print(f"DEBUG: {msg} = {val}")
        return LightValue(None, '空')
    
    def _builtin_assert(self, args: List[LightValue]) -> LightValue:
        """断言"""
        condition = args[0].value
        msg = str(args[1].value)
        if not condition:
            self.output_lines.append(f"断言失败: {msg}")
            print(f"断言失败: {msg}")
            raise RuntimeError(f"断言失败: {msg}")
        return LightValue(None, '空')
    
    # ----- 新数学函数 -----
    
    def _builtin_random_int(self, args: List[LightValue]) -> LightValue:
        """随机整数"""
        import random
        lo = int(args[0].value)
        hi = int(args[1].value)
        return LightValue(random.randint(lo, hi), '数')
    
    def _builtin_random_float(self, args: List[LightValue]) -> LightValue:
        """随机浮点 [0,1)"""
        import random
        return LightValue(random.random(), '数')
    
    def _builtin_factorial(self, args: List[LightValue]) -> LightValue:
        """阶乘"""
        n = int(args[0].value)
        if n < 0:
            raise RuntimeError("阶乘参数不能为负数")
        import math
        return LightValue(math.factorial(n), '数')
    
    def _builtin_mean(self, args: List[LightValue]) -> LightValue:
        """平均数"""
        data = args[0].value
        if not isinstance(data, list) or len(data) == 0:
            raise RuntimeError("数据列表为空")
        import statistics
        values = [x.value if isinstance(x, LightValue) else x for x in data]
        return LightValue(statistics.mean(values), '数')
    
    def _builtin_median(self, args: List[LightValue]) -> LightValue:
        """中位数"""
        data = args[0].value
        if not isinstance(data, list) or len(data) == 0:
            raise RuntimeError("数据列表为空")
        import statistics
        values = [x.value if isinstance(x, LightValue) else x for x in data]
        return LightValue(statistics.median(values), '数')
    
    def _builtin_sum(self, args: List[LightValue]) -> LightValue:
        """求和"""
        data = args[0].value
        if not isinstance(data, list):
            raise RuntimeError("参数必须是列表")
        values = [x.value if isinstance(x, LightValue) else x for x in data]
        return LightValue(sum(values), '数')
    
    def _builtin_pi(self, args: List[LightValue]) -> LightValue:
        """圆周率"""
        import math
        return LightValue(math.pi, '数')
    
    def _builtin_e(self, args: List[LightValue]) -> LightValue:
        """自然常数"""
        import math
        return LightValue(math.e, '数')
    
    # ----- JSON 函数 -----
    
    def _builtin_parse_json(self, args: List[LightValue]) -> LightValue:
        """解析JSON字符串"""
        import json
        text = str(args[0].value)
        try:
            result = json.loads(text)
            if isinstance(result, dict):
                return LightValue(result, '典')
            elif isinstance(result, list):
                return LightValue(result, '列')
            elif isinstance(result, str):
                return LightValue(result, '串')
            elif isinstance(result, bool):
                return LightValue(result, '布尔')
            elif isinstance(result, (int, float)):
                return LightValue(result, '数')
            elif result is None:
                return LightValue(None, '空')
            return LightValue(result)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"JSON解析失败: {e}")
    
    def _builtin_stringify_json(self, args: List[LightValue]) -> LightValue:
        """序列化为JSON字符串"""
        import json
        val = args[0].value
        indent = None
        if len(args) >= 2 and args[1].value is not None:
            indent = int(args[1].value)
        try:
            result = json.dumps(val, ensure_ascii=False, indent=indent)
            return LightValue(result, '串')
        except (TypeError, ValueError) as e:
            raise RuntimeError(f"JSON序列化失败: {e}")
    
    # ----- 日期时间函数 -----
    
    def _builtin_current_time(self, args: List[LightValue]) -> LightValue:
        """当前时间字符串"""
        from datetime import datetime
        fmt = '%Y-%m-%d %H:%M:%S'
        if args:
            fmt = str(args[0].value)
        return LightValue(datetime.now().strftime(fmt), '串')
    
    def _builtin_current_date(self, args: List[LightValue]) -> LightValue:
        """当前日期字符串"""
        from datetime import date
        fmt = '%Y-%m-%d'
        if args:
            fmt = str(args[0].value)
        return LightValue(date.today().strftime(fmt), '串')
    
    def _builtin_timestamp(self, args: List[LightValue]) -> LightValue:
        """当前时间戳"""
        import time
        return LightValue(time.time(), '数')
    
    def _builtin_format_time(self, args: List[LightValue]) -> LightValue:
        """格式化时间"""
        from datetime import datetime
        time_str = str(args[0].value)
        fmt = str(args[1].value)
        try:
            dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            return LightValue(dt.strftime(fmt), '串')
        except ValueError:
            try:
                dt = datetime.strptime(time_str, '%Y-%m-%d')
                return LightValue(dt.strftime(fmt), '串')
            except ValueError:
                raise RuntimeError(f"无法解析时间: '{time_str}'")
    
    def _builtin_date_diff(self, args: List[LightValue]) -> LightValue:
        """日期差"""
        from datetime import datetime
        d1 = str(args[0].value)
        d2 = str(args[1].value)
        try:
            dt1 = datetime.strptime(d1, '%Y-%m-%d')
            dt2 = datetime.strptime(d2, '%Y-%m-%d')
            diff = (dt2 - dt1).days
            return LightValue(diff, '数')
        except ValueError as e:
            raise RuntimeError(f"日期格式无效: {e}")
    
    # ----- 哈希函数 -----
    
    def _builtin_md5(self, args: List[LightValue]) -> LightValue:
        """MD5哈希"""
        import hashlib
        text = str(args[0].value)
        return LightValue(hashlib.md5(text.encode('utf-8')).hexdigest(), '串')
    
    def _builtin_sha256(self, args: List[LightValue]) -> LightValue:
        """SHA256哈希"""
        import hashlib
        text = str(args[0].value)
        return LightValue(hashlib.sha256(text.encode('utf-8')).hexdigest(), '串')
    
    def _builtin_base64_encode(self, args: List[LightValue]) -> LightValue:
        """Base64编码"""
        import base64
        text = str(args[0].value)
        return LightValue(base64.b64encode(text.encode('utf-8')).decode('ascii'), '串')
    
    def _builtin_base64_decode(self, args: List[LightValue]) -> LightValue:
        """Base64解码"""
        import base64
        text = str(args[0].value)
        try:
            return LightValue(base64.b64decode(text).decode('utf-8'), '串')
        except Exception as e:
            raise RuntimeError(f"Base64解码失败: {e}")
    
    # ----- 正则表达式函数 -----
    
    def _builtin_regex_match(self, args: List[LightValue]) -> LightValue:
        """正则匹配（开头匹配）"""
        import re
        pattern = str(args[0].value)
        text = str(args[1].value)
        m = re.match(pattern, text)
        if m:
            return LightValue(m.group(0), '串')
        return LightValue(None, '空')
    
    def _builtin_regex_search(self, args: List[LightValue]) -> LightValue:
        """正则搜索（第一个匹配）"""
        import re
        pattern = str(args[0].value)
        text = str(args[1].value)
        m = re.search(pattern, text)
        if m:
            return LightValue(m.group(0), '串')
        return LightValue(None, '空')
    
    def _builtin_regex_find_all(self, args: List[LightValue]) -> LightValue:
        """查找所有正则匹配"""
        import re
        pattern = str(args[0].value)
        text = str(args[1].value)
        result = re.findall(pattern, text)
        return LightValue(result, '列')
    
    def _builtin_regex_replace(self, args: List[LightValue]) -> LightValue:
        """正则替换"""
        import re
        pattern = str(args[0].value)
        repl = str(args[1].value)
        text = str(args[2].value)
        try:
            result = re.sub(pattern, repl, text)
            return LightValue(result, '串')
        except re.error as e:
            raise RuntimeError(f"正则替换失败: {e}")
    
    def _builtin_regex_split(self, args: List[LightValue]) -> LightValue:
        """正则分割"""
        import re
        pattern = str(args[0].value)
        text = str(args[1].value)
        result = re.split(pattern, text)
        return LightValue(result, '列')