"""
配置管理 — lightpub 桥接模块

基于 Python configparser 库封装，函数名对齐上游 duanpub（段言时期）packages/配置管理/源.duan。

上游 duanpub 原始包通过 C FFI 实现自研配置解析引擎，
本桥接模块用 Python configparser/json 等标准库模块替代，
提供等价的配置管理功能，支持 INI/JSON/YAML/TOML 多格式加载与保存。
函数签名与上游 duanpub（段言时期）包保持一致。
"""

import configparser as _configparser
import json as _json
import os as _os


# =============================================================================
# 配置项
# =============================================================================

class 配置项:
    """单个配置项"""
    def __init__(self, 键="", 值="", 描述="", 类型="字符串"):
        self.键 = 键
        self.值 = 值
        self.描述 = 描述
        self.类型 = 类型  # 字符串, 整数, 浮点数, 布尔, JSON


# =============================================================================
# 内部：配置源实现
# =============================================================================

class _配置源:
    """内部配置源，存储键值对"""
    def __init__(self, 名称="默认"):
        self.名称 = 名称
        self._数据 = {}
        self._文件路径 = None
        self._格式 = "dict"

    def 全部键(self):
        return list(self._数据.keys())

    def 导出字典(self):
        return dict(self._数据)


# =============================================================================
# 配置源操作
# =============================================================================

def 创建配置源(名称="默认"):
    """创建配置源"""
    return _配置源(名称)


def 从字典加载(配置源, 字典数据):
    """从字典加载配置"""
    if not isinstance(字典数据, dict):
        raise Exception("从字典加载失败: 数据不是字典类型")
    _展平字典(配置源._数据, 字典数据, "")
    配置源._格式 = "dict"
    return 配置源


def 从文件加载(配置源, 文件路径, 格式="ini"):
    """从文件加载配置（支持 ini/json/yaml/toml）"""
    if not 文件路径:
        raise Exception("从文件加载失败: 文件路径为空")
    if not _os.path.exists(文件路径):
        raise Exception("从文件加载失败: 文件不存在 " + 文件路径)

    try:
        格式 = 格式.lower()
        if 格式 == "ini":
            _加载_ini(配置源, 文件路径)
        elif 格式 == "json":
            _加载_json(配置源, 文件路径)
        elif 格式 == "yaml":
            _加载_yaml(配置源, 文件路径)
        elif 格式 == "toml":
            _加载_toml(配置源, 文件路径)
        else:
            raise Exception("从文件加载失败: 不支持的格式 " + 格式)
        配置源._文件路径 = 文件路径
        配置源._格式 = 格式
    except Exception as e:
        if "不支持的格式" in str(e) or "从文件加载失败" in str(e):
            raise
        raise Exception("从文件加载失败: " + str(e))
    return 配置源


def _加载_ini(配置源, 文件路径):
    """内部：从 INI 文件加载配置"""
    parser = _configparser.ConfigParser()
    parser.read(文件路径, encoding='utf-8')
    for section in parser.sections():
        for key, value in parser[section].items():
            配置源._数据[section + "." + key] = value


def _加载_json(配置源, 文件路径):
    """内部：从 JSON 文件加载配置"""
    with open(文件路径, 'r', encoding='utf-8') as f:
        data = _json.load(f)
    _展平字典(配置源._数据, data, "")


def _加载_yaml(配置源, 文件路径):
    """内部：从 YAML 文件加载配置"""
    try:
        import yaml as _yaml
    except ImportError:
        raise Exception("加载 YAML 失败: 需要安装 PyYAML 库 (pip install pyyaml)")
    with open(文件路径, 'r', encoding='utf-8') as f:
        data = _yaml.safe_load(f)
    if data is not None:
        _展平字典(配置源._数据, data, "")


def _加载_toml(配置源, 文件路径):
    """内部：从 TOML 文件加载配置"""
    try:
        import tomllib as _tomllib
    except ImportError:
        try:
            import tomli as _tomllib
        except ImportError:
            raise Exception("加载 TOML 失败: 需要安装 tomli 库 (pip install tomli)")
    with open(文件路径, 'rb') as f:
        data = _tomllib.load(f)
    _展平字典(配置源._数据, data, "")


def _展平字典(目标, 数据, 前缀):
    """内部：递归展平字典为点号分隔的键值对"""
    if isinstance(数据, dict):
        for key, value in 数据.items():
            新键 = 前缀 + "." + key if 前缀 else key
            if isinstance(value, dict):
                _展平字典(目标, value, 新键)
            else:
                目标[新键] = value
    elif isinstance(数据, list):
        目标[前缀] = 数据


def 从环境变量加载(配置源, 前缀=""):
    """从环境变量加载配置"""
    try:
        for key, value in _os.environ.items():
            if 前缀:
                if key.startswith(前缀):
                    配置源._数据[key] = value
            else:
                配置源._数据[key] = value
    except Exception as e:
        raise Exception("从环境变量加载失败: " + str(e))
    return 配置源


def 获取(配置源, 键, 默认值=None):
    """获取配置项"""
    try:
        return 配置源._数据.get(键, 默认值)
    except Exception as e:
        raise Exception("获取配置失败: " + str(e))


def 设置(配置源, 键, 值):
    """设置配置项"""
    try:
        配置源._数据[键] = 值
    except Exception as e:
        raise Exception("设置配置失败: " + str(e))


def 获取整数(配置源, 键, 默认值=0):
    """获取整数配置"""
    try:
        value = 配置源._数据.get(键)
        if value is None:
            return 默认值
        return int(value)
    except (ValueError, TypeError):
        return 默认值
    except Exception as e:
        raise Exception("获取整数配置失败: " + str(e))


def 获取浮点数(配置源, 键, 默认值=0.0):
    """获取浮点数配置"""
    try:
        value = 配置源._数据.get(键)
        if value is None:
            return 默认值
        return float(value)
    except (ValueError, TypeError):
        return 默认值
    except Exception as e:
        raise Exception("获取浮点数配置失败: " + str(e))


def 获取布尔(配置源, 键, 默认值=False):
    """获取布尔配置"""
    try:
        value = 配置源._数据.get(键)
        if value is None:
            return 默认值
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on', '是', '真')
        return bool(value)
    except Exception as e:
        raise Exception("获取布尔配置失败: " + str(e))


def 获取列表(配置源, 键, 分隔符=",", 默认值=None):
    """获取列表配置"""
    if 默认值 is None:
        默认值 = []
    try:
        value = 配置源._数据.get(键)
        if value is None:
            return 默认值
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [item.strip() for item in value.split(分隔符) if item.strip()]
        return [str(value)]
    except Exception as e:
        raise Exception("获取列表配置失败: " + str(e))


def 获取字典(配置源, 键, 默认值=None):
    """获取字典配置（JSON 格式）"""
    if 默认值 is None:
        默认值 = {}
    try:
        value = 配置源._数据.get(键)
        if value is None:
            return 默认值
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            return _json.loads(value)
        return 默认值
    except (_json.JSONDecodeError, TypeError):
        return 默认值
    except Exception as e:
        raise Exception("获取字典配置失败: " + str(e))


def 包含(配置源, 键):
    """检查配置项是否存在"""
    try:
        return 键 in 配置源._数据
    except Exception as e:
        raise Exception("检查配置项失败: " + str(e))


def 删除(配置源, 键):
    """删除配置项"""
    try:
        if 键 in 配置源._数据:
            del 配置源._数据[键]
    except Exception as e:
        raise Exception("删除配置失败: " + str(e))


def 全部键(配置源):
    """获取所有配置键"""
    try:
        return 配置源.全部键()
    except Exception as e:
        raise Exception("获取全部键失败: " + str(e))


def 导出字典(配置源):
    """导出配置为字典"""
    try:
        return 配置源.导出字典()
    except Exception as e:
        raise Exception("导出字典失败: " + str(e))


def 保存到文件(配置源, 文件路径, 格式="ini"):
    """保存配置到文件"""
    if not 文件路径:
        raise Exception("保存到文件失败: 文件路径为空")
    try:
        格式 = 格式.lower()
        if 格式 == "ini":
            _保存_ini(配置源, 文件路径)
        elif 格式 == "json":
            _保存_json(配置源, 文件路径)
        elif 格式 == "yaml":
            _保存_yaml(配置源, 文件路径)
        elif 格式 == "toml":
            _保存_toml(配置源, 文件路径)
        else:
            raise Exception("保存到文件失败: 不支持的格式 " + 格式)
    except Exception as e:
        if "不支持的格式" in str(e) or "保存到文件失败" in str(e):
            raise
        raise Exception("保存到文件失败: " + str(e))


def _保存_ini(配置源, 文件路径):
    """内部：保存配置为 INI 文件"""
    parser = _configparser.ConfigParser()
    sections = {}
    for key, value in 配置源._数据.items():
        if "." in key:
            section, option = key.split(".", 1)
            if section not in sections:
                sections[section] = {}
            sections[section][option] = str(value)
        else:
            if "DEFAULT" not in sections:
                sections["DEFAULT"] = {}
            sections["DEFAULT"][key] = str(value)
    for section, options in sections.items():
        parser[section] = options
    with open(文件路径, 'w', encoding='utf-8') as f:
        parser.write(f)


def _保存_json(配置源, 文件路径):
    """内部：保存配置为 JSON 文件"""
    data = _恢复嵌套字典(配置源._数据)
    with open(文件路径, 'w', encoding='utf-8') as f:
        _json.dump(data, f, indent=2, ensure_ascii=False)


def _保存_yaml(配置源, 文件路径):
    """内部：保存配置为 YAML 文件"""
    try:
        import yaml as _yaml
    except ImportError:
        raise Exception("保存 YAML 失败: 需要安装 PyYAML 库 (pip install pyyaml)")
    data = _恢复嵌套字典(配置源._数据)
    with open(文件路径, 'w', encoding='utf-8') as f:
        _yaml.dump(data, f, allow_unicode=True, indent=2)


def _保存_toml(配置源, 文件路径):
    """内部：保存配置为 TOML 文件"""
    try:
        import tomli_w as _tomli_w
    except ImportError:
        raise Exception("保存 TOML 失败: 需要安装 tomli-w 库 (pip install tomli-w)")
    data = _恢复嵌套字典(配置源._数据)
    with open(文件路径, 'wb') as f:
        _tomli_w.dump(data, f)


def _恢复嵌套字典(扁平数据):
    """内部：将点号分隔的扁平键恢复为嵌套字典"""
    result = {}
    for key, value in 扁平数据.items():
        parts = key.split(".")
        当前 = result
        for part in parts[:-1]:
            if part not in 当前:
                当前[part] = {}
            if not isinstance(当前[part], dict):
                当前[part] = {}
            当前 = 当前[part]
        当前[parts[-1]] = value
    return result


def 刷新(配置源):
    """重新加载配置"""
    if 配置源._文件路径 and _os.path.exists(配置源._文件路径):
        配置源._数据.clear()
        从文件加载(配置源, 配置源._文件路径, 配置源._格式)
    return 配置源


# =============================================================================
# 配置管理器（多源管理）
# =============================================================================

class 配置管理器:
    """配置管理器，支持多源配置和优先级"""
    def __init__(self, 名称="默认"):
        self.名称 = 名称
        self._配置源列表 = []  # [(优先级, 配置源), ...]
        self._监听器 = []

    def 添加源(self, 配置源, 优先级=0):
        """添加配置源（优先级越高越优先）"""
        self._配置源列表.append((优先级, 配置源))
        self._配置源列表.sort(key=lambda x: x[0], reverse=True)

    def 移除源(self, 配置源名称):
        """移除配置源"""
        self._配置源列表 = [
            (p, s) for p, s in self._配置源列表
            if s.名称 != 配置源名称
        ]

    def 获取(self, 键, 默认值=None):
        """获取配置（按优先级从高到低查找）"""
        for 优先级, 配置源 in self._配置源列表:
            value = 获取(配置源, 键)
            if value is not None:
                return value
        return 默认值

    def 设置(self, 键, 值):
        """设置配置到最高优先级源"""
        if not self._配置源列表:
            raise Exception("配置管理器设置失败: 没有配置源")
        最高源 = self._配置源列表[0][1]
        旧值 = 获取(最高源, 键)
        设置(最高源, 键, 值)
        self.通知变更(键, 旧值, 值)

    def 注册监听器(self, 回调函数):
        """注册配置变更监听器"""
        if 回调函数 not in self._监听器:
            self._监听器.append(回调函数)

    def 通知变更(self, 键, 旧值, 新值):
        """通知配置变更"""
        for 监听器 in self._监听器:
            try:
                监听器(键, 旧值, 新值)
            except Exception:
                pass


# =============================================================================
# 快捷操作
# =============================================================================

def 创建配置(名称="默认"):
    """创建配置管理器（快捷方式）"""
    return 配置管理器(名称)


def 创建INI配置(文件路径):
    """创建基于 INI 文件的配置"""
    if not 文件路径:
        raise Exception("创建INI配置失败: 文件路径为空")
    源 = 创建配置源("ini源")
    if _os.path.exists(文件路径):
        从文件加载(源, 文件路径, "ini")
    管理器 = 配置管理器("ini配置")
    管理器.添加源(源)
    return 管理器


def 创建JSON配置(文件路径):
    """创建基于 JSON 文件的配置"""
    if not 文件路径:
        raise Exception("创建JSON配置失败: 文件路径为空")
    源 = 创建配置源("json源")
    if _os.path.exists(文件路径):
        从文件加载(源, 文件路径, "json")
    管理器 = 配置管理器("json配置")
    管理器.添加源(源)
    return 管理器


def 创建分层配置(字典数据):
    """创建分层配置（支持点号分隔的键路径）"""
    if not isinstance(字典数据, dict):
        raise Exception("创建分层配置失败: 数据不是字典类型")
    源 = 创建配置源("分层源")
    从字典加载(源, 字典数据)
    管理器 = 配置管理器("分层配置")
    管理器.添加源(源)
    return 管理器