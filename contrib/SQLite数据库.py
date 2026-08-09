"""
光明标准库 - SQLite数据库模块

提供SQLite数据库操作功能，包括：
- 数据库连接与管理
- SQL查询与执行
- 事务管理
- 数据导入导出
- 表结构管理
"""

import sqlite3
import os
import json
from typing import Any, List, Dict, Optional, Union, Tuple


class SQLite数据库:
    """SQLite数据库连接类"""
    
    def __init__(self, 数据库路径: str = ":memory:"):
        """
        初始化数据库连接
        
        参数:
            数据库路径: 数据库文件路径，":memory:" 表示内存数据库
        """
        self.路径 = 数据库路径
        self._连接 = None
        self._连接 = sqlite3.connect(数据库路径)
        self._连接.row_factory = sqlite3.Row
        self.自动提交 = True
    
    def 执行(self, SQL语句: str, 参数: Union[tuple, list, dict] = None) -> int:
        """
        执行SQL语句
        
        参数:
            SQL语句: SQL语句
            参数: 查询参数
        
        返回:
            受影响的行数
        """
        游标 = self._连接.cursor()
        if 参数 is None:
            游标.execute(SQL语句)
        else:
            游标.execute(SQL语句, 参数)
        if self.自动提交:
            self._连接.commit()
        return 游标.rowcount
    
    def 查询(self, SQL语句: str, 参数: Union[tuple, list, dict] = None) -> List[Dict[str, Any]]:
        """
        执行查询并返回结果列表
        
        参数:
            SQL语句: SELECT语句
            参数: 查询参数
        
        返回:
            字典列表，每行一个字典
        """
        游标 = self._连接.cursor()
        if 参数 is None:
            游标.execute(SQL语句)
        else:
            游标.execute(SQL语句, 参数)
        行列表 = 游标.fetchall()
        return [dict(行) for 行 in 行列表]
    
    def 查询一行(self, SQL语句: str, 参数: Union[tuple, list, dict] = None) -> Optional[Dict[str, Any]]:
        """
        查询单行数据
        
        参数:
            SQL语句: SELECT语句
            参数: 查询参数
        
        返回:
            行字典，无结果返回None
        """
        结果 = self.查询(SQL语句, 参数)
        return 结果[0] if 结果 else None
    
    def 查询值(self, SQL语句: str, 参数: Union[tuple, list, dict] = None) -> Any:
        """
        查询单个值
        
        参数:
            SQL语句: SELECT语句
            参数: 查询参数
        
        返回:
            第一列的第一个值
        """
        游标 = self._连接.cursor()
        if 参数 is None:
            游标.execute(SQL语句)
        else:
            游标.execute(SQL语句, 参数)
        行 = 游标.fetchone()
        return 行[0] if 行 else None
    
    def 执行脚本(self, SQL脚本: str) -> None:
        """
        执行多个SQL语句组成的脚本
        
        参数:
            SQL脚本: SQL脚本字符串
        """
        游标 = self._连接.cursor()
        游标.executescript(SQL脚本)
        if self.自动提交:
            self._连接.commit()
    
    def 批量执行(self, SQL语句: str, 参数列表: List[Union[tuple, list, dict]]) -> int:
        """
        批量执行SQL语句
        
        参数:
            SQL语句: SQL语句
            参数列表: 参数列表
        
        返回:
            受影响的总行数
        """
        游标 = self._连接.cursor()
        游标.executemany(SQL语句, 参数列表)
        if self.自动提交:
            self._连接.commit()
        return 游标.rowcount
    
    def 提交(self) -> None:
        """提交事务"""
        self._连接.commit()
    
    def 回滚(self) -> None:
        """回滚事务"""
        self._连接.rollback()
    
    def 开始事务(self) -> None:
        """开始事务（关闭自动提交）"""
        self.自动提交 = False
    
    def 结束事务(self, 提交: bool = True) -> None:
        """
        结束事务
        
        参数:
            提交: True提交，False回滚
        """
        if 提交:
            self.提交()
        else:
            self.回滚()
        self.自动提交 = True
    
    def 表存在(self, 表名: str) -> bool:
        """
        检查表是否存在
        
        参数:
            表名: 表名
        
        返回:
            是否存在
        """
        结果 = self.查询值(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
            (表名,)
        )
        return 结果 > 0
    
    def 获取表列表(self) -> List[str]:
        """获取所有表名列表"""
        结果 = self.查询(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        return [行['name'] for 行 in 结果]
    
    def 获取表结构(self, 表名: str) -> List[Dict[str, Any]]:
        """
        获取表结构信息
        
        参数:
            表名: 表名
        
        返回:
            列信息列表
        """
        return self.查询(f"PRAGMA table_info('{表名}')")
    
    def 创建表(self, 表名: str, 列定义: Dict[str, str], 主键: List[str] = None) -> None:
        """
        创建表
        
        参数:
            表名: 表名
            列定义: {列名: 类型} 的字典
            主键: 主键列名列表
        """
        列列表 = []
        for 列名, 类型 in 列定义.items():
            列列表.append(f"{列名} {类型}")
        
        if 主键:
            主键列 = ", ".join(主键)
            列列表.append(f"PRIMARY KEY ({主键列})")
        
        列定义字符串 = ", ".join(列列表)
        self.执行(f"CREATE TABLE IF NOT EXISTS {表名} ({列定义字符串})")
    
    def 删除表(self, 表名: str) -> None:
        """删除表"""
        self.执行(f"DROP TABLE IF EXISTS {表名}")
    
    def 插入(self, 表名: str, 数据: Dict[str, Any]) -> int:
        """
        插入一行数据
        
        参数:
            表名: 表名
            数据: {列名: 值} 的字典
        
        返回:
            最后插入的行ID
        """
        列列表 = list(数据.keys())
        占位符 = ",".join(["?"] * len(列列表))
        列字符串 = ",".join(列列表)
        值列表 = list(数据.values())
        
        游标 = self._连接.cursor()
        游标.execute(
            f"INSERT INTO {表名} ({列字符串}) VALUES ({占位符})",
            值列表
        )
        if self.自动提交:
            self._连接.commit()
        return 游标.lastrowid
    
    def 批量插入(self, 表名: str, 数据列表: List[Dict[str, Any]]) -> int:
        """
        批量插入数据
        
        参数:
            表名: 表名
            数据列表: 数据字典列表
        
        返回:
            插入的行数
        """
        if not 数据列表:
            return 0
        
        列列表 = list(数据列表[0].keys())
        占位符 = ",".join(["?"] * len(列列表))
        列字符串 = ",".join(列列表)
        
        参数列表 = [list(行.values()) for 行 in 数据列表]
        return self.批量执行(
            f"INSERT INTO {表名} ({列字符串}) VALUES ({占位符})",
            参数列表
        )
    
    def 更新(self, 表名: str, 数据: Dict[str, Any], 条件: str = "", 条件参数: tuple = ()) -> int:
        """
        更新数据
        
        参数:
            表名: 表名
            数据: {列名: 新值} 的字典
            条件: WHERE条件（不带WHERE）
            条件参数: 条件参数
        
        返回:
            受影响的行数
        """
        赋值列表 = [f"{列} = ?" for 列 in 数据.keys()]
        赋值字符串 = ", ".join(赋值列表)
        所有参数 = list(数据.values()) + list(条件参数)
        
        SQL语句 = f"UPDATE {表名} SET {赋值字符串}"
        if 条件:
            SQL语句 += f" WHERE {条件}"
        
        return self.执行(SQL语句, 所有参数)
    
    def 删除(self, 表名: str, 条件: str = "", 条件参数: tuple = ()) -> int:
        """
        删除数据
        
        参数:
            表名: 表名
            条件: WHERE条件（不带WHERE）
            条件参数: 条件参数
        
        返回:
            删除的行数
        """
        SQL语句 = f"DELETE FROM {表名}"
        if 条件:
            SQL语句 += f" WHERE {条件}"
        return self.执行(SQL语句, 条件参数)
    
    def 计数(self, 表名: str, 条件: str = "", 条件参数: tuple = ()) -> int:
        """
        统计表行数
        
        参数:
            表名: 表名
            条件: WHERE条件
            条件参数: 条件参数
        
        返回:
            行数
        """
        SQL语句 = f"SELECT COUNT(*) FROM {表名}"
        if 条件:
            SQL语句 += f" WHERE {条件}"
        return self.查询值(SQL语句, 条件参数)
    
    def 导出为JSON(self, 表名: str, 输出文件: str = None, 条件: str = "", 条件参数: tuple = ()) -> str:
        """
        导出表数据为JSON
        
        参数:
            表名: 表名
            输出文件: 输出文件路径，None返回JSON字符串
            条件: WHERE条件
            条件参数: 条件参数
        
        返回:
            JSON字符串（写入文件时返回空字符串）
        """
        数据 = self.查询(f"SELECT * FROM {表名}" + (f" WHERE {条件}" if 条件 else ""), 条件参数)
        json字符串 = json.dumps(数据, ensure_ascii=False, indent=2)
        
        if 输出文件:
            with open(输出文件, 'w', encoding='utf-8') as f:
                f.write(json字符串)
            return ""
        return json字符串
    
    def 从JSON导入(self, 表名: str, JSON数据: Union[str, List[Dict]], 创建表: bool = False) -> int:
        """
        从JSON导入数据
        
        参数:
            表名: 表名
            JSON数据: JSON字符串或数据列表
            创建表: 是否自动创建表
        
        返回:
            导入的行数
        """
        if isinstance(JSON数据, str):
            数据列表 = json.loads(JSON数据)
        else:
            数据列表 = JSON数据
        
        if not 数据列表:
            return 0
        
        if 创建表 and not self.表存在(表名):
            第一行 = 数据列表[0]
            列定义 = {列: "TEXT" for 列 in 第一行.keys()}
            self.创建表(表名, 列定义)
        
        return self.批量插入(表名, 数据列表)
    
    def 备份(self, 备份路径: str) -> None:
        """
        备份数据库到另一个文件
        
        参数:
            备份路径: 备份文件路径
        """
        备份连接 = sqlite3.connect(备份路径)
        self._连接.backup(备份连接)
        备份连接.close()
    
    def 关闭(self) -> None:
        """关闭数据库连接"""
        if self._连接:
            self._连接.close()
            self._连接 = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, 异常类型, 异常值, 追溯):
        self.关闭()
        return False


def 打开数据库(路径: str = ":memory:") -> SQLite数据库:
    """
    打开数据库连接（便捷函数）
    
    参数:
        路径: 数据库文件路径
    
    返回:
        SQLite数据库对象
    """
    return SQLite数据库(路径)


def 创建内存数据库() -> SQLite数据库:
    """创建内存数据库"""
    return SQLite数据库(":memory:")


def 数据库存在(路径: str) -> bool:
    """
    检查数据库文件是否存在且有效
    
    参数:
        路径: 数据库文件路径
    
    返回:
        是否为有效SQLite数据库
    """
    if not os.path.exists(路径):
        return False
    try:
        conn = sqlite3.connect(路径)
        conn.execute("SELECT COUNT(*) FROM sqlite_master")
        conn.close()
        return True
    except:
        return False


def 获取SQLite版本() -> str:
    """获取SQLite版本"""
    return sqlite3.sqlite_version


__all__ = [
    'SQLite数据库',
    '打开数据库',
    '创建内存数据库',
    '数据库存在',
    '获取SQLite版本',
]
