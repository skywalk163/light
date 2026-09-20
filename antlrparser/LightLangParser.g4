/*
 * 光明（Light）编程语言 ANTLR4 语法定义
 *
 * 版本: v1.0
 * 独立的 Parser 语法，配合 LightLangLexer 使用
 */

parser grammar LightLangParser;

options { tokenVocab = LightLangLexer; }

@header {
from typing import List, Optional, Tuple, Any, Union
}


// ================================================================
// PARSER RULES
// ================================================================

// ----- 程序入口 -----

program
    : ( moduleDecl
      | importStmt
      | exportStmt
      | definition
      | stmt
      )* EOF
    ;

moduleDecl
    : LBRACKET ID RBRACKET
    ;

definition
    : paragraphDef
    | classDef
    | interfaceDef
    | dataTypeDef
    | errorTypeDef
    | decoratorDef
    | ffiLoadLibrary
    | ffiFunctionDecl
    | ffiStructDef
    | ffiCallbackDef
    | ffiEnumDef
    | ffiVarArgsDecl
    ;

// ----- 段落定义（统一语法）-----

paragraphDef
    : BOOK_L ID BOOK_R K_SEGMENT ( LPAREN paramList? RPAREN )? COLON block K_END PERIOD?  // 《名称》段(参数)
    | K_SEGMENT ID ( LPAREN paramList? RPAREN | K_RECEIVE paramList? )? ( K_RETURN typeAnnotation? )? COLON block K_END PERIOD?  // 段 名称(参数) / 段 名称 接收 参数
    ;

// ----- 块规则（统一处理"结束"标记）-----
// 块只包含语句，由父规则负责匹配"结束"标记
// 块内容为语句或嵌套定义（段落/类等）
block
    : ( stmt | definition )*
    ;

// 块内容仅为语句
blockContent
    : stmt
    ;

// ----- 类定义（统一语法）-----

classDef
    : K_CLASS ID genericParams?
      ( K_INHERIT typeAnnotation ( COMMA typeAnnotation )* )?
      ( K_IMPLEMENTS typeAnnotation ( COMMA typeAnnotation )* )?
      COLON
      classMember*
      K_END PERIOD?
    ;

genericParams
    : LBRACKET ID ( COMMA ID )* RBRACKET
    ;

classMember
    : ( K_PUBLIC | K_PRIVATE | K_PROTECTED | K_STATIC )? ( methodDef | constructorDef | attributeDecl )
    | stmt
    ;

methodDef
    : K_SEGMENT ID ( LPAREN paramList? RPAREN | K_RECEIVE paramList? )? ( K_RETURN typeAnnotation? )?
      COLON block K_END PERIOD?
    ;

constructorDef
    : K_CONSTRUCTOR ( LPAREN paramList? RPAREN | K_RECEIVE paramList )? COLON block K_END PERIOD?
    ;

attributeDecl
    : K_ATTRIBUTE ID ( K_AS typeAnnotation )? ( K_EQUAL expr )? PERIOD?
    ;

// ----- 接口定义（统一语法）-----

interfaceDef
    : K_INTERFACE ID
      ( K_INHERIT typeAnnotation ( COMMA typeAnnotation )* )?
      COLON
      interfaceMember*
      K_END PERIOD?
    ;

interfaceMember
    : K_METHOD ID LPAREN paramList? RPAREN ( K_RETURN typeAnnotation )? PERIOD?
    ;

paramList
    : param ( COMMA param )*
    ;

param
    : identifier_like ( typeMark? typeAnnotation )? ( K_EQUAL expr )?
    ;

typeMark
    : COLON
    | K_TYPE
    ;

// ----- 语句 -----

dataTypeDef
    : BOOK_L ID BOOK_R K_DATA_TYPE COLON
      dataTypeField+
      K_END PERIOD?
    ;

dataTypeField
    : ID COLON typeAnnotation PERIOD?
    ;

errorTypeDef
    : BOOK_L ID BOOK_R K_ERROR_TYPE COLON
      dataTypeField+
      K_END PERIOD?
    ;

// ----- 导入/导出 -----

importStmt
    : K_FROM path K_IMPORT importList PERIOD?
    | K_IMPORT importList PERIOD?
    ;

exportStmt
    : K_EXPORT ( ID | BOOK_L ID BOOK_R ) PERIOD?
    ;

path
    : ID ( PATH_SEP ID )*
    | BOOK_L ID BOOK_R
    ;

importList
    : importItem ( COMMA importItem )*
    ;

importItem
    : BOOK_L ID BOOK_R
    | ID
    ;

// ----- C FFI（R77-A）-----
// 与 src/parser_stmt.py 的 FFI 子语法同口径：
//   加载库 "libxxx.so" 为 别名。
//   外部 段落/函数 光明名 为 "c_name" 接收 参数… 返回 类型 在 库别名。
//   外部 结构体/联合体 名称 { 字段：类型，… }
//   外部 枚举 名称 { 成员 = 值，… }
//   外部 回调 名称 接收 参数… 返回 类型。
//   外部 变长参数 名称 接收 参数…。

ffiLoadLibrary
    : K_LOAD_LIBRARY STRING K_AS ( ID | STRING ) PERIOD?
    ;

ffiFunctionDecl
    : K_EXTERN ( K_SEGMENT | K_METHOD ) ID
      ( K_AS STRING )?
      ( K_RECEIVE ffiParamList? )?
      ( K_RETURN typeAnnotation )?
      ( K_IN ffiLibraryAlias )?
      PERIOD?
    ;

ffiParamList
    : ffiParam ( ( COMMA | PAUSE ) ffiParam )*
    ;

ffiParam
    : identifier_like ( typeMark typeAnnotation | K_AS typeAnnotation )?
    ;

ffiLibraryAlias
    : ID ( DOT ID )*
    ;

ffiStructDef
    : K_EXTERN ( K_STRUCT | K_UNION ) ID
      LBRACE ffiFieldList? RBRACE
      PERIOD?
    ;

ffiFieldList
    : ffiField ( ( COMMA | PAUSE | PERIOD ) ffiField )* PERIOD?
    ;

ffiField
    : ID ( typeMark typeAnnotation | K_AS typeAnnotation )
    ;

ffiCallbackDef
    : K_EXTERN K_CALLBACK ID
      ( K_RECEIVE ffiParamList? )?
      ( K_RETURN typeAnnotation )?
      PERIOD?
    ;

ffiEnumDef
    : K_EXTERN K_ENUM ID
      LBRACE ffiEnumMemberList? RBRACE
      PERIOD?
    ;

ffiEnumMemberList
    : ffiEnumMember ( ( COMMA | PAUSE | PERIOD ) ffiEnumMember )* PERIOD?
    ;

ffiEnumMember
    : ID ( K_EQUAL expr | ASSIGN expr )?
    ;

ffiVarArgsDecl
    : K_EXTERN K_VARARGS ID
      ( K_RECEIVE ffiParamList? )?
      ( K_RETURN typeAnnotation )?
      ( K_IN ffiLibraryAlias )?
      PERIOD?
    ;

// ----- 语句 -----

stmt
    : varDecl
    | assignStmt
    | compoundAssignStmt
    | ifStmt
    | foreachStmt
    | whileStmt
    | returnStmt
    | breakStmt
    | continueStmt
    | tryStmt
    | throwStmt
    | matchStmt
    | withStmt
    | printStmt
    | exprStmt
    ;

varDecl
    : K_SET identifier_like K_AS expr PERIOD ( K_TYPE typeAnnotation )?  // 设 甲 为 三
    | K_SET identifier_like K_AS typeAnnotation K_EQUAL expr PERIOD?     // 设 甲 为 数 = 1（类型+值）
    | K_SET K_SELF ID K_AS expr PERIOD                               // 设 己名称 为 值（属性赋值）
    | K_SET LPAREN identifier_like ( COMMA identifier_like )* RPAREN K_AS expr PERIOD?  // 设（甲，乙）为 元组
    | K_DEFINE ID ( K_EQUAL expr PERIOD )?                           // 兼容旧语法
    ;

assignStmt
    : identifier_like ( ASSIGN | K_EQUAL | K_AS ) expr PERIOD?          // 甲 = 值 / 甲 等于 值 / 甲 为 值
    | K_SELF_PROP ( ASSIGN | K_EQUAL | K_AS ) expr PERIOD?          // R76-A：己属性 = 值（整体成词）
    | K_SELF ID ( ASSIGN | K_EQUAL | K_AS ) expr PERIOD?            // 己属性 = 值
    | primary DOT memberName ( ASSIGN | K_EQUAL | K_AS ) expr PERIOD?       // 对象.属性 = 值
    | primary K_DE memberName ( ASSIGN | K_EQUAL | K_AS ) expr PERIOD?      // 对象的属性 = 值
    | primary K_OF memberName ( ASSIGN | K_EQUAL | K_AS ) expr PERIOD?      // 对象之属性 = 值
    | primary LBRACKET expr RBRACKET ( ASSIGN | K_EQUAL | K_AS ) expr PERIOD?  // 甲[丁] = 值
    ;

// 复合赋值：甲 加上 1。
compoundAssignStmt
    : identifier_like compoundAssignOp expr PERIOD?
    ;

compoundAssignOp
    : K_PLUS_ASSIGN
    | K_MINUS_ASSIGN
    | K_MULTIPLY_ASSIGN
    | K_DIVIDE_ASSIGN
    | K_MOD_ASSIGN
    | K_POW_ASSIGN
    ;

ifStmt
    : K_IF expr K_THEN? COLON block K_END PERIOD?
      ( K_ELSE_IF expr K_THEN? COLON block K_END PERIOD? )*
      ( K_ELSE K_THEN? COLON block K_END PERIOD? )?
    | K_IF expr K_THEN stmt PERIOD?          // 单行内联：如果 条件 那么 语句（无冒号）
    ;

foreachStmt
    : K_FOREACH ID ( K_OF | K_AT ) expr ( K_TO expr ( K_STEP expr )? )?
      COLON block K_END PERIOD?
    ;

foreachVar
    : ID
    | ID K_OF ID
    | ID K_OF ID COMMA ID
    ;

whileStmt
    : K_WHILE expr
      ( COLON block K_END PERIOD? )?
    ;

returnStmt
    : K_RETURN expr? PERIOD?
    ;

breakStmt
    : K_BREAK PERIOD?
    ;

continueStmt
    : K_CONTINUE PERIOD?
    ;

tryStmt
    : K_TRY COLON block K_END PERIOD?
      K_CATCH ID COLON block K_END PERIOD?
    ;

throwStmt
    : K_THROW expr PERIOD?
    ;

matchStmt
    : K_MATCH expr COLON
      matchCase*
    ;

matchCase
    : K_CASE matchPattern (K_IF expr)? COLON block K_END PERIOD?
    ;

matchPattern
    : NUMBER                                       // 数字匹配
    | STRING                                       // 字符串匹配
    | K_TRUE                                       // 真匹配
    | K_FALSE                                      // 假匹配
    | K_NULL                                       // 空匹配
    | ID                                           // 变量绑定或枚举匹配
    | LBRACKET matchPatternList? RBRACKET          // 列表模式
    | ID K_OF matchPattern                         // 类型检查：类名 之 变量
    | UNDERSCORE                                   // 通配符
    ;

matchPatternList
    : matchPattern ( COMMA matchPattern )*
    ;

printStmt
    : ( K_PRINT | K_OUTPUT ) ( LPAREN exprList? RPAREN | expr )? PERIOD?
    ;

// ----- 上下文管理器 -----

withStmt
    : K_WITH expr ( K_AS ID )? COLON block K_END PERIOD?
    ;

// ----- 装饰器 -----

decoratorDef
    : AT ID K_DECORATE paragraphDef    // @段落名 标注 段落 ...
    ;

exprStmt
    : expr PERIOD
    ;

// ----- 表达式 -----

expr
    : pipelineExpr
    ;

pipelineExpr
    : andExpr ( ( PIPE | K_AND_WORD ) andExpr )*
    ;

andExpr
    : orExpr ( K_AND orExpr )*
    ;

orExpr
    : comparisonExpr ( K_OR comparisonExpr )*
    ;

comparisonExpr
    : additiveExpr ( K_TO additiveExpr ( K_STEP additiveExpr )? )   // 范围表达式：1至10 / 1到10步2
    | additiveExpr ( compOp additiveExpr )*
    ;

compOp
    : K_GE | K_LE | K_GT | K_LT | K_NE | K_EQUAL | K_IN
    | GE | LE | GT | LT | NE | EQ
    ;

// 范围表达式连接字（1至10）——供 visitor 探测（comparisonExpr 内使用）
comparisonKTo
    : K_TO
    ;

additiveExpr
    : multiplicativeExpr ( addOp multiplicativeExpr )*
    ;

addOp
    : K_PLUS | K_MINUS
    | PLUS | MINUS
    | K_PLUS_ASSIGN | K_MINUS_ASSIGN | K_MULTIPLY_ASSIGN
    | K_DIVIDE_ASSIGN | K_MOD_ASSIGN | K_POW_ASSIGN   // 复合赋值词兼作中缀加/减等（甲 加上 1）
    ;

multiplicativeExpr
    : unaryExpr ( multOp unaryExpr )*
    ;

multOp
    : K_MULTIPLY | K_DIVIDE | K_MOD | K_POW
    | MULTIPLY | DIVIDE | MODULO | POW
    ;

unaryExpr
    : ( K_NOT | NOT ) unaryExpr
    | ( MINUS | K_MINUS ) unaryExpr
    | postfixExpr
    ;

postfixExpr
    : primary
      ( BOOK_L ID BOOK_R LPAREN exprList? RPAREN     // 《段名》(参数)
      | LPAREN exprList? RPAREN                        // (参数)
      | DOT memberName                                 // 属性访问: 对象.属性
      | K_OF memberName                                // 之字结构: 对象之属性
      | K_DE memberName                                // 的字结构: 对象的属性
      | LBRACKET expr RBRACKET                         // 索引: 对象[索引]
      )*
    ;

// 成员名（允许构造 等 关键字作成员名：父.构造(...)）——R76-A
memberName
    : ID
    | K_CONSTRUCTOR
    ;

primary
    : NUMBER
    | STRING
    | K_TRUE
    | K_FALSE
    | K_NULL
    | UNDERSCORE                                          // 通配符作变量名（设 _ 为 ...）
    | K_SELF_PROP                                         // R76-A：己属性（整体成词，见 Lexer）
    | K_SELF                                              // 己（self引用）
    | K_SELF ID                                           // 己属性（无分隔的 self 属性访问：己姓名）
    | K_PARENT                                            // 父（父类引用，后跟成员访问符时=super()）
    | conditionalExpr                                     // 三元条件表达式：如果 条件 那么 值1 否则 值2
    | K_NEW ID ( LPAREN exprList? RPAREN | exprList )   // 新建 对象(参数) 或 新建 对象 参数
    | listComprehension                                   // 列表推导：[表达式 遍历 变量 之 列表]
    | lambdaExpr                                          // 匿名函数：接收 甲：返回 甲 乘 甲。
    | ID                                    // 变量
    | typeAsIdentifier                                     // 类型关键字用作标识符
    | LPAREN expr RPAREN                                   // 括号表达式
    | LBRACE dictContent RBRACE                            // 字典字面量/推导：{键: 值}
    | LBRACE RBRACE                                        // 空字典
    | LBRACKET RBRACKET                                   // 空列表
    | LBRACKET bracketContent RBRACKET                    // 列表/字典字面量或推导
    | BOOK_L ID BOOK_R                                 // 《段落名》
    // 动词调用（支持动词白名单中的动词）
    | K_FIRST LPAREN expr RPAREN                       // 首(列表)
    | K_LAST LPAREN expr RPAREN                        // 末(列表)
    | K_REST LPAREN expr RPAREN                        // 余(列表)
    | K_LENGTH LPAREN expr RPAREN                      // 长(列表)
    | K_SORT LPAREN expr RPAREN                        // 排序(列表)
    | K_REVERSE LPAREN expr RPAREN                     // 反转(列表)
    // K_SUM, K_MAX, K_MIN 移除，改为内置函数
    | K_UNIQUE LPAREN expr RPAREN                      // 去重(列表)
    | K_FILTER LPAREN expr COMMA expr RPAREN           // 筛选(列表, 条件)
    | K_MAP LPAREN expr COMMA expr RPAREN              // 映射(列表, 函数)
    // 字符串操作动词
    | K_TO_INT LPAREN expr RPAREN                      // 转整数(值)
    | K_TO_FLOAT LPAREN expr RPAREN                    // 转浮点(值)
    | K_TO_STR LPAREN expr RPAREN                      // 转字符串(值)
    | K_STR_LEN LPAREN expr RPAREN                     // 字符串长度(文本)
    | K_STR_SPLIT LPAREN expr COMMA expr RPAREN        // 分割字符串(文本, 分隔符)
    | K_STR_JOIN LPAREN expr COMMA expr RPAREN         // 连接字符串(列表, 分隔符)
    | K_STR_REPLACE LPAREN expr COMMA expr COMMA expr RPAREN  // 替换字符串(文本, 旧, 新)
    | K_STR_TRIM LPAREN expr RPAREN                    // 去除空白(文本)
    // 文件操作动词
    | K_READ_FILE LPAREN expr RPAREN                   // 读取文件(路径)
    | K_WRITE_FILE LPAREN expr COMMA expr RPAREN       // 写入文件(路径, 内容)
    | K_APPEND_FILE LPAREN expr COMMA expr RPAREN      // 追加文件(路径, 内容)
    | K_FILE_EXISTS LPAREN expr RPAREN                 // 文件存在(路径)
    | K_DIR_EXISTS LPAREN expr RPAREN                  // 目录存在(路径)
    | K_MAKE_DIR LPAREN expr RPAREN                    // 创建目录(路径)
    | K_REMOVE_FILE LPAREN expr RPAREN                 // 删除文件(路径)
    | K_REMOVE_DIR LPAREN expr RPAREN                  // 删除目录(路径)
    // 系统操作动词
    | K_ENV LPAREN expr RPAREN                         // 环境变量(名称)
    | K_SET_ENV LPAREN expr COMMA expr RPAREN          // 设置环境变量(名称, 值)
    | K_ARGS LPAREN RPAREN                             // 参数列表()
    | K_EXIT LPAREN expr? RPAREN                       // 退出程序(状态码)
    | K_CWD LPAREN RPAREN                              // 当前目录()
    | K_CD LPAREN expr RPAREN                          // 切换目录(路径)
    | K_EXEC LPAREN expr RPAREN                        // 执行命令(命令)
    // I/O操作动词
    | K_INPUT LPAREN expr? RPAREN                      // 输入(提示)
    | K_READ LPAREN expr? RPAREN                       // 读取(提示)
    ;

implicitCall
    : implicitArg ( COMMA? implicitArg )*
    ;

implicitArg
    : NUMBER | STRING | K_TRUE | K_FALSE | K_NULL | ID | K_SELF
    ;

dictLiteral
    : dictEntry ( COMMA dictEntry )*
    ;

dictEntry
    : expr COLON expr
    ;

// ----- 列表推导 -----

listComprehension
    : LBRACKET expr K_FOREACH identifier_like ( K_OF | K_AT ) expr ( K_IF expr )? RBRACKET
    ;

identifier_like
    : ID
    | UNDERSCORE
    | T_NUMBER | T_INT | T_FLOAT | T_STRING | T_LIST | T_DICT | T_SET | T_BOOL | T_ANY
    | K_TRUE | K_FALSE | K_NULL
    ;

// 类型关键字用作标识符（如变量名"数"）
typeAsIdentifier
    : T_NUMBER | T_INT | T_FLOAT | T_STRING | T_LIST | T_DICT | T_SET | T_BOOL | T_ANY
    ;

// ----- 匿名函数 -----

lambdaExpr
    : K_RECEIVE paramList? COLON ( K_RETURN expr | expr ) PERIOD?
    ;

// ----- 字典推导 -----

dictComprehension
    : expr COLON expr K_FOREACH identifier_like ( K_OF | K_AT ) expr ( K_IF expr )?
    ;

// ----- 方括号/花括号内容（消除歧义）-----

bracketContent
    : dictComprehension COMMA?                                        // 字典推导：键: 值 遍历 变量 之 列表
    | dictLiteral COMMA?                                              // 字典字面量：键: 值, ...
    | expr K_FOREACH identifier_like ( K_OF | K_AT ) expr ( K_IF expr )?  // 列表推导
    | exprList COMMA?                                                 // 列表字面量（允许尾逗号，跨行书写）
    | COMMA?
    ;

dictContent
    : dictComprehension
    | dictLiteral
    ;


typeAnnotation
    : builtinType
    | ID
    ;

builtinType
    : T_NUMBER | T_INT | T_FLOAT
    | T_STRING | T_LIST | T_DICT | T_SET
    | T_BOOL | K_NULL | T_ANY
    ;

exprList
    : expr ( COMMA expr )*
    ;

// ----- 三元条件表达式 -----

conditionalExpr
    : K_IF expr K_THEN expr ( K_ELSE expr )?
    ;