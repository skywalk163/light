/*
 * 光明（Light）编程语言 ANTLR4 词法定义
 *
 * 版本: v1.2
 * 恢复原始注释 token 定义以保持与 Parser 同步
 */

lexer grammar LightLangLexer;

// ----- 注释（保持原始定义）-----

LINE_COMMENT
    : '#' ~[\r\n]* -> channel(HIDDEN)
    ;

LINE_COMMENT_SLASH
    : '//' ~[\r\n]* -> channel(HIDDEN)
    ;

COMMENT_START
    : '```' -> pushMode(COMMENT_MODE), channel(HIDDEN)
    ;

mode COMMENT_MODE;
COMMENT_CLOSE
    : '```' -> popMode, channel(HIDDEN)
    ;
COMMENT_CONTENT
    : . -> channel(HIDDEN)
    ;

mode DEFAULT_MODE;

// ----- 双字关键字（v3.3 决策27）+ v4.0 L0 单字别名（长关键字在前避免部分匹配）-----

// 条件判断（三字优先于二字）
K_ELSE_IF  : '否则若' ;
K_IF       : '如果' | '若' ;
K_THEN     : '那么' | '则' ;
K_ELSE     : '否则' | '否' ;            // v4.0 新增 '否'(L0) 别名
K_END      : '结束' ;

// 比较运算符（三字优先于二字）
K_GE       : '大于等于' ;
K_LE       : '小于等于' ;
K_NE       : '不等于' ;
K_GT       : '大于' ;
K_LT       : '小于' ;

// 定义声明（统一语法 / v4.0 L0 单字别名）
K_SET      : '设' ;                     // 变量声明：设 甲 为 三
K_AS       : '为' ;                     // 赋值连接符
K_DEFINE   : '定义' ;                   // 保留兼容
K_EQUAL    : '等于' | '是' ;            // v4.0 '是'(L0) 别名 用于判断
K_SEGMENT  : '段落' | '段' | '函数' ;   // v4.0 '段'(L0) 为主形式
K_RECEIVE  : '接收' ;                   // 参数声明：段落 平方 接收 数值
K_DATA_TYPE: '数据类型' ;
K_ERROR_TYPE: '错误' ;
K_CONST    : '常量' ;
K_TYPE     : '类型' ;
K_EXPORT   : '导出' | '出' ;            // v4.0 '出'(L0) 别名
K_IMPORT   : '导入' | '导' ;            // v4.0 '导'(L0) 别名
K_FROM     : '从' ;

// 循环控制（v4.0 L0 单字别名）
K_FOREACH  : '遍历' | '遍' | '对' ;     // v4.0 '遍'(L0) 为主形式
K_WHILE    : '当' ;
K_BREAK    : '跳出' | '跳' ;            // v4.0 '跳'(L0) 别名
K_CONTINUE : '跳过' | '过' ;            // v4.0 '过'(L0) 别名

// 异常处理（v4.0 L0 单字别名）
K_TRY      : '尝试' | '试' ;            // v4.0 '试'(L0) 别名
K_CATCH    : '捕获' | '捕' ;            // v4.0 '捕'(L0) 别名
K_THROW    : '抛出' | '抛' ;            // v4.0 '抛'(L0) 别名
K_FINALLY  : '最终' | '终' ;            // v4.0 新增 finally

// 返回（v4.0 L0 单字别名）
K_RETURN   : '返回' | '返' ;            // v4.0 '返'(L0) 别名

// 模式匹配（v4.0 L0 单字别名）
K_MATCH    : '匹配' | '配' ;            // v4.0 '配'(L0) 别名
K_CASE     : '情况' ;                   // 匹配分支：情况 模式 ->

// 匿名函数（接收已存在为K_RECEIVE，此处不再重复）

// 数据操作
K_PRINT    : '打印' ;
K_OUTPUT   : '输出' ;
K_INPUT    : '输入' ;
K_READ     : '读取' ;

// 列表操作动词（保留部分不常用的）
K_FIRST    : '首' ;
K_LAST     : '末' ;
K_REST     : '余' ;
K_LENGTH   : '长' ;
K_SORT     : '排序' ;
K_REVERSE  : '反转' ;
// K_SUM, K_MAX, K_MIN 移除，避免与用户函数名冲突
// 改为内置函数，在语义层面识别
K_UNIQUE   : '去重' ;
K_FILTER   : '筛选' ;
K_MAP      : '映射' ;

// 字符串操作动词（保留不常用的）
K_TO_INT   : '转整数' ;
K_TO_FLOAT : '转浮点' ;
K_TO_STR   : '转字符串' ;
K_STR_LEN  : '字符串长度' ;
K_STR_SPLIT: '分割字符串' ;
K_STR_JOIN : '连接字符串' ;
K_STR_REPLACE: '替换字符串' ;
K_STR_TRIM : '去除空白' ;

// 文件操作动词
K_READ_FILE  : '读取文件' ;
K_WRITE_FILE : '写入文件' ;
K_APPEND_FILE: '追加文件' ;
K_FILE_EXISTS: '文件存在' ;
K_DIR_EXISTS : '目录存在' ;
K_MAKE_DIR   : '创建目录' ;
K_REMOVE_FILE: '删除文件' ;
K_REMOVE_DIR : '删除目录' ;

// 系统操作动词
K_ENV       : '环境变量' ;
K_SET_ENV   : '设置环境变量' ;
K_ARGS      : '参数列表' ;
K_EXIT      : '退出程序' ;
K_CWD       : '当前目录' ;
K_CD        : '切换目录' ;
K_EXEC      : '执行命令' ;

// 类相关（v4.0 L0 单字别名）
K_CLASS    : '类' ;
K_INTERFACE: '接口' | '接' ;            // v4.0 '接'(L0) 别名（接口/interface）
K_INHERIT  : '继承' | '承' ;            // v4.0 '承'(L0) 别名（extends）
K_IMPLEMENTS: '实现' ;                  // 新增：实现接口
K_PARENT   : '父' ;
K_SELF     : '己' | '自我' | '自' ;     // v4.0 '自'(L0) 为主形式
K_METHOD   : '方法' ;
K_ATTRIBUTE: '属性' ;                   // 新增：属性声明
K_CONSTRUCTOR: '构造' ;                 // 新增：构造函数
K_NEW      : '新建' ;                   // 新增：实例化对象

// L4 外语引用 / 嵌入块（v4.0 引 为推荐形式；嵌入 兼容保留）
K_EMBED       : '嵌入' | '引' ;         // v4.0 引 Python:
K_END_EMBED   : '结束嵌入' | '结束引' ; // v4.0 对应结束

// 逻辑运算
K_AND      : '且' | '与' ;
K_OR       : '或' ;
K_NOT      : '非' ;

// 算术运算（中文关键字）
K_PLUS     : '加' ;
K_MINUS    : '减' ;
K_MULTIPLY : '乘' ;
K_DIVIDE   : '除' ;
K_MOD      : '模' ;
K_POW      : '幂' ;

// 复合赋值运算符（Phase 5）
K_PLUS_ASSIGN     : '加上' ;
K_MINUS_ASSIGN    : '减去' ;
K_MULTIPLY_ASSIGN : '乘以' ;
K_DIVIDE_ASSIGN   : '除以' ;
K_MOD_ASSIGN      : '模以' ;
K_POW_ASSIGN      : '幂以' ;

// 连接符/管道
K_AND_WORD : '并' ;
K_OF       : '之' ;
K_AT       : '于' ;                  // 新增：用于遍历语句
K_DE       : '的' ;

// 特殊值
K_TRUE     : '真' ;
K_FALSE    : '假' ;
K_NULL     : '空' ;

// 上下文管理器
K_WITH     : '使用' ;               // 使用 表达式 作为 变量

// 装饰器
K_DECORATE : '标注' ;               // @段落名 标注

// ----- 内置类型 -----

T_NUMBER   : '数' ;
T_INT      : '整数' ;
T_FLOAT    : '浮数' ;
T_STRING   : '串' ;
T_LIST     : '列' ;
T_DICT     : '典' ;
T_SET      : '集' ;
T_BOOL     : '布尔' ;
T_ANY      : '任意' ;

// 通配符（用于模式匹配）
UNDERSCORE : '_' ;

// ----- 符号运算符（英文/符号）-----

POW        : '^' | '**' ;   // v4.0 支持 Python 风格 ** 幂
MODULO     : '%' ;
MULTIPLY   : '*' | '×' ;
DIVIDE     : '/' | '÷' ;
PLUS       : '+' ;
MINUS      : '-' ;

// 比较符号
EQ         : '==' ;           // 仅用于比较
NE         : '!=' ;
GE         : '>=' ;
LE         : '<=' ;
GT         : '>' ;
LT         : '<' ;

// 赋值符号
ASSIGN     : '=' ;            // 仅用于赋值

// 逻辑符号
NOT        : '!' ;
AND        : '&&' ;
OR         : '||' ;

// 管道/箭头
PIPE       : '->' ;

// 装饰器符号
AT         : '@' ;

// 路径分隔符
PATH_SEP   : '/' | '／' ;

// ----- 标点符号（中英文双模式）-----

DOT        : '.' ;               // 英文点号：属性访问
PERIOD     : '。' ;              // 中文句号：语句结束
COMMA      : '，' | ',' ;        // 逗号：分隔符/管道
COLON      : '：' | ':' ;        // 冒号：块定义/类型注解
SEMICOLON  : '；' | ';' ;        // 分号：多语句分隔
PAUSE      : '、' ;              // 顿号：参数并列

// ----- 括号 -----

LPAREN     : '（' | '(' ;
RPAREN     : '）' | ')' ;
LBRACKET   : '【' | '[' ;
RBRACKET   : '】' | ']' ;
LBRACE     : '{' ;
RBRACE     : '}' ;
BOOK_L     : '《' ;
BOOK_R     : '》' ;

// ----- 字面量 -----

NUMBER
    : [0-9]+ ( '.' [0-9]+ )?
    ;

STRING
    : '"' ( '\\' . | ~["\\] )* '"'
    | '\'' ( '\\' . | ~['\\] )* '\''
    ;

// ----- 标识符（含中文字符）-----

fragment IDEOGRAPHIC
    : [\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]
    ;

fragment LETTER
    : [a-zA-Z_]
    ;

fragment DIGIT
    : [0-9]
    ;

ID
    : ( IDEOGRAPHIC | LETTER ) ( IDEOGRAPHIC | LETTER | DIGIT )*
    ;

// ----- 空白 -----

NEWLINE
    : '\r'? '\n' -> skip
    ;

WS
    : [ \t]+ -> skip
    ;

// ----- 未知字符（捕获错误）-----

UNKNOWN
    : .
    ;
