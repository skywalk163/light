"""
段言标准库 - 身份证校验模块

提供中国身份证号码的校验、信息提取功能。

类：
    ChineseIDValidator: 身份证校验器

用法:
    validator = ChineseIDValidator()
    result = validator.validate("110101199001011234")
    birthday = validator.get_birthday("110101199001011234")
    gender = validator.get_gender("110101199001011234")
    region = validator.get_region("110101199001011234")
"""

import re
import datetime
from typing import Dict, Optional


# =============================================================================
# 地区代码映射
# =============================================================================

_REGION_CODE_MAP = {
    "11": "北京市", "12": "天津市", "13": "河北省", "14": "山西省",
    "15": "内蒙古自治区", "21": "辽宁省", "22": "吉林省", "23": "黑龙江省",
    "31": "上海市", "32": "江苏省", "33": "浙江省", "34": "安徽省",
    "35": "福建省", "36": "江西省", "37": "山东省", "41": "河南省",
    "42": "湖北省", "43": "湖南省", "44": "广东省", "45": "广西壮族自治区",
    "46": "海南省", "50": "重庆市", "51": "四川省", "52": "贵州省",
    "53": "云南省", "54": "西藏自治区", "61": "陕西省", "62": "甘肃省",
    "63": "青海省", "64": "宁夏回族自治区", "65": "新疆维吾尔自治区",
    "71": "台湾省", "81": "香港特别行政区", "82": "澳门特别行政区",
}

# 部分城市代码（前四位）
_CITY_CODE_MAP = {
    "1101": "市辖区", "1102": "县",
    "1201": "市辖区", "1202": "县",
    "1301": "石家庄市", "1302": "唐山市", "1303": "秦皇岛市", "1304": "邯郸市",
    "1305": "邢台市", "1306": "保定市", "1307": "张家口市", "1308": "承德市",
    "1309": "沧州市", "1310": "廊坊市", "1311": "衡水市",
    "3201": "南京市", "3202": "无锡市", "3203": "徐州市", "3204": "常州市",
    "3205": "苏州市", "3206": "南通市", "3207": "连云港市", "3208": "淮安市",
    "3209": "盐城市", "3210": "扬州市", "3211": "镇江市", "3212": "泰州市",
    "3213": "宿迁市",
    "3301": "杭州市", "3302": "宁波市", "3303": "温州市", "3304": "嘉兴市",
    "3305": "湖州市", "3306": "绍兴市", "3307": "金华市", "3308": "衢州市",
    "3309": "舟山市", "3310": "台州市", "3311": "丽水市",
    "4401": "广州市", "4402": "韶关市", "4403": "深圳市", "4404": "珠海市",
    "4405": "汕头市", "4406": "佛山市", "4407": "江门市", "4408": "湛江市",
    "4409": "茂名市", "4412": "肇庆市", "4413": "惠州市", "4414": "梅州市",
    "4415": "汕尾市", "4416": "河源市", "4417": "阳江市", "4418": "清远市",
    "4419": "东莞市", "4420": "中山市", "4451": "潮州市", "4452": "揭阳市",
    "4453": "云浮市",
    "5101": "成都市", "5103": "自贡市", "5104": "攀枝花市", "5105": "泸州市",
    "5106": "德阳市", "5107": "绵阳市", "5108": "广元市", "5109": "遂宁市",
    "5110": "内江市", "5111": "乐山市", "5113": "南充市", "5114": "眉山市",
    "5115": "宜宾市", "5116": "广安市", "5117": "达州市", "5118": "雅安市",
    "5119": "巴中市", "5120": "资阳市",
    "6101": "西安市", "6102": "铜川市", "6103": "宝鸡市", "6104": "咸阳市",
    "6105": "渭南市", "6106": "延安市", "6107": "汉中市", "6108": "榆林市",
    "6109": "安康市", "6110": "商洛市",
}

# 校验码加权因子
_WEIGHT_FACTORS = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]

# 校验码映射
_CHECK_CODE_MAP = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2']


class ChineseIDValidator:
    """中国身份证号码校验器

    支持 18 位身份证号码的格式校验、校验码验证、信息提取。
    提供出生日期、性别、地区的提取功能。

    用法:
        validator = ChineseIDValidator()
        result = validator.validate("110101199001011234")
        # result = {"valid": True, "birthday": "1990-01-01", "gender": "男", "region": "北京市市辖区"}
    """

    # 18 位身份证号正则：6位地区码 + 8位出生日期 + 3位顺序码 + 1位校验码
    _ID_PATTERN = re.compile(r'^(\d{6})(\d{4})(\d{2})(\d{2})(\d{3})([\dXx])$')

    def validate(self, id_number: str) -> Dict[str, object]:
        """校验身份证号码并返回详细信息

        对 18 位身份证号码进行完整性校验，包括：
        - 格式检查（长度、字符）
        - 出生日期合法性
        - 校验码验证

        Args:
            id_number: 18 位身份证号码

        Returns:
            校验结果字典:
            - valid: 是否有效
            - birthday: 出生日期（如 "1990-01-01"）
            - gender: 性别（"男"/"女"）
            - region: 地区（如 "北京市市辖区"）
            - errors: 错误信息列表（无效时）
        """
        errors = []

        # 基本格式校验
        if not id_number or len(id_number) != 18:
            errors.append("身份证号码必须为18位")
            return self._make_error_result(errors)

        # 正则匹配
        match = self._ID_PATTERN.match(id_number)
        if not match:
            errors.append("身份证号码格式不正确")
            return self._make_error_result(errors)

        region_code = match.group(1)
        year = match.group(2)
        month = match.group(3)
        day = match.group(4)
        sequence_code = match.group(5)
        check_digit = match.group(6).upper()

        # 验证出生日期
        birthday = f"{year}-{month}-{day}"
        if not self._validate_birthday(int(year), int(month), int(day)):
            errors.append(f"出生日期无效: {birthday}")

        # 验证地区码
        region = self._lookup_region(region_code)
        if not region:
            errors.append(f"地区代码无效: {region_code}")

        # 验证校验码
        expected_check = self.generate_check_digit(id_number)
        if check_digit != expected_check:
            errors.append(f"校验码不匹配: 期望 {expected_check}, 实际 {check_digit}")

        # 提取性别
        gender = self._get_gender_from_code(int(sequence_code))

        if errors:
            return self._make_error_result(errors, birthday, gender, region)

        return {
            "valid": True,
            "birthday": birthday,
            "gender": gender,
            "region": region or "未知地区",
            "errors": [],
        }

    def get_birthday(self, id_number: str) -> str:
        """提取身份证号码中的出生日期

        Args:
            id_number: 18 位身份证号码

        Returns:
            出生日期字符串（如 "1990-01-01"），无效返回空字符串
        """
        match = self._ID_PATTERN.match(id_number)
        if not match:
            return ""
        return f"{match.group(2)}-{match.group(3)}-{match.group(4)}"

    def get_gender(self, id_number: str) -> str:
        """提取身份证号码中的性别

        Args:
            id_number: 18 位身份证号码

        Returns:
            "男" 或 "女"，无效返回空字符串
        """
        match = self._ID_PATTERN.match(id_number)
        if not match:
            return ""
        sequence_code = int(match.group(5))
        return self._get_gender_from_code(sequence_code)

    def get_region(self, id_number: str) -> str:
        """提取身份证号码中的地区信息

        Args:
            id_number: 18 位身份证号码

        Returns:
            地区名称（如 "北京市市辖区"），无效返回空字符串
        """
        match = self._ID_PATTERN.match(id_number)
        if not match:
            return ""
        region_code = match.group(1)
        return self._lookup_region(region_code) or ""

    def generate_check_digit(self, id_number: str) -> str:
        """计算身份证号码的校验码

        根据 GB 11643-1999 标准，对前 17 位进行加权求和，
        取模 11 后映射到校验码。

        Args:
            id_number: 17 位或 18 位身份证号码（取前 17 位）

        Returns:
            校验码字符（'0'-'9' 或 'X'）
        """
        # 取前 17 位数字
        digits = id_number[:17]
        if len(digits) < 17 or not digits.isdigit():
            return ""

        # 加权求和
        total = sum(int(digits[i]) * _WEIGHT_FACTORS[i] for i in range(17))
        remainder = total % 11
        return _CHECK_CODE_MAP[remainder]

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_birthday(year: int, month: int, day: int) -> bool:
        """验证出生日期是否合法

        Args:
            year: 年份
            month: 月份
            day: 日期

        Returns:
            True 如果日期合法
        """
        try:
            datetime.date(year, month, day)
            return True
        except (ValueError, OverflowError):
            return False

    @staticmethod
    def _get_gender_from_code(sequence_code: int) -> str:
        """根据顺序码获取性别

        顺序码的第 17 位奇数表示男性，偶数表示女性。
        顺序码是 3 位数字，取最后一位判断。

        Args:
            sequence_code: 3 位顺序码

        Returns:
            "男" 或 "女"
        """
        return "男" if sequence_code % 2 == 1 else "女"

    @staticmethod
    def _lookup_region(code: str) -> Optional[str]:
        """查询地区代码对应的地区名称

        先尝试 4 位城市代码，回退到 2 位省份代码。

        Args:
            code: 6 位地区代码

        Returns:
            地区名称，未找到返回 None
        """
        # 先尝试 4 位城市代码
        city_code = code[:4]
        if city_code in _CITY_CODE_MAP:
            province = _REGION_CODE_MAP.get(code[:2], "")
            city = _CITY_CODE_MAP[city_code]
            if province and not city.startswith("市辖区") and not city.startswith("县"):
                return province + city
            return province + city

        # 回退到 2 位省份代码
        province_code = code[:2]
        if province_code in _REGION_CODE_MAP:
            return _REGION_CODE_MAP[province_code]

        return None

    @staticmethod
    def _make_error_result(errors: list, birthday: str = "", gender: str = "", region: str = "") -> Dict[str, object]:
        """构建错误结果字典

        Args:
            errors: 错误信息列表
            birthday: 出生日期
            gender: 性别
            region: 地区

        Returns:
            包含错误信息的结果字典
        """
        return {
            "valid": False,
            "birthday": birthday,
            "gender": gender,
            "region": region,
            "errors": errors,
        }


# =============================================================================
# 便捷函数
# =============================================================================

_default_validator = ChineseIDValidator()


def 校验身份证(id_number: str) -> Dict[str, object]:
    """校验身份证号码

    Args:
        id_number: 18 位身份证号码

    Returns:
        校验结果字典
    """
    return _default_validator.validate(id_number)


def 提取出生日期(id_number: str) -> str:
    """提取身份证出生日期

    Args:
        id_number: 18 位身份证号码

    Returns:
        出生日期字符串
    """
    return _default_validator.get_birthday(id_number)


def 提取性别(id_number: str) -> str:
    """提取身份证性别

    Args:
        id_number: 18 位身份证号码

    Returns:
        "男" 或 "女"
    """
    return _default_validator.get_gender(id_number)


def 提取地区(id_number: str) -> str:
    """提取身份证地区

    Args:
        id_number: 18 位身份证号码

    Returns:
        地区名称
    """
    return _default_validator.get_region(id_number)


def 计算校验码(id_number: str) -> str:
    """计算身份证校验码

    Args:
        id_number: 17 位或 18 位身份证号码

    Returns:
        校验码字符
    """
    return _default_validator.generate_check_digit(id_number)


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    'ChineseIDValidator',
    '校验身份证',
    '提取出生日期',
    '提取性别',
    '提取地区',
    '计算校验码',
]