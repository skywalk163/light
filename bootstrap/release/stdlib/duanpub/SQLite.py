"""
SQLite — duanpub 桥接模块

基于 Python sqlite3 库封装，函数名对齐 duanpub/packages/SQLite/源.duan。

duanpub 原始包通过 C FFI 直接调用 SQLite3 C API，
本桥接模块用 Python sqlite3 模块替代，提供等价的数据库操作功能。

数据结构对齐 duanpub 源.duan:
- DBConn: 数据库连接
- QueryResult: 查询结果
- Stmt: 预处理语句
- QueryBuilder: 查询构建器
- Migration: 数据库迁移
"""

import sqlite3 as _sqlite3


# =============================================================================
# 数据结构（对齐 duanpub 源.duan 的结构体定义）
# =============================================================================

class DBConn:
    """数据库连接"""
    def __init__(self, path='', opened=False):
        self.path = path
        self.opened = opened
        self._conn = None


class QueryResult:
    """查询结果"""
    def __init__(self, col_names=None, rows=None, row_count=0, col_count=0):
        self.col_names = col_names or []
        self.rows = rows or []
        self.row_count = row_count
        self.col_count = col_count


class Stmt:
    """预处理语句"""
    def __init__(self, sql='', db=None):
        self.sql = sql
        self.db = db
        self._stmt = None


class QueryBuilder:
    """查询构建器"""
    def __init__(self, table=''):
        self.table = table
        self.select_cols = []
        self.conds = []
        self.cond_params = []
        self.orders = []
        self.groups = []
        self.limit = None
        self.offset = None
        self.joins = []


class Migration:
    """数据库迁移"""
    def __init__(self, version=0, desc='', up_sql='', down_sql=''):
        self.version = version
        self.desc = desc
        self.up_sql = up_sql
        self.down_sql = down_sql


# =============================================================================
# 连接管理
# =============================================================================

def 打开数据库(路径):
    """打开/创建 SQLite 数据库，返回 DBConn"""
    if not 路径:
        raise Exception("打开数据库失败: 路径为空")
    try:
        conn = _sqlite3.connect(路径)
        conn.row_factory = _sqlite3.Row
        return DBConn(path=路径, opened=True)._replace_conn(conn)
    except Exception as e:
        raise Exception("打开数据库失败: " + str(e))


def 关闭数据库(db):
    """关闭数据库连接"""
    if not db or not db.opened:
        return
    if db._conn:
        try:
            db._conn.close()
        except Exception:
            pass
    db.opened = False
    db._conn = None


# 为 DBConn 添加 _replace_conn 方法（因为 __init__ 不接受 _conn 参数）
def _dbconn_replace_conn(self, conn):
    self._conn = conn
    return self

DBConn._replace_conn = _dbconn_replace_conn


# =============================================================================
# SQL 执行
# =============================================================================

def 执行SQL(db, sql, params=None):
    """执行 SQL 语句（INSERT/UPDATE/DELETE/DDL），返回受影响行数"""
    if not db or not db.opened or not db._conn:
        raise Exception("执行SQL失败: 数据库未打开")
    try:
        cursor = db._conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        db._conn.commit()
        return cursor.rowcount
    except Exception as e:
        raise Exception("执行SQL失败: " + str(e))


def 批量执行(db, sql, params_list):
    """批量执行 SQL（参数化），返回受影响行数"""
    if not db or not db.opened or not db._conn:
        raise Exception("批量执行失败: 数据库未打开")
    try:
        cursor = db._conn.cursor()
        cursor.executemany(sql, params_list)
        db._conn.commit()
        return cursor.rowcount
    except Exception as e:
        raise Exception("批量执行失败: " + str(e))


# =============================================================================
# 查询
# =============================================================================

def 查询(db, sql, params=None):
    """执行查询 SQL，返回 QueryResult"""
    if not db or not db.opened or not db._conn:
        raise Exception("查询失败: 数据库未打开")
    try:
        cursor = db._conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        rows = cursor.fetchall()
        col_names = [desc[0] for desc in cursor.description] if cursor.description else []
        # 将 Row 对象转为列表
        row_list = []
        for row in rows:
            if isinstance(row, _sqlite3.Row):
                row_list.append(list(row))
            else:
                row_list.append(list(row))
        return QueryResult(
            col_names=col_names,
            rows=row_list,
            row_count=len(row_list),
            col_count=len(col_names)
        )
    except Exception as e:
        raise Exception("查询失败: " + str(e))


def 查询单条(db, sql, params=None):
    """查询单条记录，返回 dict 或 None"""
    result = 查询(db, sql, params)
    if result.row_count == 0:
        return None
    row = result.rows[0]
    return dict(zip(result.col_names, row))


def 查询所有(db, sql, params=None):
    """查询所有记录，返回 list[dict]"""
    result = 查询(db, sql, params)
    return [dict(zip(result.col_names, row)) for row in result.rows]


# =============================================================================
# 事务管理
# =============================================================================

def 开始事务(db):
    """开始事务"""
    if not db or not db._conn:
        raise Exception("开始事务失败: 数据库未打开")
    db._conn.execute("BEGIN")


def 提交事务(db):
    """提交事务"""
    if not db or not db._conn:
        raise Exception("提交事务失败: 数据库未打开")
    db._conn.commit()


def 回滚事务(db):
    """回滚事务"""
    if not db or not db._conn:
        raise Exception("回滚事务失败: 数据库未打开")
    db._conn.rollback()


# =============================================================================
# 便捷函数
# =============================================================================

def 最后插入ID(db):
    """获取最后插入的行 ID"""
    if not db or not db._conn:
        raise Exception("获取最后插入ID失败: 数据库未打开")
    return db._conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def 受影响行数(db):
    """获取上次操作受影响行数"""
    if not db or not db._conn:
        return 0
    return db._conn.total_changes


def 表是否存在(db, 表名):
    """检查表是否存在"""
    result = 查询单条(db, "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (表名,))
    return result is not None


def 获取所有表(db):
    """获取所有表名列表"""
    result = 查询(db, "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [row[0] for row in result.rows]


def 获取表结构(db, 表名):
    """获取表的列信息"""
    result = 查询(db, "PRAGMA table_info(" + 表名 + ")")
    columns = []
    for row in result.rows:
        columns.append({
            '序号': row[0],
            '名称': row[1],
            '类型': row[2],
            '非空': row[3] == 1,
            '默认值': row[4],
            '主键': row[5] == 1,
        })
    return columns


# =============================================================================
# 预处理语句
# =============================================================================

def 准备语句(db, sql):
    """准备 SQL 语句，返回 Stmt"""
    if not db or not db.opened or not db._conn:
        raise Exception("准备语句失败: 数据库未打开")
    try:
        stmt = Stmt(sql=sql, db=db)
        stmt._stmt = db._conn.cursor()
        return stmt
    except Exception as e:
        raise Exception("准备语句失败: " + str(e))


def 绑定文本(stmt, index, value):
    """绑定文本参数"""
    stmt._stmt.bindparam(index, value)


def 绑定整数(stmt, index, value):
    """绑定整数参数"""
    stmt._stmt.bindparam(index, value)


def 绑定浮点(stmt, index, value):
    """绑定浮点参数"""
    stmt._stmt.bindparam(index, value)


def 绑定空值(stmt, index):
    """绑定 NULL 参数"""
    stmt._stmt.bindparam(index, None)


def 执行语句(stmt):
    """执行预处理语句"""
    stmt._stmt.execute(stmt.sql)


def 重置语句(stmt):
    """重置预处理语句"""
    # sqlite3 cursor 不直接支持 reset，重新 prepare
    if stmt.db and stmt.db._conn:
        stmt._stmt = stmt.db._conn.cursor()


def 释放语句(stmt):
    """释放预处理语句"""
    if stmt._stmt:
        stmt._stmt.close()
        stmt._stmt = None


# =============================================================================
# 查询构建器（简化版）
# =============================================================================

def 创建查询(table):
    """创建查询构建器"""
    return QueryBuilder(table=table)


def 查询构建器_select(qb, *cols):
    """设置查询列"""
    qb.select_cols = list(cols)
    return qb


def 查询构建器_where(qb, condition, *params):
    """添加 WHERE 条件"""
    qb.conds.append(condition)
    qb.cond_params.extend(params)
    return qb


def 查询构建器_order(qb, *orders):
    """添加 ORDER BY"""
    qb.orders.extend(orders)
    return qb


def 查询构建器_limit(qb, limit, offset=None):
    """设置 LIMIT"""
    qb.limit = limit
    qb.offset = offset
    return qb


def 查询构建器执行(db, qb):
    """执行查询构建器，返回 QueryResult"""
    sql = "SELECT "
    if qb.select_cols:
        sql += ", ".join(qb.select_cols)
    else:
        sql += "*"
    sql += " FROM " + qb.table

    params = []
    if qb.conds:
        sql += " WHERE " + " AND ".join(qb.conds)
        params = qb.cond_params

    if qb.orders:
        sql += " ORDER BY " + ", ".join(qb.orders)

    if qb.limit is not None:
        sql += " LIMIT ?"
        params.append(qb.limit)
        if qb.offset is not None:
            sql += " OFFSET ?"
            params.append(qb.offset)

    return 查询(db, sql, params if params else None)
