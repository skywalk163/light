/*
 * 光明 (Light) 运行时库 - 类型版 (v3)
 * 
 * 基于 LightValue 结构体，所有值携带类型标记。
 * 算术运算直接在原生类型上操作，避免 atoi/itoa 转换。
 * 
 * 类型系统：
 *   0 = NULL, 1 = INT, 2 = FLOAT, 3 = STRING, 4 = LIST, 5 = BOOL
 * 
 * 所有 LightValue 参数通过指针传递，避免 C/LLVM 结构体布局 ABI 不兼容。
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include <math.h>
#include <sys/stat.h>
#include <ctype.h>
#include <errno.h>

#ifdef _WIN32
/* WSAPoll 与 Schannel 需要 Vista+ 的 SDK 表面；必须在 winsock2.h 之前定死 */
#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0601
#endif
/* winsock2.h must be included BEFORE windows.h to avoid redefinition */
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <io.h>
#include <direct.h>
#pragma comment(lib, "ws2_32.lib")
#define F_OK 0
#define access _access
#else
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/select.h>
#include <netdb.h>
/* dv_socket_set_nonblocking 用 fcntl/F_GETFL/F_SETFL/O_NONBLOCK。
   glibc 会经别的头间接带出来，FreeBSD/clang 不会，缺这行在 FreeBSD 上是
   4 个 error（use of undeclared identifier），整条 clang 腿全崩。 */
#include <fcntl.h>
#endif

/* ================================================================
 * 类型定义
 * ================================================================ */

typedef struct LightValue LightValue;
/* DuanValue is an alias for LightValue (legacy interface system) */
typedef LightValue DuanValue;
/* DuanMethodFunc: function pointer type for interface method dispatch */
typedef void (*DuanMethodFunc)(DuanValue* result, DuanValue* obj,
                               DuanValue* args, int num_args);
struct LightValue {
    int type;          /* 0=NULL 1=INT 2=FLOAT 3=STR 4=LIST 5=BOOL 6=OBJ 7=DICT 8=REF */
    int64_t i64;       /* INT */
    double f64;        /* FLOAT */
    char* str;         /* STR / REF (type=8 时存储 LightValue* 指针) */
    int boolean;       /* BOOL */
    /* LIST 类型专用字段 (type=4) */
    int list_size;     /* 当前元素数量 */
    int list_capacity; /* 分配的数组容量 */
    struct LightValue** list_data; /* 元素数组指针 */
    /* DICT 类型专用字段 (type=7) - 复用 list_data/list_size/list_capacity
       list_data 存储键值对: [key1, val1, key2, val2, ...]
       list_size = 键值对数量
       list_capacity = 已分配容量（对数，list_data 有 2*list_capacity 个槽位） */
};

/* type=8 REF: 引用类型，str 字段存储被引用的 LightValue* 指针
   用于 dv_dict_get 返回对字典内部值的引用，使原地修改（如列表追加）能传播回字典 */

/* 元组类型标记（type=23）：不可变序列，复用 list_data/list_size/list_capacity */
#define LV_TYPE_TUPLE 23

/* ================================================================
 * 前向声明（避免隐式函数声明）
 * ================================================================ */

void dv_clone(LightValue* result, LightValue* v);
void dv_class_get_member(LightValue* result, LightValue* obj, const char* field_name);
void dv_value_to_string(LightValue* result, LightValue* v);
int dv_is_object(LightValue* v);
/* 接口系统前向声明（Level 7） */
int dv_register_interface(const char* name);
int dv_register_interface_method(const char* interface_name, const char* method_name, const char* signature);
int dv_register_class_implements(const char* class_name, const char* interface_name);
int dv_class_implements_interface(const char* class_name, const char* interface_name);
int dv_call_interface_method(DuanValue* result, DuanValue* obj,
                              const char* interface_name, const char* method_name,
                              DuanValue* args, int num_args);

/* ================================================================
 * 内部工具
 * ================================================================ */

/* 跟随 REF 链，返回实际值指针（用于原地修改操作） */
static LightValue* dv_deref(LightValue* v) {
    while (v && v->type == 8 && v->str) {
        v = (LightValue*)v->str;
    }
    return v;
}

static char* dv_strdup(const char* s) {
    if (!s) return NULL;
    size_t len = strlen(s);
    char* d = (char*)malloc(len + 1);
    if (d) memcpy(d, s, len + 1);
    return d;
}

/* ================================================================
 * UTF-8 辅助（码位 / 字符自码位 / 字符感知索引 共用）
 * 原生腿没有一等 bytes 类型，字节级 UTF-8 解码必须在 C 侧完成。
 * ================================================================ */

/* 以 p 开头的 UTF-8 字符占用字节数（1..4）；非法首字节按 1 处理。 */
static size_t dv_utf8_seq_len(const unsigned char* p) {
    unsigned char c = p[0];
    if (c < 0x80) return 1;
    if ((c & 0xE0) == 0xC0) return 2;
    if ((c & 0xF0) == 0xE0) return 3;
    if ((c & 0xF8) == 0xF0) return 4;
    return 1;
}

/* 从 s（len 字节）解码第 1 个码点；*consumed 回写占用字节数。
   空串 -> -1（consumed=0）；非法/截断序列 -> U+FFFD（consumed=1）。 */
static int64_t dv_utf8_decode_cp(const unsigned char* s, size_t len, size_t* consumed) {
    if (len == 0) { *consumed = 0; return -1; }
    unsigned char c = s[0];
    int64_t cp;
    size_t need;
    if (c < 0x80) { *consumed = 1; return c; }
    else if ((c & 0xE0) == 0xC0) { cp = c & 0x1F; need = 2; }
    else if ((c & 0xF0) == 0xE0) { cp = c & 0x0F; need = 3; }
    else if ((c & 0xF8) == 0xF0) { cp = c & 0x07; need = 4; }
    else { *consumed = 1; return 0xFFFD; }
    if (len < need) { *consumed = 1; return 0xFFFD; }
    for (size_t i = 1; i < need; i++) {
        if ((s[i] & 0xC0) != 0x80) { *consumed = 1; return 0xFFFD; }
        cp = (cp << 6) | (s[i] & 0x3F);
    }
    *consumed = need;
    return cp;
}

/* 字符串的 Unicode 字符数（非字节数）。 */
static size_t dv_utf8_char_count(const char* s) {
    if (!s) return 0;
    const unsigned char* p = (const unsigned char*)s;
    size_t len = strlen(s);
    size_t n = 0, off = 0;
    while (off < len) {
        off += dv_utf8_seq_len(p + off);
        n++;
    }
    return n;
}

/* 字符串中第 idx 个字符（按 Unicode，idx>=0）的字节偏移。 */
static size_t dv_utf8_char_offset(const char* s, size_t idx) {
    const unsigned char* p = (const unsigned char*)s;
    size_t len = strlen(s);
    size_t off = 0;
    for (size_t i = 0; i < idx && off < len; i++) {
        off += dv_utf8_seq_len(p + off);
    }
    return off;
}

/* 码位(字符)：取字符串首字符的码点（等价 Python ord）。空/非串 -> 0。 */
void dv_ord(LightValue* result, LightValue* str_val) {
    result->type = 1; result->i64 = 0; result->f64 = 0.0; result->str = NULL; result->boolean = 0;
    if (!str_val || str_val->type != 3 || !str_val->str) return;
    const unsigned char* s = (const unsigned char*)str_val->str;
    size_t len = strlen((const char*)s);
    size_t consumed;
    int64_t cp = dv_utf8_decode_cp(s, len, &consumed);
    if (cp < 0) return;
    result->i64 = cp;
}

/* 字符自码位(n)：把码点编码成 UTF-8 字符串（等价 Python chr）。 */
void dv_chr(LightValue* result, LightValue* int_val) {
    result->type = 3; result->i64 = 0; result->f64 = 0.0; result->str = NULL; result->boolean = 0;
    int64_t cp = 0;
    if (int_val) {
        if (int_val->type == 1) cp = int_val->i64;
        else if (int_val->type == 3) cp = strtoll(int_val->str ? int_val->str : "0", NULL, 10);
    }
    if (cp < 0) cp = 0;
    unsigned char buf[5];
    size_t n;
    if (cp < 0x80) { buf[0] = (unsigned char)cp; n = 1; }
    else if (cp < 0x800) { buf[0] = 0xC0 | (cp >> 6); buf[1] = 0x80 | (cp & 0x3F); n = 2; }
    else if (cp < 0x10000) { buf[0] = 0xE0 | (cp >> 12); buf[1] = 0x80 | ((cp >> 6) & 0x3F); buf[2] = 0x80 | (cp & 0x3F); n = 3; }
    else { buf[0] = 0xF0 | (cp >> 18); buf[1] = 0x80 | ((cp >> 12) & 0x3F); buf[2] = 0x80 | ((cp >> 6) & 0x3F); buf[3] = 0x80 | (cp & 0x3F); n = 4; }
    buf[n] = '\0';
    result->str = dv_strdup((const char*)buf);
}

/* 十六进制(n)：码点 -> 大写十六进制字符串，无 0x 前缀（等价 format(n,'X')）。 */
void dv_hex(LightValue* result, LightValue* int_val) {
    result->type = 3; result->i64 = 0; result->f64 = 0.0; result->str = NULL; result->boolean = 0;
    int64_t v = 0;
    if (int_val) {
        if (int_val->type == 1) v = int_val->i64;
        else if (int_val->type == 3) v = strtoll(int_val->str ? int_val->str : "0", NULL, 10);
    }
    unsigned long long u = (unsigned long long)v;
    static const char HEXD[] = "0123456789ABCDEF";
    char buf[32];
    if (u == 0) {
        buf[0] = '0'; buf[1] = '\0';
    } else {
        int p = 31;
        /* buf 为 char[32]（下标 0..31），越界写 buf[32] 是 UB；
         * 真正的终止由下方 buf[digits]='\0' 完成，此处无需预置终止符。 */
        while (u > 0 && p >= 0) {
            buf[p] = HEXD[u & 0xF];
            u >>= 4;
            p--;
        }
        size_t start = (size_t)(p + 1);
        size_t digits = 32 - start;
        for (size_t i = 0; i < digits; i++) buf[i] = buf[start + i];
        buf[digits] = '\0';
    }
    result->str = dv_strdup(buf);
}

/* ================================================================
 * 值构造器 - 写结果到 result 指针，避免返回 struct 值
 * ================================================================ */

void dv_null(LightValue* result) {
    result->type = 0;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = NULL;
    result->boolean = 0;
}

int dv_is_null(LightValue* v) {
    return v && v->type == 0;
}

/* null 合并操作符：如果 v 是 null，返回 default_val，否则返回 v */
void dv_null_coalesce(LightValue* result, LightValue* v, LightValue* default_val) {
    if (v && v->type != 0) {
        dv_clone(result, v);
    } else {
        dv_clone(result, default_val);
    }
}

/* 安全获取属性：如果 obj 为 null，返回 null；否则返回 obj.属性 */
void dv_safe_get(LightValue* result, LightValue* obj, LightValue* attr_name) {
    if (!obj || obj->type == 0) {
        dv_null(result);
        return;
    }
    if (obj->type == 6) {  /* OBJ 类型 */
        dv_class_get_member(result, obj, attr_name->str);
    } else {
        dv_null(result);
    }
}

void dv_int(LightValue* result, int64_t x) {
    result->type = 1;
    result->i64 = x;
    result->f64 = 0.0;
    result->str = NULL;
    result->boolean = 0;
}

void dv_float(LightValue* result, double x) {
    result->type = 2;
    result->i64 = 0;
    result->f64 = x;
    result->str = NULL;
    result->boolean = 0;
}

void dv_str(LightValue* result, const char* s) {
    result->type = 3;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = dv_strdup(s ? s : "");
    result->boolean = 0;
}

void dv_bool(LightValue* result, int b) {
    result->type = 5;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = NULL;
    result->boolean = b ? 1 : 0;
}

/* ================================================================
 * 值销毁 / 复制
 * ================================================================ */

void dv_free(LightValue* v) {
    if (!v) return;
    if (v->type == 8) {
        /* REF: 不释放引用目标，仅清空指针 */
        v->str = NULL;
        v->type = 0;
        return;
    }
    if (v->type == 3 && v->str) {
        free(v->str);
        v->str = NULL;
    } else if (v->type == 4 && v->list_data) {
        for (int i = 0; i < v->list_size; i++) {
            if (v->list_data[i]) {
                dv_free(v->list_data[i]);
                free(v->list_data[i]);
            }
        }
        free(v->list_data);
        v->list_data = NULL;
        v->list_size = 0;
        v->list_capacity = 0;
    } else if (v->type == 7 && v->list_data) {
        /* DICT: list_data 有 2*list_size 个条目 (key, val, key, val, ...) */
        for (int i = 0; i < 2 * v->list_size; i++) {
            if (v->list_data[i]) {
                dv_free(v->list_data[i]);
                free(v->list_data[i]);
            }
        }
        free(v->list_data);
        v->list_data = NULL;
        v->list_size = 0;
        v->list_capacity = 0;
    }
}

void dv_clone(LightValue* result, LightValue* v) {
    if (v->type == 8) {
        /* REF: 复制引用（浅拷贝，指向同一目标） */
        result->type = 8;
        result->str = v->str;
        result->i64 = 0;
        result->f64 = 0.0;
        result->boolean = 0;
        result->list_size = 0;
        result->list_capacity = 0;
        result->list_data = NULL;
        return;
    }
    *result = *v;
    if (v->type == 3 && v->str) {
        result->str = dv_strdup(v->str);
    } else if (v->type == 4) {
        /* 复制列表数据 */
        result->list_data = NULL;
        result->list_size = 0;
        result->list_capacity = 0;
        if (v->list_size > 0 && v->list_data) {
            result->list_capacity = v->list_capacity > 0 ? v->list_capacity : v->list_size;
            result->list_data = (struct LightValue**)malloc(result->list_capacity * sizeof(LightValue*));
            for (int i = 0; i < v->list_size; i++) {
                if (v->list_data[i]) {
                    result->list_data[i] = (LightValue*)malloc(sizeof(LightValue));
                    dv_clone(result->list_data[i], v->list_data[i]);
                } else {
                    result->list_data[i] = NULL;
                }
            }
            result->list_size = v->list_size;
        }
    } else if (v->type == 7) {
        /* DICT: 浅拷贝 - 共享 list_data 指针，使字典值（如列表）可被原地修改 */
        /* list_data 保持原指针，list_size/list_capacity 保持原值 */
    }
}

/* ================================================================
 * 类型转换 - 取 LightValue* 避免 struct 传参 ABI 问题
 * ================================================================ */

int64_t dv_to_i64(LightValue* v) {
    v = dv_deref(v);
    switch (v->type) {
        case 1: return v->i64;
        case 2: return (int64_t)v->f64;
        case 5: return v->boolean ? 1 : 0;
        case 3: return v->str ? atoll(v->str) : 0;
        default: return 0;
    }
}

double dv_to_f64(LightValue* v) {
    v = dv_deref(v);
    switch (v->type) {
        case 1: return (double)v->i64;
        case 2: return v->f64;
        case 5: return v->boolean ? 1.0 : 0.0;
        case 3: return v->str ? atof(v->str) : 0.0;
        default: return 0.0;
    }
}

const char* dv_to_str(LightValue* v) {
    v = dv_deref(v);
    switch (v->type) {
        case 3: return v->str ? v->str : "";
        default: return "";
    }
}

int dv_to_bool(LightValue* v) {
    v = dv_deref(v);
    switch (v->type) {
        case 0: return 0;
        case 1: return v->i64 != 0;
        case 2: return v->f64 != 0.0;
        case 3: return v->str && v->str[0] != '\0';
        case 5: return v->boolean;
        case 4: return 1;  /* 非空列表为真 */
        case 7: return 1;  /* 非空字典为真 */
        default: return 0;
    }
}

char* dv_to_string(LightValue* v) {
    v = dv_deref(v);
    /* 转换为可读字符串形式 */
    char buf[128];
    switch (v->type) {
        case 0: return dv_strdup("空");
        case 1: snprintf(buf, sizeof(buf), "%lld", (long long)v->i64); return dv_strdup(buf);
        case 2: snprintf(buf, sizeof(buf), "%g", v->f64); return dv_strdup(buf);
        case 3: return dv_strdup(v->str ? v->str : "");
        case 5: return dv_strdup(v->boolean ? "真" : "假");
        case 4: return dv_strdup(v->str ? v->str : "[]");
        case 7: return dv_strdup("dict");  /* DICT 简化表示 */
        default: return dv_strdup("");
    }
}

/* ================================================================
 * 算术运算（类型提升：int + float → float）
 * ================================================================ */

static int dv_promote(LightValue* a, LightValue* b) {
    return (a->type == 2 || b->type == 2) ? 2 : 1;
}

static int dv_is_object_str(const char* s) {
    if (!s) return 0;
    return strncmp(s, "obj:", 4) == 0;
}

void dv_add(LightValue* result, LightValue* a, LightValue* b);
void dv_sub(LightValue* result, LightValue* a, LightValue* b);
void dv_mul(LightValue* result, LightValue* a, LightValue* b);
void dv_div(LightValue* result, LightValue* a, LightValue* b);

static void dv_add_default(LightValue* result, LightValue* a, LightValue* b) {
    /* 特殊：字符串拼接 */
    if (a->type == 3 || b->type == 3) {
        char* sa = dv_to_string(a);
        char* sb = dv_to_string(b);
        char* r = (char*)malloc(strlen(sa) + strlen(sb) + 1);
        if (r) { sprintf(r, "%s%s", sa, sb); }
        free(sa);
        free(sb);
        if (r) {
            result->type = 3;
            result->i64 = 0;
            result->f64 = 0.0;
            result->str = dv_strdup(r);
            result->boolean = 0;
        } else {
            result->type = 3;
            result->i64 = 0;
            result->f64 = 0.0;
            result->str = dv_strdup("");
            result->boolean = 0;
        }
        free(r);
        return;
    }
    if (dv_promote(a, b) == 2) {
        result->type = 2;
        result->i64 = 0;
        result->f64 = dv_to_f64(a) + dv_to_f64(b);
        result->str = NULL;
        result->boolean = 0;
        return;
    }
    result->type = 1;
    result->i64 = dv_to_i64(a) + dv_to_i64(b);
    result->f64 = 0.0;
    result->str = NULL;
    result->boolean = 0;
}

static void dv_sub_default(LightValue* result, LightValue* a, LightValue* b) {
    if (dv_promote(a, b) == 2) {
        result->type = 2;
        result->i64 = 0;
        result->f64 = dv_to_f64(a) - dv_to_f64(b);
        result->str = NULL;
        result->boolean = 0;
        return;
    }
    result->type = 1;
    result->i64 = dv_to_i64(a) - dv_to_i64(b);
    result->f64 = 0.0;
    result->str = NULL;
    result->boolean = 0;
}

static void dv_mul_default(LightValue* result, LightValue* a, LightValue* b) {
    if (dv_promote(a, b) == 2) {
        result->type = 2;
        result->i64 = 0;
        result->f64 = dv_to_f64(a) * dv_to_f64(b);
        result->str = NULL;
        result->boolean = 0;
        return;
    }
    result->type = 1;
    result->i64 = dv_to_i64(a) * dv_to_i64(b);
    result->f64 = 0.0;
    result->str = NULL;
    result->boolean = 0;
}

static void dv_div_default(LightValue* result, LightValue* a, LightValue* b) {
    if (dv_promote(a, b) == 2) {
        double denom = dv_to_f64(b);
        if (denom == 0.0) {
            dv_null(result);
            return;
        }
        result->type = 2;
        result->i64 = 0;
        result->f64 = dv_to_f64(a) / denom;
        result->str = NULL;
        result->boolean = 0;
        return;
    }
    int64_t denom = dv_to_i64(b);
    if (denom == 0) {
        dv_null(result);
        return;
    }
    result->type = 1;
    result->i64 = dv_to_i64(a) / denom;
    result->f64 = 0.0;
    result->str = NULL;
    result->boolean = 0;
}

/* ================================================================
 * 数学函数
 * ================================================================ */

void dv_sin(LightValue* result, LightValue* a) {
    double x = dv_to_f64(a);
    result->type = 2;
    result->i64 = 0;
    result->f64 = sin(x);
    result->str = NULL;
    result->boolean = 0;
}

void dv_cos(LightValue* result, LightValue* a) {
    double x = dv_to_f64(a);
    result->type = 2;
    result->i64 = 0;
    result->f64 = cos(x);
    result->str = NULL;
    result->boolean = 0;
}

void dv_sqrt(LightValue* result, LightValue* a) {
    double x = dv_to_f64(a);
    if (x < 0) {
        dv_null(result);
        return;
    }
    result->type = 2;
    result->i64 = 0;
    result->f64 = sqrt(x);
    result->str = NULL;
    result->boolean = 0;
}

void dv_abs(LightValue* result, LightValue* a) {
    if (a->type == 1) {
        int64_t x = dv_to_i64(a);
        result->type = 1;
        result->i64 = x < 0 ? -x : x;
        result->f64 = 0.0;
        result->str = NULL;
        result->boolean = 0;
    } else {
        double x = dv_to_f64(a);
        result->type = 2;
        result->i64 = 0;
        result->f64 = fabs(x);
        result->str = NULL;
        result->boolean = 0;
    }
}

void dv_pow(LightValue* result, LightValue* a, LightValue* b) {
    double x = dv_to_f64(a);
    double y = dv_to_f64(b);
    result->type = 2;
    result->i64 = 0;
    result->f64 = pow(x, y);
    result->str = NULL;
    result->boolean = 0;
}

void dv_floor(LightValue* result, LightValue* a) {
    if (a->type == 1) {
        dv_clone(result, a);
        return;
    }
    double x = dv_to_f64(a);
    result->type = 1;
    result->i64 = (int64_t)floor(x);
    result->f64 = 0.0;
    result->str = NULL;
    result->boolean = 0;
}

void dv_ceil(LightValue* result, LightValue* a) {
    if (a->type == 1) {
        dv_clone(result, a);
        return;
    }
    double x = dv_to_f64(a);
    result->type = 1;
    result->i64 = (int64_t)ceil(x);
    result->f64 = 0.0;
    result->str = NULL;
    result->boolean = 0;
}

void dv_mod(LightValue* result, LightValue* a, LightValue* b) {
    if (a->type == 1 && b->type == 1) {
        int64_t x = dv_to_i64(a);
        int64_t y = dv_to_i64(b);
        if (y == 0) {
            dv_null(result);
            return;
        }
        result->type = 1;
        result->i64 = x % y;
        result->f64 = 0.0;
        result->str = NULL;
        result->boolean = 0;
    } else {
        double x = dv_to_f64(a);
        double y = dv_to_f64(b);
        if (y == 0.0) {
            dv_null(result);
            return;
        }
        result->type = 2;
        result->i64 = 0;
        result->f64 = fmod(x, y);
        result->str = NULL;
        result->boolean = 0;
    }
}

/* ----------------------------------------------------------------
 * 数学扩展（第三批移植）
 * ---------------------------------------------------------------- */

void dv_tan(LightValue* result, LightValue* a) {
    double x = dv_to_f64(a);
    result->type = 2;
    result->i64 = 0;
    result->f64 = tan(x);
    result->str = NULL;
    result->boolean = 0;
}

void dv_asin(LightValue* result, LightValue* a) {
    double x = dv_to_f64(a);
    result->type = 2;
    result->i64 = 0;
    result->f64 = asin(x);
    result->str = NULL;
    result->boolean = 0;
}

void dv_acos(LightValue* result, LightValue* a) {
    double x = dv_to_f64(a);
    result->type = 2;
    result->i64 = 0;
    result->f64 = acos(x);
    result->str = NULL;
    result->boolean = 0;
}

void dv_atan(LightValue* result, LightValue* a) {
    double x = dv_to_f64(a);
    result->type = 2;
    result->i64 = 0;
    result->f64 = atan(x);
    result->str = NULL;
    result->boolean = 0;
}

void dv_atan2(LightValue* result, LightValue* a, LightValue* b) {
    double x = dv_to_f64(a);
    double y = dv_to_f64(b);
    result->type = 2;
    result->i64 = 0;
    result->f64 = atan2(x, y);
    result->str = NULL;
    result->boolean = 0;
}

void dv_log(LightValue* result, LightValue* a) {
    double x = dv_to_f64(a);
    result->type = 2;
    result->i64 = 0;
    result->f64 = (x > 0) ? log(x) : 0.0;
    result->str = NULL;
    result->boolean = 0;
}

void dv_log2(LightValue* result, LightValue* a) {
    double x = dv_to_f64(a);
    result->type = 2;
    result->i64 = 0;
    result->f64 = (x > 0) ? log2(x) : 0.0;
    result->str = NULL;
    result->boolean = 0;
}

void dv_log10(LightValue* result, LightValue* a) {
    double x = dv_to_f64(a);
    result->type = 2;
    result->i64 = 0;
    result->f64 = (x > 0) ? log10(x) : 0.0;
    result->str = NULL;
    result->boolean = 0;
}

void dv_exp(LightValue* result, LightValue* a) {
    double x = dv_to_f64(a);
    result->type = 2;
    result->i64 = 0;
    result->f64 = exp(x);
    result->str = NULL;
    result->boolean = 0;
}

void dv_round(LightValue* result, LightValue* a) {
    if (a->type == 1) {
        dv_clone(result, a);
        return;
    }
    double x = dv_to_f64(a);
    result->type = 1;
    result->i64 = (int64_t)round(x);
    result->f64 = 0.0;
    result->str = NULL;
    result->boolean = 0;
}

void dv_trunc(LightValue* result, LightValue* a) {
    if (a->type == 1) {
        dv_clone(result, a);
        return;
    }
    double x = dv_to_f64(a);
    result->type = 1;
    result->i64 = (int64_t)trunc(x);
    result->f64 = 0.0;
    result->str = NULL;
    result->boolean = 0;
}

void dv_sign(LightValue* result, LightValue* a) {
    if (a->type == 1) {
        int64_t x = dv_to_i64(a);
        int64_t s = (x > 0) - (x < 0);
        result->type = 1;
        result->i64 = s;
        result->f64 = 0.0;
        result->str = NULL;
        result->boolean = 0;
        return;
    }
    double x = dv_to_f64(a);
    double s = (x > 0.0) - (x < 0.0);
    result->type = 2;
    result->i64 = 0;
    result->f64 = s;
    result->str = NULL;
    result->boolean = 0;
}

void dv_hypot(LightValue* result, LightValue* a, LightValue* b) {
    double x = dv_to_f64(a);
    double y = dv_to_f64(b);
    result->type = 2;
    result->i64 = 0;
    result->f64 = hypot(x, y);
    result->str = NULL;
    result->boolean = 0;
}

void dv_degrees(LightValue* result, LightValue* a) {
    double x = dv_to_f64(a);
    result->type = 2;
    result->i64 = 0;
    result->f64 = x * (180.0 / 3.14159265358979323846);
    result->str = NULL;
    result->boolean = 0;
}

void dv_radians(LightValue* result, LightValue* a) {
    double x = dv_to_f64(a);
    result->type = 2;
    result->i64 = 0;
    result->f64 = x * (3.14159265358979323846 / 180.0);
    result->str = NULL;
    result->boolean = 0;
}

void dv_min(LightValue* result, LightValue* a, LightValue* b) {
    if (dv_promote(a, b) == 2) {
        double x = dv_to_f64(a);
        double y = dv_to_f64(b);
        result->type = 2;
        result->i64 = 0;
        result->f64 = (x < y) ? x : y;
        result->str = NULL;
        result->boolean = 0;
        return;
    }
    int64_t x = dv_to_i64(a);
    int64_t y = dv_to_i64(b);
    result->type = 1;
    result->i64 = (x < y) ? x : y;
    result->f64 = 0.0;
    result->str = NULL;
    result->boolean = 0;
}

void dv_max(LightValue* result, LightValue* a, LightValue* b) {
    if (dv_promote(a, b) == 2) {
        double x = dv_to_f64(a);
        double y = dv_to_f64(b);
        result->type = 2;
        result->i64 = 0;
        result->f64 = (x > y) ? x : y;
        result->str = NULL;
        result->boolean = 0;
        return;
    }
    int64_t x = dv_to_i64(a);
    int64_t y = dv_to_i64(b);
    result->type = 1;
    result->i64 = (x > y) ? x : y;
    result->f64 = 0.0;
    result->str = NULL;
    result->boolean = 0;
}

/* 辗转相除法求最大公约数 */
static int64_t _i64_gcd(int64_t a, int64_t b) {
    if (a < 0) a = -a;
    if (b < 0) b = -b;
    while (b != 0) {
        int64_t t = a % b;
        a = b;
        b = t;
    }
    return a;
}

void dv_gcd(LightValue* result, LightValue* a, LightValue* b) {
    int64_t x = dv_to_i64(a);
    int64_t y = dv_to_i64(b);
    result->type = 1;
    result->i64 = _i64_gcd(x, y);
    result->f64 = 0.0;
    result->str = NULL;
    result->boolean = 0;
}

void dv_lcm(LightValue* result, LightValue* a, LightValue* b) {
    int64_t x = dv_to_i64(a);
    int64_t y = dv_to_i64(b);
    int64_t g = _i64_gcd(x, y);
    int64_t m = (g == 0) ? 0 : (x / g) * y;
    if (m < 0) m = -m;
    result->type = 1;
    result->i64 = m;
    result->f64 = 0.0;
    result->str = NULL;
    result->boolean = 0;
}

/* ================================================================
 * 比较运算
 * ================================================================ */

int dv_eq(LightValue* a, LightValue* b) {
    /* 类型感知的相等判定：
     *  - 任一为 空(null, type 0)：仅当两者皆 空 时相等，否则不等
     *    （修复：原实现对非字符串/非浮点对一律走 dv_to_i64 比较，
     *     导致 字典/对象 与 空 都转为 i64=0 而误判相等，
     *     使得 `事件 != 空` 类判断恒为假，SSE 原生 0 事件根因之一）
     *  - 同为字符串(type 3)：按内容比较
     *  - 数值类型(int=1 / float=2，含跨数值类型如 1 == 1.0)：按数值比较
     *  - 同为非数值类型：按 i64 标识比较（bool/obj 等）
     *  - 类型不同：不等
     */
    a = dv_deref(a);
    b = dv_deref(b);
    if (a->type == 0 || b->type == 0) {
        return (a->type == 0 && b->type == 0) ? 1 : 0;
    }
    if (a->type == 3 && b->type == 3) {
        return (a->str && b->str && strcmp(a->str, b->str) == 0) ||
               (!a->str && !b->str);
    }
    if ((a->type == 1 || a->type == 2) && (b->type == 1 || b->type == 2)) {
        return dv_to_f64(a) == dv_to_f64(b);
    }
    if (a->type == b->type) {
        return dv_to_i64(a) == dv_to_i64(b);
    }
    return 0;
}

int dv_cmp(LightValue* a, LightValue* b) {
    /* 返回 -1, 0, 1 用于 <, ==, > */
    if (a->type == 3 && b->type == 3) {
        if (!a->str && !b->str) return 0;
        if (!a->str) return -1;
        if (!b->str) return 1;
        return strcmp(a->str, b->str);
    }
    double fa = dv_to_f64(a);
    double fb = dv_to_f64(b);
    if (fa < fb) return -1;
    if (fa > fb) return 1;
    return 0;
}

int dv_lt(LightValue* a, LightValue* b) { return dv_cmp(a, b) < 0; }
int dv_gt(LightValue* a, LightValue* b) { return dv_cmp(a, b) > 0; }
int dv_le(LightValue* a, LightValue* b) { return dv_cmp(a, b) <= 0; }
int dv_ge(LightValue* a, LightValue* b) { return dv_cmp(a, b) >= 0; }

/* ================================================================
 * I/O 函数
 * ================================================================ */

void dv_print(LightValue* v) {
    char* s = dv_to_string(v);
    if (s) printf("%s", s);
    free(s);
}

void dv_println(LightValue* v) {
    char* s = dv_to_string(v);
    if (s) printf("%s\n", s);
    free(s);
}

void dv_print_int(LightValue* result, int64_t n) {
    printf("%lld\n", (long long)n);
    result->type = 1;
    result->i64 = n;
    result->f64 = 0.0;
    result->str = NULL;
    result->boolean = 0;
}

void dv_input(LightValue* result) {
    char buf[4096];
    if (fgets(buf, sizeof(buf), stdin)) {
        size_t len = strlen(buf);
        if (len > 0 && buf[len-1] == '\n') buf[len-1] = '\0';
        if (len > 1 && buf[len-2] == '\r') buf[len-2] = '\0';
        result->type = 3;
        result->i64 = 0;
        result->f64 = 0.0;
        result->str = dv_strdup(buf);
        result->boolean = 0;
        return;
    }
    result->type = 3;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = dv_strdup("");
    result->boolean = 0;
}

/* ================================================================
 * 字符串操作
 * ================================================================ */

void dv_concat(LightValue* result, LightValue* a, LightValue* b) {
    char* sa = dv_to_string(a);
    char* sb = dv_to_string(b);
    char* r = (char*)malloc(strlen(sa) + strlen(sb) + 1);
    if (r) { sprintf(r, "%s%s", sa, sb); }
    free(sa);
    free(sb);
    if (r) {
        result->type = 3;
        result->i64 = 0;
        result->f64 = 0.0;
        result->str = dv_strdup(r);
        result->boolean = 0;
    } else {
        result->type = 3;
        result->i64 = 0;
        result->f64 = 0.0;
        result->str = dv_strdup("");
        result->boolean = 0;
    }
    free(r);
}

int64_t dv_str_len(LightValue* v) {
    if (v->type == 3 && v->str) return (int64_t)strlen(v->str);
    return 0;
}

void dv_substr(LightValue* result, LightValue* str, int64_t start, int64_t len) {
    if (!str || str->type != 3 || !str->str) {
        dv_str(result, "");
        return;
    }
    const char* s = str->str;
    int64_t n = (int64_t)dv_utf8_char_count(s);
    int64_t st = start;
    if (st < 0) st = n + st;
    if (st < 0) st = 0;
    if (st >= n) { dv_str(result, ""); return; }
    int64_t en;
    if (len < 0) en = n;
    else en = st + len;
    if (en > n) en = n;
    if (en <= st) { dv_str(result, ""); return; }
    /* 字符偏移 -> 字节偏移 */
    size_t byte_st = dv_utf8_char_offset(s, (size_t)st);
    size_t byte_en = dv_utf8_char_offset(s, (size_t)en);
    size_t blen = byte_en - byte_st;
    char* out = (char*)malloc(blen + 1);
    if (out) {
        memcpy(out, s + byte_st, blen);
        out[blen] = '\0';
    }
    result->type = 3;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = out;
    result->boolean = 0;
}

int64_t dv_str_find(LightValue* str, LightValue* sub) {
    if (str->type != 3 || sub->type != 3 || !str->str || !sub->str) return -1;
    const char* found = strstr(str->str, sub->str);
    if (!found) return -1;
    return (int64_t)(found - str->str);
}

void dv_upper(LightValue* result, LightValue* str) {
    if (str->type != 3 || !str->str) {
        dv_str(result, "");
        return;
    }
    const char* s = str->str;
    int len = (int)strlen(s);
    char* out = (char*)malloc(len + 1);
    if (out) {
        for (int i = 0; i < len; i++) {
            out[i] = (char)toupper((unsigned char)s[i]);
        }
        out[len] = '\0';
    }
    result->type = 3;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = out;
    result->boolean = 0;
}

void dv_lower(LightValue* result, LightValue* str) {
    if (str->type != 3 || !str->str) {
        dv_str(result, "");
        return;
    }
    const char* s = str->str;
    int len = (int)strlen(s);
    char* out = (char*)malloc(len + 1);
    if (out) {
        for (int i = 0; i < len; i++) {
            out[i] = (char)tolower((unsigned char)s[i]);
        }
        out[len] = '\0';
    }
    result->type = 3;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = out;
    result->boolean = 0;
}

void dv_trim(LightValue* result, LightValue* str) {
    if (str->type != 3 || !str->str) {
        dv_str(result, "");
        return;
    }
    const char* s = str->str;
    int len = (int)strlen(s);
    int start = 0;
    int end = len - 1;
    while (start < len && isspace((unsigned char)s[start])) start++;
    while (end >= start && isspace((unsigned char)s[end])) end--;
    int out_len = end - start + 1;
    char* out = (char*)malloc(out_len + 1);
    if (out) {
        memcpy(out, s + start, out_len);
        out[out_len] = '\0';
    }
    result->type = 3;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = out;
    result->boolean = 0;
}

void dv_str_replace(LightValue* result, LightValue* str, LightValue* old_s, LightValue* new_s) {
    if (str->type != 3 || old_s->type != 3 || new_s->type != 3 || !str->str || !old_s->str || !new_s->str) {
        dv_str(result, "");
        return;
    }
    const char* s = str->str;
    const char* old_sub = old_s->str;
    const char* new_sub = new_s->str;
    int old_len = (int)strlen(old_sub);
    int new_len = (int)strlen(new_sub);
    if (old_len == 0) {
        dv_str(result, s);
        return;
    }
    int count = 0;
    const char* p = s;
    while ((p = strstr(p, old_sub)) != NULL) {
        count++;
        p += old_len;
    }
    int out_len = (int)strlen(s) + count * (new_len - old_len);
    char* out = (char*)malloc(out_len + 1);
    if (!out) {
        dv_str(result, "");
        return;
    }
    char* dst = out;
    p = s;
    while (1) {
        const char* found = strstr(p, old_sub);
        if (!found) {
            strcpy(dst, p);
            break;
        }
        memcpy(dst, p, found - p);
        dst += (found - p);
        memcpy(dst, new_sub, new_len);
        dst += new_len;
        p = found + old_len;
    }
    result->type = 3;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = out;
    result->boolean = 0;
}

/* ----------------------------------------------------------------
 * 字符串扩展（第三批移植）
 * ---------------------------------------------------------------- */

void dv_str_repeat(LightValue* result, LightValue* str, LightValue* times) {
    if (str->type != 3 || !str->str) {
        dv_str(result, "");
        return;
    }
    int64_t n = dv_to_i64(times);
    if (n <= 0) {
        dv_str(result, "");
        return;
    }
    size_t len = strlen(str->str);
    if (len == 0) {
        dv_str(result, "");
        return;
    }
    /* 防止溢出：单次最大 64MB */
    if (n > (64 * 1024 * 1024) / (int64_t)len) {
        n = (64 * 1024 * 1024) / (int64_t)len;
    }
    size_t out_len = len * (size_t)n;
    char* out = (char*)malloc(out_len + 1);
    if (!out) {
        dv_str(result, "");
        return;
    }
    out[0] = '\0';
    for (int64_t i = 0; i < n; i++) {
        strcat(out, str->str);
    }
    result->type = 3;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = out;
    result->boolean = 0;
}

int dv_str_contains(LightValue* str, LightValue* sub) {
    if (str->type != 3 || sub->type != 3 || !str->str || !sub->str) {
        return 0;
    }
    return strstr(str->str, sub->str) != NULL;
}

int dv_str_starts_with(LightValue* str, LightValue* prefix) {
    if (str->type != 3 || prefix->type != 3 || !str->str || !prefix->str) {
        return 0;
    }
    size_t plen = strlen(prefix->str);
    if (plen == 0) return 1;
    return strncmp(str->str, prefix->str, plen) == 0;
}

/* POSIX 风格路径连接（对齐 stdlib/内置核心路径.light 的 连接路径 口径）：
 *   b 以 '/' 开头 -> 返回 b（绝对路径丢弃前面全部）；
 *   a 为空 -> 返回 b；b 为空 -> 返回 a；
 *   否则 a 去尾斜杠 + '/' + b（a 已有尾斜杠不再补）。
 */
void dv_path_join(LightValue* result, LightValue* a, LightValue* b) {
    if (a->type != 3 || !a->str) { dv_clone(result, b); return; }
    if (b->type != 3 || !b->str) { dv_clone(result, a); return; }
    const char* sa = a->str;
    const char* sb = b->str;
    if (sb[0] == '/') { dv_clone(result, b); return; }
    size_t la = strlen(sa);
    size_t lb = strlen(sb);
    if (la == 0) { dv_clone(result, b); return; }
    if (lb == 0) { dv_clone(result, a); return; }
    int need_sep = (sa[la-1] != '/');
    char* out = (char*)malloc(la + (need_sep ? 1 : 0) + lb + 1);
    if (!out) { dv_str(result, ""); return; }
    memcpy(out, sa, la);
    size_t p = la;
    if (need_sep) out[p++] = '/';
    memcpy(out + p, sb, lb);
    out[p + lb] = '\0';
    result->type = 3;
    result->i64 = 0; result->f64 = 0.0; result->boolean = 0;
    result->list_size = 0; result->list_capacity = 0; result->list_data = NULL;
    result->str = out;
}

int dv_str_ends_with(LightValue* str, LightValue* suffix) {
    if (str->type != 3 || suffix->type != 3 || !str->str || !suffix->str) {
        return 0;
    }
    size_t slen = strlen(str->str);
    size_t flen = strlen(suffix->str);
    if (flen == 0) return 1;
    if (flen > slen) return 0;
    return strcmp(str->str + (slen - flen), suffix->str) == 0;
}

int64_t dv_str_count(LightValue* str, LightValue* sub) {
    if (str->type != 3 || sub->type != 3 || !str->str || !sub->str) {
        return 0;
    }
    size_t sub_len = strlen(sub->str);
    if (sub_len == 0) return 0;
    int64_t count = 0;
    const char* p = str->str;
    while ((p = strstr(p, sub->str)) != NULL) {
        count++;
        p += sub_len;
    }
    return count;
}

void dv_str_rjust(LightValue* result, LightValue* str, LightValue* width, LightValue* fill) {
    if (str->type != 3 || !str->str) {
        dv_str(result, "");
        return;
    }
    int64_t w = dv_to_i64(width);
    size_t len = strlen(str->str);
    if ((int64_t)len >= w) {
        dv_str(result, str->str);
        return;
    }
    char fc = ' ';
    if (fill && fill->type == 3 && fill->str && fill->str[0]) {
        fc = fill->str[0];
    }
    int64_t pad = w - (int64_t)len;
    char* out = (char*)malloc((size_t)w + 1);
    if (!out) { dv_str(result, str->str); return; }
    memset(out, fc, (size_t)pad);
    strcpy(out + pad, str->str);
    result->type = 3;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = out;
    result->boolean = 0;
}

void dv_str_ljust(LightValue* result, LightValue* str, LightValue* width, LightValue* fill) {
    if (str->type != 3 || !str->str) {
        dv_str(result, "");
        return;
    }
    int64_t w = dv_to_i64(width);
    size_t len = strlen(str->str);
    if ((int64_t)len >= w) {
        dv_str(result, str->str);
        return;
    }
    char fc = ' ';
    if (fill && fill->type == 3 && fill->str && fill->str[0]) {
        fc = fill->str[0];
    }
    int64_t pad = w - (int64_t)len;
    char* out = (char*)malloc((size_t)w + 1);
    if (!out) { dv_str(result, str->str); return; }
    strcpy(out, str->str);
    memset(out + len, fc, (size_t)pad);
    out[w] = '\0';
    result->type = 3;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = out;
    result->boolean = 0;
}

void dv_str_center(LightValue* result, LightValue* str, LightValue* width, LightValue* fill) {
    if (str->type != 3 || !str->str) {
        dv_str(result, "");
        return;
    }
    int64_t w = dv_to_i64(width);
    size_t len = strlen(str->str);
    if ((int64_t)len >= w) {
        dv_str(result, str->str);
        return;
    }
    char fc = ' ';
    if (fill && fill->type == 3 && fill->str && fill->str[0]) {
        fc = fill->str[0];
    }
    int64_t total = w - (int64_t)len;
    int64_t left = total / 2;
    int64_t right = total - left;
    char* out = (char*)malloc((size_t)w + 1);
    if (!out) { dv_str(result, str->str); return; }
    memset(out, fc, (size_t)left);
    strcpy(out + left, str->str);
    memset(out + left + len, fc, (size_t)right);
    out[w] = '\0';
    result->type = 3;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = out;
    result->boolean = 0;
}

void dv_str_reverse(LightValue* result, LightValue* str) {
    if (str->type != 3 || !str->str) {
        dv_str(result, "");
        return;
    }
    size_t len = strlen(str->str);
    char* out = (char*)malloc(len + 1);
    if (!out) { dv_str(result, ""); return; }
    for (size_t i = 0; i < len; i++) {
        out[i] = str->str[len - 1 - i];
    }
    out[len] = '\0';
    result->type = 3;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = out;
    result->boolean = 0;
}

/* ================================================================
 * 列表操作
 * ================================================================ */

/* 列表初始化辅助函数 */
static void dv_list_init_internal(LightValue* result, int capacity) {
    result->type = 4;  /* LIST 类型 */
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = NULL;
    result->boolean = 0;
    result->list_size = 0;
    result->list_capacity = capacity > 0 ? capacity : 4;
    result->list_data = (struct LightValue**)malloc(result->list_capacity * sizeof(LightValue*));
    for (int i = 0; i < result->list_capacity; i++) {
        result->list_data[i] = NULL;
    }
}

/* 列表增长辅助函数 */
static void dv_list_grow(LightValue* list) {
    if (!list || list->type != 4) return;
    int new_capacity = list->list_capacity * 2;
    struct LightValue** new_data = (struct LightValue**)malloc(new_capacity * sizeof(LightValue*));
    for (int i = 0; i < list->list_size; i++) {
        new_data[i] = list->list_data[i];
    }
    for (int i = list->list_size; i < new_capacity; i++) {
        new_data[i] = NULL;
    }
    free(list->list_data);
    list->list_data = new_data;
    list->list_capacity = new_capacity;
}

/* 列表添加元素辅助函数 */
static void dv_list_add_internal(LightValue* list, LightValue* elem) {
    if (!list || list->type != 4 || !elem) return;
    if (list->list_size >= list->list_capacity) {
        dv_list_grow(list);
    }
    if (list->list_size < list->list_capacity) {
        list->list_data[list->list_size] = elem;
        list->list_size++;
    }
}

void dv_list_new(LightValue* result) {
    dv_list_init_internal(result, 4);
}

/* 遍历取值：list(type=4) 按索引取元素；dict(type=7) 取第 i 个键（list_data[2*i]）。
   供 _gen_typed_foreach 使用——旧实现只走 dv_list_len/dv_list_get，dict 遍历恒为 0 次。 */
void dv_foreach_get(LightValue* result, LightValue* v, int64_t i) {
    if (!result) return;
    dv_null(result);
    if (!v) return;
    v = dv_deref(v);  /* 跟随 REF（dict 索引取值返回 REF），否则 dict 内数组/列表遍历取到 null */
    if (v->type == 4 && v->list_data) {
        if (i >= 0 && i < v->list_size && v->list_data[i]) dv_clone(result, v->list_data[i]);
    } else if (v->type == 7 && v->list_data) {
        if (i >= 0 && i < v->list_size && v->list_data[2 * i]) dv_clone(result, v->list_data[2 * i]);
    }
}

int64_t dv_list_len(LightValue* v) {
    if (v->type != 4) return 0;
    return v->list_size;
}

int64_t dv_len(LightValue* v) {
    v = dv_deref(v);
    if (v->type == 3) {
        const char* s = v->str ? v->str : "";
        if (strncmp(s, "dict:", 5) == 0) {
            return atoll(s + 5);
        }
        /* 按 Unicode 字符计数，与 src 后端（Python len）语义一致 */
        return (int64_t)dv_utf8_char_count(s);
    }
    if (v->type == 4) {
        return v->list_size;
    }
    if (v->type == 7) {
        /* DICT: list_size 是键值对数量 */
        return v->list_size;
    }
    if (v->type == LV_TYPE_TUPLE) {
        return v->list_size;
    }
    return 0;
}

void dv_list_get(LightValue* result, LightValue* list, int64_t index) {
    list = dv_deref(list);
    if (list->type != 4) {
        dv_null(result);
        return;
    }
    if (index < 0 || index >= list->list_size) {
        dv_null(result);
        return;
    }
    LightValue* elem = list->list_data[index];
    if (elem) {
        dv_clone(result, elem);
    } else {
        dv_null(result);
    }
}

/* 解引用 REF 并把实际值复制到 result（供 codegen 索引前统一 deref，避免
   REF 字符串/列表因 type=8 被索引逻辑误判走错分支——dict 索引取值返回 REF，
   再对其做字符串/列表索引时 type 判断需先解引用） */
void dv_deref_value(LightValue* result, LightValue* v) {
    if (!result) return;
    if (!v) { dv_null(result); return; }
    LightValue* real = dv_deref(v);
    if (real != v) {
        dv_clone(result, real);
    } else {
        *result = *v;
        if (v->type == 3 && v->str) {
            result->str = dv_strdup(v->str);
        }
    }
}

void dv_str_get(LightValue* result, LightValue* str_val, int64_t index) {
    if (!str_val || str_val->type != 3) {
        dv_null(result);
        return;
    }
    const char* s = str_val->str ? str_val->str : "";
    size_t nchars = dv_utf8_char_count(s);
    int64_t idx = index;
    if (idx < 0) idx += (int64_t)nchars;
    if (idx < 0 || idx >= (int64_t)nchars) {
        dv_null(result);
        return;
    }
    /* 第 idx 个字符按 Unicode 取字节，与 src 后端（Python 下标）语义一致 */
    size_t off = dv_utf8_char_offset(s, (size_t)idx);
    const unsigned char* p = (const unsigned char*)(s + off);
    size_t cl = dv_utf8_seq_len(p);
    size_t slen = strlen(s);
    char buf[5];
    size_t k = 0;
    while (k < cl && off + k < slen) { buf[k] = s[off + k]; k++; }
    buf[k] = '\0';
    dv_str(result, buf);
}

/* 列表操作：基于动态数组实现 */

void dv_list_append(LightValue* result, LightValue* list, LightValue* elem) {
    if (!result) return;

    /* 跟随 REF：如果 result 或 list 是 REF，找到实际目标 */
    LightValue* result_real = dv_deref(result);
    LightValue* list_real = dv_deref(list);

    /* 选择修改目标：优先 result_real（原地修改） */
    LightValue* target = (result_real == list_real) ? result_real : list_real;

    if (target->type != 4) {
        dv_list_new(target);
    }

    if (target->list_size >= target->list_capacity) {
        int new_cap = target->list_capacity * 2;
        if (new_cap < 4) new_cap = 4;
        LightValue** new_data = (LightValue**)realloc(target->list_data, new_cap * sizeof(LightValue*));
        if (!new_data) return;
        target->list_data = new_data;
        target->list_capacity = new_cap;
    }

    LightValue* elem_copy = (LightValue*)malloc(sizeof(LightValue));
    if (elem_copy) {
        dv_clone(elem_copy, elem);
        target->list_data[target->list_size] = elem_copy;
        target->list_size++;
    }

    /* 如果 result 是 REF，不需要更新 result（REF 指向 target，已自动反映修改） */
    /* 如果 result 不是 REF 且 != target，需要把结果复制到 result */
    if (result->type != 8 && result != target) {
        dv_clone(result, target);
    }
}

void dv_list_clear(LightValue* result, LightValue* list) {
    if (result == list) {
        /* 清空当前列表 */
        for (int i = 0; i < list->list_size; i++) {
            if (list->list_data[i]) {
                dv_free(list->list_data[i]);
                free(list->list_data[i]);
                list->list_data[i] = NULL;
            }
        }
        list->list_size = 0;
    } else {
        dv_list_new(result);
    }
}

void dv_list_set(LightValue* result, LightValue* list, int64_t index, LightValue* elem) {
    if (list->type != 4 || index < 0 || index >= list->list_size) {
        dv_clone(result, list);
        return;
    }
    
    /* 复制列表 */
    LightValue* new_list = (LightValue*)malloc(sizeof(LightValue));
    if (!new_list) { dv_clone(result, list); return; }
    
    dv_list_init_internal(new_list, list->list_capacity);
    for (int i = 0; i < list->list_size; i++) {
        LightValue* copy = (LightValue*)malloc(sizeof(LightValue));
        if (i == index && elem) {
            dv_clone(copy, elem);
        } else {
            dv_clone(copy, list->list_data[i]);
        }
        dv_list_add_internal(new_list, copy);
    }
    
    result->type = 4;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = NULL;
    result->boolean = 0;
    result->list_size = new_list->list_size;
    result->list_capacity = new_list->list_capacity;
    result->list_data = new_list->list_data;
    free(new_list);
}

void dv_list_insert(LightValue* result, LightValue* list, int64_t index, LightValue* elem) {
    if (list->type != 4) {
        dv_list_new(result);
        return;
    }
    
    if (index < 0) index = 0;
    if (index > list->list_size) index = list->list_size;
    
    /* 复制列表 */
    LightValue* new_list = (LightValue*)malloc(sizeof(LightValue));
    if (!new_list) { dv_clone(result, list); return; }
    
    dv_list_init_internal(new_list, list->list_capacity + 1);
    for (int i = 0; i < list->list_size; i++) {
        if (i == index) {
            LightValue* copy = (LightValue*)malloc(sizeof(LightValue));
            dv_clone(copy, elem);
            dv_list_add_internal(new_list, copy);
        }
        LightValue* copy = (LightValue*)malloc(sizeof(LightValue));
        dv_clone(copy, list->list_data[i]);
        dv_list_add_internal(new_list, copy);
    }
    if (index >= list->list_size) {
        LightValue* copy = (LightValue*)malloc(sizeof(LightValue));
        dv_clone(copy, elem);
        dv_list_add_internal(new_list, copy);
    }
    
    result->type = 4;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = NULL;
    result->boolean = 0;
    result->list_size = new_list->list_size;
    result->list_capacity = new_list->list_capacity;
    result->list_data = new_list->list_data;
    free(new_list);
}

void dv_list_remove(LightValue* result, LightValue* list, int64_t index) {
    if (list->type != 4 || index < 0 || index >= list->list_size) {
        dv_clone(result, list);
        return;
    }
    
    /* 复制列表（跳过要删除的元素） */
    LightValue* new_list = (LightValue*)malloc(sizeof(LightValue));
    if (!new_list) { dv_clone(result, list); return; }
    
    dv_list_init_internal(new_list, list->list_capacity);
    for (int i = 0; i < list->list_size; i++) {
        if (i == index) continue;
        LightValue* copy = (LightValue*)malloc(sizeof(LightValue));
        dv_clone(copy, list->list_data[i]);
        dv_list_add_internal(new_list, copy);
    }
    
    result->type = 4;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = NULL;
    result->boolean = 0;
    result->list_size = new_list->list_size;
    result->list_capacity = new_list->list_capacity;
    result->list_data = new_list->list_data;
    free(new_list);
}

/* 列表弹出：返回移除指定下标元素后的新列表（index<0 表示末尾，默认弹尾）。
 * 数据结构轻量.light 的 `列表弹出(己.数据)` 用法是「先取值、后弹出、弃返回值」，
 * 返回值即新列表，由调用方写回接收者（与 dv_list_remove 同语义）。
 */
void dv_list_pop(LightValue* result, LightValue* list, int64_t index) {
    if (list->type != 4 || list->list_size == 0) {
        dv_clone(result, list);
        return;
    }
    int64_t idx = index;
    if (idx < 0) idx = list->list_size - 1;
    dv_list_remove(result, list, idx);
}

int64_t dv_list_index_of(LightValue* list, LightValue* elem) {
    if (list->type != 4 || !elem) return -1;
    
    for (int i = 0; i < list->list_size; i++) {
        LightValue* e = list->list_data[i];
        if (e && dv_eq(e, elem)) {
            return i;
        }
    }
    return -1;
}

int64_t dv_list_contains(LightValue* list, LightValue* elem) {
    return dv_list_index_of(list, elem) >= 0 ? 1 : 0;
}

void dv_list_reverse(LightValue* result, LightValue* list) {
    if (list->type != 4) {
        dv_list_new(result);
        return;
    }
    
    LightValue* new_list = (LightValue*)malloc(sizeof(LightValue));
    if (!new_list) { dv_clone(result, list); return; }
    
    dv_list_init_internal(new_list, list->list_capacity);
    for (int i = list->list_size - 1; i >= 0; i--) {
        LightValue* copy = (LightValue*)malloc(sizeof(LightValue));
        dv_clone(copy, list->list_data[i]);
        dv_list_add_internal(new_list, copy);
    }
    
    result->type = 4;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = NULL;
    result->boolean = 0;
    result->list_size = new_list->list_size;
    result->list_capacity = new_list->list_capacity;
    result->list_data = new_list->list_data;
    free(new_list);
}

static int cmp_dv(const void* a, const void* b) {
    LightValue* va = *(LightValue**)a;
    LightValue* vb = *(LightValue**)b;
    if (!va && !vb) return 0;
    if (!va) return -1;
    if (!vb) return 1;
    char* sa = dv_to_string(va);
    char* sb = dv_to_string(vb);
    int cmp = strcmp(sa ? sa : "", sb ? sb : "");
    free(sa);
    free(sb);
    return cmp;
}

void dv_list_sort(LightValue* result, LightValue* list) {
    if (list->type != 4 || list->list_size <= 1) {
        dv_clone(result, list);
        return;
    }
    
    LightValue* new_list = (LightValue*)malloc(sizeof(LightValue));
    if (!new_list) { dv_clone(result, list); return; }
    
    dv_list_init_internal(new_list, list->list_capacity);
    for (int i = 0; i < list->list_size; i++) {
        LightValue* copy = (LightValue*)malloc(sizeof(LightValue));
        dv_clone(copy, list->list_data[i]);
        dv_list_add_internal(new_list, copy);
    }
    
    qsort(new_list->list_data, new_list->list_size, sizeof(LightValue*), cmp_dv);
    
    result->type = 4;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = NULL;
    result->boolean = 0;
    result->list_size = new_list->list_size;
    result->list_capacity = new_list->list_capacity;
    result->list_data = new_list->list_data;
    free(new_list);
}

void dv_str_split(LightValue* result, LightValue* str, LightValue* delim) {
    if (str->type != 3 || delim->type != 3 || !str->str || !delim->str) {
        dv_list_new(result);
        return;
    }
    const char* s = str->str;
    const char* d = delim->str;
    int d_len = (int)strlen(d);
    
    int count = 1;
    const char* p = s;
    if (d_len > 0) {
        while ((p = strstr(p, d)) != NULL) {
            count++;
            p += d_len;
        }
    }
    
    /* 创建 type=4 的列表 */
    LightValue* list = (LightValue*)malloc(sizeof(LightValue));
    if (!list) {
        dv_list_new(result);
        return;
    }
    dv_list_init_internal(list, count > 4 ? count : 4);
    
    p = s;
    for (int i = 0; i < count; i++) {
        const char* end;
        if (d_len > 0 && i < count - 1) {
            end = strstr(p, d);
        } else {
            end = p + strlen(p);
        }
        int part_len = (int)(end - p);
        char* part = (char*)malloc(part_len + 1);
        if (part) {
            memcpy(part, p, part_len);
            part[part_len] = '\0';
        }
        
        LightValue* elem = (LightValue*)malloc(sizeof(LightValue));
        if (elem) {
            dv_str(elem, part ? part : "");
            dv_list_add_internal(list, elem);
        }
        if (part) free(part);
        p = end + d_len;
    }
    
    result->type = 4;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = NULL;
    result->boolean = 0;
    result->list_size = list->list_size;
    result->list_capacity = list->list_capacity;
    result->list_data = list->list_data;
    free(list);
}

/* ================================================================
 * 字典操作 (type=7 DICT)
 * 字典存储格式: list_data = [key1*, val1*, key2*, val2*, ...]
 * list_size = 键值对数量, list_capacity = 已分配容量（对数）
 * 使用堆分配的 LightValue* 存储键值，使字典值（如列表）可被原地修改
 * ================================================================ */

void dv_dict_new(LightValue* result) {
    result->type = 7;  /* DICT 类型 */
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = NULL;
    result->boolean = 0;
    result->list_size = 0;
    result->list_capacity = 8;
    result->list_data = (struct LightValue**)calloc(result->list_capacity * 2, sizeof(LightValue*));
}

int64_t dv_dict_len(LightValue* v) {
    if (v->type != 7) return 0;
    return v->list_size;
}

/* 内部：查找键的位置，返回键值对索引，-1 表示未找到 */
static int64_t dv_dict_find(LightValue* dict, LightValue* key) {
    if (dict->type != 7 || !dict->list_data) return -1;
    LightValue key_str;
    dv_value_to_string(&key_str, key);
    const char* key_cstr = key_str.str ? key_str.str : "";
    int key_len = (int)strlen(key_cstr);
    for (int64_t i = 0; i < dict->list_size; i++) {
        LightValue* stored_key = dict->list_data[2 * i];
        if (!stored_key) continue;
        LightValue stored_key_str;
        dv_value_to_string(&stored_key_str, stored_key);
        const char* sk = stored_key_str.str ? stored_key_str.str : "";
        int sklen = (int)strlen(sk);
        if (sklen == key_len && strncmp(sk, key_cstr, key_len) == 0) {
            dv_free(&stored_key_str);
            dv_free(&key_str);
            return i;
        }
        dv_free(&stored_key_str);
    }
    dv_free(&key_str);
    return -1;
}

void dv_dict_set(LightValue* result, LightValue* dict, LightValue* key, LightValue* value) {
    /* 如果 result == dict（原地修改），直接修改 dict */
    LightValue* target = (result == dict) ? result : dict;

    if (target->type != 7) {
        /* 不是字典类型，创建新字典 */
        dv_dict_new(result);
        target = result;
    }

    /* 跟随 REF，避免将 REF 存入字典 */
    key = dv_deref(key);
    value = dv_deref(value);

    /* 查找键 */
    int64_t idx = dv_dict_find(target, key);

    if (idx >= 0) {
        /* 键存在，替换值 */
        LightValue* old_val = target->list_data[2 * idx + 1];
        if (old_val) {
            dv_free(old_val);
            free(old_val);
        }
        /* 堆分配新值并深拷贝（对于列表会复制 list_data） */
        LightValue* new_val = (LightValue*)malloc(sizeof(LightValue));
        if (new_val) {
            dv_clone(new_val, value);
            target->list_data[2 * idx + 1] = new_val;
        }
    } else {
        /* 键不存在，新增键值对 */
        if (target->list_size >= target->list_capacity) {
            int new_cap = target->list_capacity * 2;
            if (new_cap < 8) new_cap = 8;
            struct LightValue** new_data = (struct LightValue**)realloc(target->list_data, new_cap * 2 * sizeof(LightValue*));
            if (!new_data) {
                if (result != target) dv_clone(result, target);
                return;
            }
            /* 初始化新槽位为 NULL */
            for (int i = target->list_capacity * 2; i < new_cap * 2; i++) {
                new_data[i] = NULL;
            }
            target->list_data = new_data;
            target->list_capacity = new_cap;
        }
        /* 堆分配键和值 */
        LightValue* new_key = (LightValue*)malloc(sizeof(LightValue));
        LightValue* new_val = (LightValue*)malloc(sizeof(LightValue));
        if (new_key && new_val) {
            dv_clone(new_key, key);
            dv_clone(new_val, value);
            target->list_data[2 * target->list_size] = new_key;
            target->list_data[2 * target->list_size + 1] = new_val;
            target->list_size++;
        } else {
            if (new_key) free(new_key);
            if (new_val) free(new_val);
        }
    }

    /* 如果 result != target，需要把结果复制到 result */
    if (result != target) {
        dv_clone(result, target);
    }
}

void dv_dict_get(LightValue* result, LightValue* dict, LightValue* key) {
    if (dict->type != 7) {
        dv_null(result);
        return;
    }
    int64_t idx = dv_dict_find(dict, key);
    if (idx < 0) {
        dv_null(result);
        return;
    }
    LightValue* stored_val = dict->list_data[2 * idx + 1];
    if (!stored_val) {
        dv_null(result);
        return;
    }
    /* 返回 REF 引用，指向字典内部存储的值
       使原地修改（如 dv_list_append）通过 dv_deref 直接作用于 stored_val */
    result->type = 8;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = (char*)stored_val;
    result->boolean = 0;
    result->list_size = 0;
    result->list_capacity = 0;
    result->list_data = NULL;
}

void dv_dict_has(LightValue* result, LightValue* dict, LightValue* key) {
    if (dict->type != 7) {
        result->type = 5;
        result->i64 = 0;
        result->f64 = 0.0;
        result->boolean = 0;
        return;
    }
    int64_t idx = dv_dict_find(dict, key);
    result->type = 5;
    result->i64 = 0;
    result->f64 = 0.0;
    result->boolean = (idx >= 0) ? 1 : 0;
}

void dv_dict_keys(LightValue* result, LightValue* dict) {
    dv_list_new(result);
    if (dict->type != 7 || !dict->list_data) return;
    for (int64_t i = 0; i < dict->list_size; i++) {
        LightValue* stored_key = dict->list_data[2 * i];
        if (!stored_key) continue;
        LightValue key_copy;
        dv_clone(&key_copy, stored_key);
        LightValue list_copy;
        dv_clone(&list_copy, result);
        dv_list_append(result, &list_copy, &key_copy);
        dv_free(&list_copy);
        dv_free(&key_copy);
    }
}

void dv_dict_values(LightValue* result, LightValue* dict) {
    dv_list_new(result);
    if (dict->type != 7 || !dict->list_data) return;
    for (int64_t i = 0; i < dict->list_size; i++) {
        LightValue* stored_val = dict->list_data[2 * i + 1];
        if (!stored_val) continue;
        LightValue val_copy;
        dv_clone(&val_copy, stored_val);
        LightValue list_copy;
        dv_clone(&list_copy, result);
        dv_list_append(result, &list_copy, &val_copy);
        dv_free(&list_copy);
        dv_free(&val_copy);
    }
}

void dv_dict_remove(LightValue* result, LightValue* dict, LightValue* key) {
    if (dict->type != 7) {
        dv_clone(result, dict);
        return;
    }
    int64_t idx = dv_dict_find(dict, key);
    if (idx < 0) {
        dv_clone(result, dict);
        return;
    }
    /* 释放要删除的键值 */
    LightValue* old_key = dict->list_data[2 * idx];
    LightValue* old_val = dict->list_data[2 * idx + 1];
    if (old_key) { dv_free(old_key); free(old_key); }
    if (old_val) { dv_free(old_val); free(old_val); }
    /* 将后续键值对前移 */
    for (int64_t i = idx; i < dict->list_size - 1; i++) {
        dict->list_data[2 * i] = dict->list_data[2 * (i + 1)];
        dict->list_data[2 * i + 1] = dict->list_data[2 * (i + 1) + 1];
    }
    dict->list_data[2 * (dict->list_size - 1)] = NULL;
    dict->list_data[2 * (dict->list_size - 1) + 1] = NULL;
    dict->list_size--;
    dv_clone(result, dict);
}

/* ================================================================
 * 时间函数
 * ================================================================ */

double dv_timestamp(void) {
    return (double)time(NULL);
}

char* dv_format_time(double ts, const char* fmt) {
    if (!fmt) fmt = "%Y-%m-%d %H:%M:%S";
    time_t t = (time_t)ts;
    struct tm* tm_info = localtime(&t);
    char buffer[256];
    strftime(buffer, sizeof(buffer), fmt, tm_info);
    return dv_strdup(buffer);
}

/* ================================================================
 * 文件操作
 * ================================================================ */

int dv_file_exists(const char* path) {
    if (!path) return 0;
    return access(path, F_OK) == 0;
}

char* dv_read_file(const char* path) {
    if (!path) return dv_strdup("");
    FILE* f = fopen(path, "rb");
    if (!f) return dv_strdup("");
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);
    char* buf = (char*)malloc(size + 1);
    if (buf) {
        fread(buf, 1, size, f);
        buf[size] = '\0';
    }
    fclose(f);
    return buf ? buf : dv_strdup("");
}

void dv_write_file(const char* path, const char* content) {
    if (!path || !content) return;
    FILE* f = fopen(path, "wb");
    if (f) {
        fwrite(content, 1, strlen(content), f);
        fclose(f);
    }
}

void dv_append_file(const char* path, const char* content) {
    if (!path || !content) return;
    FILE* f = fopen(path, "ab");
    if (f) {
        fwrite(content, 1, strlen(content), f);
        fclose(f);
    }
}

/* ================================================================
 * 文件句柄（type=22）：打开文件 -> 句柄对象，f.write/f.close 方法调用
 * POSIX fopen 无编码概念：encoding 参数忽略，字节直写（UTF-8 兼容）。
 * 句柄 str 字段存 FILE*（不参与 strdup/free），dv_free/dv_clone 对
 * type=22 仅浅拷贝不释放，生命周期由 dv_file_close 关闭后置空。
 * ================================================================ */
#define LV_TYPE_FILE 22

/* LV_TYPE_TUPLE (23) 已在文件头部定义 */

/* 前向声明（异常机制定义于本文件后部；dv_open_file 打开失败时需抛 IO异常，
 * 对齐转译腿 Python open 的 FileNotFoundError 语义，供 文件系统.文件存在 的
 * 尝试/捕获 接住）。 */
void dv_create_exception_with_cause(LightValue* result, const char* class_name,
                                    const char* message, LightValue* cause);
void dv_throw_exception(LightValue* exception_obj);
void dv_open_file(LightValue* result, const char* path, const char* mode, const char* encoding) {
    (void)encoding; /* POSIX 无编码参数，字节直写 */
    if (!result) return;
    dv_null(result);
    if (!path || !mode) return;
    FILE* fp = fopen(path, mode);
    if (!fp) {
        /* 对齐转译腿 Python open：文件不存在/打开失败抛 IO异常
         * （FileNotFoundError 语义）。文件系统.light 的 文件存在 依赖
         * 「打开文件 失败抛异常」被 尝试/捕获 接住后返回 假。 */
        char msg[512];
        snprintf(msg, sizeof(msg), "无法打开文件: %s", path ? path : "");
        LightValue exc;
        dv_null(&exc);
        dv_create_exception_with_cause(&exc, "IOException", msg, NULL);
        dv_throw_exception(&exc);
        dv_free(&exc);
        return;
    }
    result->type = LV_TYPE_FILE;
    result->str = (char*)fp;
    result->i64 = 0;
    result->f64 = 0.0;
    result->boolean = 0;
    result->list_size = 0; result->list_capacity = 0; result->list_data = NULL;
}

void dv_file_write(LightValue* result, LightValue* handle, LightValue* text) {
    if (!result) return;
    dv_null(result);
    if (!handle || handle->type != LV_TYPE_FILE || !handle->str) return;
    if (!text || text->type != 3 || !text->str) return;
    FILE* fp = (FILE*)handle->str;
    size_t n = fwrite(text->str, 1, strlen(text->str), fp);
    result->type = 1;
    result->i64 = (int64_t)n;
}

void dv_file_close(LightValue* result, LightValue* handle) {
    if (!result) return;
    dv_null(result);
    if (!handle || handle->type != LV_TYPE_FILE || !handle->str) return;
    int rc = fclose((FILE*)handle->str);
    handle->str = NULL; /* 防重复 close / 防误用已关闭句柄 */
    result->type = 5;
    result->boolean = (rc == 0);
}

/* f.read(): from current file position to EOF (aligned with Python file.read()).
 * str field holds malloc'd content (LightValue* output, same as dv_file_write);
 * failure (no handle / not file / closed) -> result null; freed by dv_free type=3. */
void dv_file_read(LightValue* result, LightValue* handle) {
    if (!result) return;
    dv_null(result);
    if (!handle || handle->type != LV_TYPE_FILE || !handle->str) return;
    FILE* fp = (FILE*)handle->str;
    long pos = ftell(fp);
    fseek(fp, 0, SEEK_END);
    long end = ftell(fp);
    fseek(fp, pos, SEEK_SET);
    long n = (end > pos) ? (end - pos) : 0;
    char* buf = (char*)malloc((size_t)n + 1);
    if (!buf) return;
    size_t got = (n > 0) ? fread(buf, 1, (size_t)n, fp) : 0;
    buf[got] = '\0';
    result->type = 3;
    result->i64 = 0;
    result->f64 = 0.0;
    result->boolean = 0;
    result->list_size = 0; result->list_capacity = 0; result->list_data = NULL;
    result->str = buf;
}

int64_t dv_file_size(const char* path) {
    if (!path) return 0;
    FILE* f = fopen(path, "rb");
    if (!f) return 0;
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fclose(f);
    return (int64_t)size;
}

int dv_delete_file(const char* path) {
    if (!path) return -1;
    return remove(path);
}

#ifndef _WIN32
#include <dirent.h>
#endif

void dv_list_dir(LightValue* result, const char* path) {
    dv_list_new(result);
    if (!path) return;
    
#ifdef _WIN32
    /* Windows 实现 */
    char search_path[1024];
    snprintf(search_path, sizeof(search_path), "%s\\*", path);
    WIN32_FIND_DATAA find_data;
    HANDLE hFind = FindFirstFileA(search_path, &find_data);
    if (hFind == INVALID_HANDLE_VALUE) return;
    
    do {
        if (strcmp(find_data.cFileName, ".") == 0 || strcmp(find_data.cFileName, "..") == 0) {
            continue;
        }
        LightValue elem;
        dv_str(&elem, find_data.cFileName);
        LightValue tmp;
        dv_list_append(&tmp, result, &elem);
        dv_free(result);
        dv_clone(result, &tmp);
        dv_free(&elem);
        dv_free(&tmp);
    } while (FindNextFileA(hFind, &find_data));
    
    FindClose(hFind);
#else
    /* POSIX 实现 */
    DIR* dir = opendir(path);
    if (!dir) return;
    
    struct dirent* entry;
    while ((entry = readdir(dir)) != NULL) {
        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
            continue;
        }
        LightValue elem;
        dv_str(&elem, entry->d_name);
        LightValue tmp;
        dv_list_append(&tmp, result, &elem);
        dv_free(result);
        dv_clone(result, &tmp);
        dv_free(&elem);
        dv_free(&tmp);
    }
    closedir(dir);
#endif
}

/* ================================================================
 * 文件系统扩展
 * ================================================================ */

int dv_mkdir(const char* path) {
    if (!path) return -1;
#ifdef _WIN32
    return _mkdir(path);
#else
    return mkdir(path, 0755);
#endif
}

int dv_rmdir(const char* path) {
    if (!path) return -1;
#ifdef _WIN32
    return _rmdir(path);
#else
    return rmdir(path);
#endif
}

int dv_rename_file(const char* old_path, const char* new_path) {
    if (!old_path || !new_path) return -1;
    return rename(old_path, new_path);
}

int dv_copy_file(const char* src, const char* dst) {
    if (!src || !dst) return -1;
    FILE* fin = fopen(src, "rb");
    if (!fin) return -1;
    FILE* fout = fopen(dst, "wb");
    if (!fout) { fclose(fin); return -1; }
    char buf[8192];
    size_t n;
    while ((n = fread(buf, 1, sizeof(buf), fin)) > 0) {
        fwrite(buf, 1, n, fout);
    }
    fclose(fin);
    fclose(fout);
    return 0;
}

int dv_is_file(const char* path) {
    if (!path) return 0;
    struct stat st;
    if (stat(path, &st) != 0) return 0;
    return (st.st_mode & S_IFREG) ? 1 : 0;
}

int dv_is_dir(const char* path) {
    if (!path) return 0;
    struct stat st;
    if (stat(path, &st) != 0) return 0;
    return (st.st_mode & S_IFDIR) ? 1 : 0;
}

/* ================================================================
 * Base64 编码/解码
 * ================================================================ */

static const char b64_enc_table[] =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

static int b64_dec_val(char c) {
    if (c >= 'A' && c <= 'Z') return c - 'A';
    if (c >= 'a' && c <= 'z') return c - 'a' + 26;
    if (c >= '0' && c <= '9') return c - '0' + 52;
    if (c == '+') return 62;
    if (c == '/') return 63;
    return -1;
}

char* dv_base64_encode(const char* data, int len) {
    if (!data || len <= 0) return dv_strdup("");
    int out_len = 4 * ((len + 2) / 3);
    char* out = (char*)malloc(out_len + 1);
    if (!out) return dv_strdup("");
    int i = 0, j = 0;
    while (i < len) {
        unsigned int octet_a = (i < len) ? (unsigned char)data[i++] : 0;
        unsigned int octet_b = (i < len) ? (unsigned char)data[i++] : 0;
        unsigned int octet_c = (i < len) ? (unsigned char)data[i++] : 0;
        unsigned int triple = (octet_a << 16) | (octet_b << 8) | octet_c;
        out[j++] = b64_enc_table[(triple >> 18) & 0x3F];
        out[j++] = b64_enc_table[(triple >> 12) & 0x3F];
        out[j++] = b64_enc_table[(triple >> 6) & 0x3F];
        out[j++] = b64_enc_table[triple & 0x3F];
    }
    int mod = len % 3;
    if (mod >= 1) out[out_len - 1] = '=';
    if (mod == 1) out[out_len - 2] = '=';
    out[out_len] = '\0';
    return out;
}

char* dv_base64_decode(const char* str, int* out_len) {
    if (!str) { if (out_len) *out_len = 0; return dv_strdup(""); }
    int in_len = (int)strlen(str);
    while (in_len > 0 && str[in_len - 1] == '=') in_len--;
    int decoded_len = (in_len * 3) / 4;
    char* out = (char*)malloc(decoded_len + 1);
    if (!out) { if (out_len) *out_len = 0; return dv_strdup(""); }
    int i = 0, j = 0;
    while (i < in_len) {
        int v0 = b64_dec_val(str[i++]);
        int v1 = (i < in_len) ? b64_dec_val(str[i++]) : 0;
        int v2 = (i < in_len) ? b64_dec_val(str[i++]) : 0;
        int v3 = (i < in_len) ? b64_dec_val(str[i++]) : 0;
        if (v0 < 0 || v1 < 0 || v2 < 0 || v3 < 0) break;
        unsigned int triple = ((unsigned int)v0 << 18) | ((unsigned int)v1 << 12) | ((unsigned int)v2 << 6) | (unsigned int)v3;
        if (j < decoded_len) out[j++] = (char)((triple >> 16) & 0xFF);
        if (j < decoded_len) out[j++] = (char)((triple >> 8) & 0xFF);
        if (j < decoded_len) out[j++] = (char)(triple & 0xFF);
    }
    out[j] = '\0';
    if (out_len) *out_len = j;
    return out;
}

/* ================================================================
 * MD5 算法
 * ================================================================ */

typedef struct {
    uint32_t state[4];
    uint32_t count[2];
    unsigned char buffer[64];
} md5_ctx_t;

static void md5_transform(uint32_t state[4], const unsigned char block[64]);
static void md5_encode(unsigned char* output, const uint32_t* input, int len);
static void md5_decode(uint32_t* output, const unsigned char* input, int len);

static const unsigned char md5_padding[64] = {
    0x80, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
};

#define F(x, y, z) (((x) & (y)) | ((~x) & (z)))
#define G(x, y, z) (((x) & (z)) | ((y) & (~z)))
#define H(x, y, z) ((x) ^ (y) ^ (z))
#define I(x, y, z) ((y) ^ ((x) | (~z)))
#define ROTATE_LEFT(x, n) (((x) << (n)) | ((x) >> (32 - (n))))
#define FF(a, b, c, d, x, s, ac) { (a) += F((b), (c), (d)) + (x) + (uint32_t)(ac); (a) = ROTATE_LEFT((a), (s)); (a) += (b); }
#define GG(a, b, c, d, x, s, ac) { (a) += G((b), (c), (d)) + (x) + (uint32_t)(ac); (a) = ROTATE_LEFT((a), (s)); (a) += (b); }
#define HH(a, b, c, d, x, s, ac) { (a) += H((b), (c), (d)) + (x) + (uint32_t)(ac); (a) = ROTATE_LEFT((a), (s)); (a) += (b); }
#define II(a, b, c, d, x, s, ac) { (a) += I((b), (c), (d)) + (x) + (uint32_t)(ac); (a) = ROTATE_LEFT((a), (s)); (a) += (b); }

static void md5_init(md5_ctx_t* ctx) {
    ctx->count[0] = ctx->count[1] = 0;
    ctx->state[0] = 0x67452301;
    ctx->state[1] = 0xefcdab89;
    ctx->state[2] = 0x98badcfe;
    ctx->state[3] = 0x10325476;
}

static void md5_update(md5_ctx_t* ctx, const unsigned char* input, unsigned int input_len) {
    unsigned int i, index, part_len;
    index = (unsigned int)((ctx->count[0] >> 3) & 0x3F);
    if ((ctx->count[0] += ((uint32_t)input_len << 3)) < ((uint32_t)input_len << 3))
        ctx->count[1]++;
    ctx->count[1] += ((uint32_t)input_len >> 29);
    part_len = 64 - index;
    if (input_len >= part_len) {
        memcpy(&ctx->buffer[index], input, part_len);
        md5_transform(ctx->state, ctx->buffer);
        for (i = part_len; i + 63 < input_len; i += 64)
            md5_transform(ctx->state, &input[i]);
        index = 0;
    } else { i = 0; }
    memcpy(&ctx->buffer[index], &input[i], input_len - i);
}

static void md5_final(unsigned char digest[16], md5_ctx_t* ctx) {
    unsigned char bits[8];
    unsigned int index, pad_len;
    md5_encode(bits, ctx->count, 8);
    index = (unsigned int)((ctx->count[0] >> 3) & 0x3f);
    pad_len = (index < 56) ? (56 - index) : (120 - index);
    md5_update(ctx, md5_padding, pad_len);
    md5_update(ctx, bits, 8);
    md5_encode(digest, ctx->state, 16);
    memset(ctx, 0, sizeof(*ctx));
}

static void md5_transform(uint32_t state[4], const unsigned char block[64]) {
    uint32_t a = state[0], b = state[1], c = state[2], d = state[3], x[16];
    md5_decode(x, block, 64);
    FF(a, b, c, d, x[ 0],  7, 0xd76aa478);
    FF(d, a, b, c, x[ 1], 12, 0xe8c7b756);
    FF(c, d, a, b, x[ 2], 17, 0x242070db);
    FF(b, c, d, a, x[ 3], 22, 0xc1bdceee);
    FF(a, b, c, d, x[ 4],  7, 0xf57c0faf);
    FF(d, a, b, c, x[ 5], 12, 0x4787c62a);
    FF(c, d, a, b, x[ 6], 17, 0xa8304613);
    FF(b, c, d, a, x[ 7], 22, 0xfd469501);
    FF(a, b, c, d, x[ 8],  7, 0x698098d8);
    FF(d, a, b, c, x[ 9], 12, 0x8b44f7af);
    FF(c, d, a, b, x[10], 17, 0xffff5bb1);
    FF(b, c, d, a, x[11], 22, 0x895cd7be);
    FF(a, b, c, d, x[12],  7, 0x6b901122);
    FF(d, a, b, c, x[13], 12, 0xfd987193);
    FF(c, d, a, b, x[14], 17, 0xa679438e);
    FF(b, c, d, a, x[15], 22, 0x49b40821);
    GG(a, b, c, d, x[ 1],  5, 0xf61e2562);
    GG(d, a, b, c, x[ 6],  9, 0xc040b340);
    GG(c, d, a, b, x[11], 14, 0x265e5a51);
    GG(b, c, d, a, x[ 0], 20, 0xe9b6c7aa);
    GG(a, b, c, d, x[ 5],  5, 0xd62f105d);
    GG(d, a, b, c, x[10],  9, 0x02441453);
    GG(c, d, a, b, x[15], 14, 0xd8a1e681);
    GG(b, c, d, a, x[ 4], 20, 0xe7d3fbc8);
    GG(a, b, c, d, x[ 9],  5, 0x21e1cde6);
    GG(d, a, b, c, x[14],  9, 0xc33707d6);
    GG(c, d, a, b, x[ 3], 14, 0xf4d50d87);
    GG(b, c, d, a, x[ 8], 20, 0x455a14ed);
    GG(a, b, c, d, x[13],  5, 0xa9e3e905);
    GG(d, a, b, c, x[ 2],  9, 0xfcefa3f8);
    GG(c, d, a, b, x[ 7], 14, 0x676f02d9);
    GG(b, c, d, a, x[12], 20, 0x8d2a4c8a);
    HH(a, b, c, d, x[ 5],  4, 0xfffa3942);
    HH(d, a, b, c, x[ 8], 11, 0x8771f681);
    HH(c, d, a, b, x[11], 16, 0x6d9d6122);
    HH(b, c, d, a, x[14], 23, 0xfde5380c);
    HH(a, b, c, d, x[ 1],  4, 0xa4beea44);
    HH(d, a, b, c, x[ 4], 11, 0x4bdecfa9);
    HH(c, d, a, b, x[ 7], 16, 0xf6bb4b60);
    HH(b, c, d, a, x[10], 23, 0xbebfbc70);
    HH(a, b, c, d, x[13],  4, 0x289b7ec6);
    HH(d, a, b, c, x[ 0], 11, 0xeaa127fa);
    HH(c, d, a, b, x[ 3], 16, 0xd4ef3085);
    HH(b, c, d, a, x[ 6], 23, 0x04881d05);
    HH(a, b, c, d, x[ 9],  4, 0xd9d4d039);
    HH(d, a, b, c, x[12], 11, 0xe6db99e5);
    HH(c, d, a, b, x[15], 16, 0x1fa27cf8);
    HH(b, c, d, a, x[ 2], 23, 0xc4ac5665);
    II(a, b, c, d, x[ 0],  6, 0xf4292244);
    II(d, a, b, c, x[ 7], 10, 0x432aff97);
    II(c, d, a, b, x[14], 15, 0xab9423a7);
    II(b, c, d, a, x[ 5], 21, 0xfc93a039);
    II(a, b, c, d, x[12],  6, 0x655b59c3);
    II(d, a, b, c, x[ 3], 10, 0x8f0ccc92);
    II(c, d, a, b, x[10], 15, 0xffeff47d);
    II(b, c, d, a, x[ 1], 21, 0x85845dd1);
    II(a, b, c, d, x[ 8],  6, 0x6fa87e4f);
    II(d, a, b, c, x[15], 10, 0xfe2ce6e0);
    II(c, d, a, b, x[ 6], 15, 0xa3014314);
    II(b, c, d, a, x[13], 21, 0x4e0811a1);
    II(a, b, c, d, x[ 4],  6, 0xf7537e82);
    II(d, a, b, c, x[11], 10, 0xbd3af235);
    II(c, d, a, b, x[ 2], 15, 0x2ad7d2bb);
    II(b, c, d, a, x[ 9], 21, 0xeb86d391);
    state[0] += a; state[1] += b; state[2] += c; state[3] += d;
    memset(x, 0, sizeof(x));
}

static void md5_encode(unsigned char* output, const uint32_t* input, int len) {
    int i, j;
    for (i = 0, j = 0; j < len; i++, j += 4) {
        output[j] = (unsigned char)(input[i] & 0xff);
        output[j + 1] = (unsigned char)((input[i] >> 8) & 0xff);
        output[j + 2] = (unsigned char)((input[i] >> 16) & 0xff);
        output[j + 3] = (unsigned char)((input[i] >> 24) & 0xff);
    }
}

static void md5_decode(uint32_t* output, const unsigned char* input, int len) {
    int i, j;
    for (i = 0, j = 0; j < len; i++, j += 4) {
        output[i] = ((uint32_t)input[j]) | (((uint32_t)input[j + 1]) << 8) |
                    (((uint32_t)input[j + 2]) << 16) | (((uint32_t)input[j + 3]) << 24);
    }
}

static char* hex_encode(const unsigned char* data, int len) {
    static const char hex[] = "0123456789abcdef";
    char* out = (char*)malloc(len * 2 + 1);
    if (!out) return dv_strdup("");
    for (int i = 0; i < len; i++) {
        out[i * 2] = hex[(data[i] >> 4) & 0xF];
        out[i * 2 + 1] = hex[data[i] & 0xF];
    }
    out[len * 2] = '\0';
    return out;
}

char* dv_md5(const char* data, int len) {
    if (!data || len <= 0) return dv_strdup("d41d8cd98f00b204e9800998ecf8427e");
    md5_ctx_t ctx;
    unsigned char digest[16];
    md5_init(&ctx);
    md5_update(&ctx, (const unsigned char*)data, (unsigned int)len);
    md5_final(digest, &ctx);
    return hex_encode(digest, 16);
}

/* ================================================================
 * SHA-1 算法
 * ================================================================ */

typedef struct {
    uint32_t state[5];
    uint32_t count[2];
    unsigned char buffer[64];
} sha1_ctx_t;

static void sha1_transform(uint32_t state[5], const unsigned char buffer[64]);

#define SHA1_ROTATE_LEFT(value, bits) (((value) << (bits)) | ((value) >> (32 - (bits))))
#define SHA1_BLOCK_DATA(i) (block[i] = (SHA1_ROTATE_LEFT(block[i - 3] ^ block[i - 8] ^ block[i - 14] ^ block[i - 16], 1)))

static void sha1_init(sha1_ctx_t* ctx) {
    ctx->count[0] = ctx->count[1] = 0;
    ctx->state[0] = 0x67452301;
    ctx->state[1] = 0xEFCDAB89;
    ctx->state[2] = 0x98BADCFE;
    ctx->state[3] = 0x10325476;
    ctx->state[4] = 0xC3D2E1F0;
}

static void sha1_update(sha1_ctx_t* ctx, const unsigned char* data, uint32_t len) {
    uint32_t i, j;
    j = (ctx->count[0] >> 3) & 0x3F;
    if ((ctx->count[0] += len << 3) < (len << 3)) ctx->count[1]++;
    ctx->count[1] += len >> 29;
    if ((j + len) > 63) {
        memcpy(&ctx->buffer[j], data, (i = 64 - j));
        sha1_transform(ctx->state, ctx->buffer);
        for (; i + 63 < len; i += 64)
            sha1_transform(ctx->state, &data[i]);
        j = 0;
    } else { i = 0; }
    memcpy(&ctx->buffer[j], &data[i], len - i);
}

static void sha1_final(unsigned char digest[20], sha1_ctx_t* ctx) {
    uint32_t i, j;
    unsigned char bits[8];
    for (i = 0; i < 8; i++)
        bits[i] = (unsigned char)((ctx->count[(i >= 4 ? 0 : 1)] >> ((3 - (i & 3)) * 8)) & 255);
    unsigned char c = 0200;
    sha1_update(ctx, &c, 1);
    while ((ctx->count[0] & 504) != 448) {
        c = 0;
        sha1_update(ctx, &c, 1);
    }
    sha1_update(ctx, bits, 8);
    for (i = 0; i < 20; i++)
        digest[i] = (unsigned char)((ctx->state[i >> 2] >> ((3 - (i & 3)) * 8)) & 255);
    memset(ctx, 0, sizeof(*ctx));
}

static void sha1_transform(uint32_t state[5], const unsigned char buffer[64]) {
    uint32_t a, b, c, d, e;
    uint32_t block[80];
    int i;
    for (i = 0; i < 16; i++)
        block[i] = ((uint32_t)buffer[i * 4] << 24) | ((uint32_t)buffer[i * 4 + 1] << 16) |
                   ((uint32_t)buffer[i * 4 + 2] << 8) | (uint32_t)buffer[i * 4 + 3];
    for (i = 16; i < 80; i++)
        block[i] = SHA1_ROTATE_LEFT(block[i - 3] ^ block[i - 8] ^ block[i - 14] ^ block[i - 16], 1);
    a = state[0]; b = state[1]; c = state[2]; d = state[3]; e = state[4];
    for (i = 0; i < 20; i++) {
        uint32_t tmp = SHA1_ROTATE_LEFT(a, 5) + ((b & c) | (~b & d)) + e + block[i] + 0x5A827999;
        e = d; d = c; c = SHA1_ROTATE_LEFT(b, 30); b = a; a = tmp;
    }
    for (i = 20; i < 40; i++) {
        uint32_t tmp = SHA1_ROTATE_LEFT(a, 5) + (b ^ c ^ d) + e + block[i] + 0x6ED9EBA1;
        e = d; d = c; c = SHA1_ROTATE_LEFT(b, 30); b = a; a = tmp;
    }
    for (i = 40; i < 60; i++) {
        uint32_t tmp = SHA1_ROTATE_LEFT(a, 5) + ((b & c) | (b & d) | (c & d)) + e + block[i] + 0x8F1BBCDC;
        e = d; d = c; c = SHA1_ROTATE_LEFT(b, 30); b = a; a = tmp;
    }
    for (i = 60; i < 80; i++) {
        uint32_t tmp = SHA1_ROTATE_LEFT(a, 5) + (b ^ c ^ d) + e + block[i] + 0xCA62C1D6;
        e = d; d = c; c = SHA1_ROTATE_LEFT(b, 30); b = a; a = tmp;
    }
    state[0] += a; state[1] += b; state[2] += c; state[3] += d; state[4] += e;
}

char* dv_sha1(const char* data, int len) {
    if (!data || len <= 0) return dv_strdup("da39a3ee5e6b4b0d3255bfef95601890afd80709");
    sha1_ctx_t ctx;
    unsigned char digest[20];
    sha1_init(&ctx);
    sha1_update(&ctx, (const unsigned char*)data, (uint32_t)len);
    sha1_final(digest, &ctx);
    return hex_encode(digest, 20);
}

/* ================================================================
 * SHA-256 算法
 * ================================================================ */

typedef struct {
    uint32_t state[8];
    uint32_t count[2];
    unsigned char buffer[64];
} sha256_ctx_t;

static const uint32_t sha256_k[64] = {
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
};

#define SHA256_ROTR(x,n) (((x) >> (n)) | ((x) << (32 - (n))))
#define SHA256_S0(x) (SHA256_ROTR(x, 7) ^ SHA256_ROTR(x, 18) ^ ((x) >> 3))
#define SHA256_S1(x) (SHA256_ROTR(x, 17) ^ SHA256_ROTR(x, 19) ^ ((x) >> 10))
#define SHA256_E0(x) (SHA256_ROTR(x, 2) ^ SHA256_ROTR(x, 13) ^ SHA256_ROTR(x, 22))
#define SHA256_E1(x) (SHA256_ROTR(x, 6) ^ SHA256_ROTR(x, 11) ^ SHA256_ROTR(x, 25))
#define SHA256_CH(x,y,z) (((x) & (y)) ^ (~(x) & (z)))
#define SHA256_MAJ(x,y,z) (((x) & (y)) ^ ((x) & (z)) ^ ((y) & (z)))

static void sha256_transform(sha256_ctx_t* ctx, const unsigned char data[64]) {
    uint32_t a, b, c, d, e, f, g, h, t1, t2, m[64];
    int i, j;
    for (i = 0, j = 0; i < 16; i++, j += 4)
        m[i] = ((uint32_t)data[j] << 24) | ((uint32_t)data[j + 1] << 16) |
               ((uint32_t)data[j + 2] << 8) | (uint32_t)data[j + 3];
    for (; i < 64; i++)
        m[i] = SHA256_S1(m[i - 2]) + m[i - 7] + SHA256_S0(m[i - 15]) + m[i - 16];
    a = ctx->state[0]; b = ctx->state[1]; c = ctx->state[2]; d = ctx->state[3];
    e = ctx->state[4]; f = ctx->state[5]; g = ctx->state[6]; h = ctx->state[7];
    for (i = 0; i < 64; i++) {
        t1 = h + SHA256_E1(e) + SHA256_CH(e, f, g) + sha256_k[i] + m[i];
        t2 = SHA256_E0(a) + SHA256_MAJ(a, b, c);
        h = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
    }
    ctx->state[0] += a; ctx->state[1] += b; ctx->state[2] += c; ctx->state[3] += d;
    ctx->state[4] += e; ctx->state[5] += f; ctx->state[6] += g; ctx->state[7] += h;
}

static void sha256_init(sha256_ctx_t* ctx) {
    ctx->count[0] = ctx->count[1] = 0;
    ctx->state[0] = 0x6a09e667; ctx->state[1] = 0xbb67ae85;
    ctx->state[2] = 0x3c6ef372; ctx->state[3] = 0xa54ff53a;
    ctx->state[4] = 0x510e527f; ctx->state[5] = 0x9b05688c;
    ctx->state[6] = 0x1f83d9ab; ctx->state[7] = 0x5be0cd19;
}

static void sha256_update(sha256_ctx_t* ctx, const unsigned char* data, uint32_t len) {
    uint32_t i;
    for (i = 0; i < len; i++) {
        ctx->buffer[(ctx->count[0] >> 3) & 0x3F] = data[i];
        ctx->count[0] += 8;
        if ((ctx->count[0] & 0x1FF) == 0) {
            sha256_transform(ctx, ctx->buffer);
            ctx->count[1]++;
            ctx->count[0] = 0;
        }
    }
}

static void sha256_final(unsigned char digest[32], sha256_ctx_t* ctx) {
    uint32_t i;
    unsigned char bits[8];
    for (i = 0; i < 4; i++) {
        bits[i] = (unsigned char)((ctx->count[1] >> (24 - i * 8)) & 0xFF);
        bits[i + 4] = (unsigned char)((ctx->count[0] >> (24 - i * 8)) & 0xFF);
    }
    unsigned char pad = 0x80;
    sha256_update(ctx, &pad, 1);
    while ((ctx->count[0] & 0x1FF) != 448) {
        pad = 0;
        sha256_update(ctx, &pad, 1);
    }
    sha256_update(ctx, bits, 8);
    for (i = 0; i < 32; i++)
        digest[i] = (unsigned char)((ctx->state[i >> 2] >> (24 - (i & 3) * 8)) & 0xFF);
}

char* dv_sha256(const char* data, int len) {
    if (!data || len <= 0) return dv_strdup("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
    sha256_ctx_t ctx;
    unsigned char digest[32];
    sha256_init(&ctx);
    sha256_update(&ctx, (const unsigned char*)data, (uint32_t)len);
    sha256_final(digest, &ctx);
    return hex_encode(digest, 32);
}

/* ================================================================
 * JSON 操作
 * ================================================================ */

static char* list_to_json_inner(const char* list, int indent, int depth) {
    if (!list || strncmp(list, "list:", 5) != 0) return dv_strdup("[]");
    int len = atoi(list + 5);
    
    size_t est = 4;
    for (int i = 0; i < len; i++) {
        LightValue list_val;
        LightValue elem;
        dv_str(&list_val, list);
        dv_list_get(&elem, &list_val, i);
        char* es = dv_to_string(&elem);
        est += strlen(es) + 4;
        free(es);
        dv_free(&elem);
        dv_free(&list_val);
    }
    
    char* r = (char*)malloc(est + indent * 2 + 64);
    if (!r) return dv_strdup("[]");
    
    char* wp = r;
    *wp++ = '[';
    if (indent > 0) { *wp++ = '\n'; }
    
    const char* p = strchr(list + 5, ':');
    if (!p) { *wp++ = ']'; *wp = '\0'; return r; }
    p++;
    
    for (int i = 0; i < len; i++) {
        if (indent > 0) {
            for (int s = 0; s < indent; s++) *wp++ = ' ';
        }
        
        const char* end = strchr(p, '\x1f');
        if (!end) end = p + strlen(p);
        
        int is_num = 1;
        for (const char* c = p; c < end; c++) {
            if (*c != '-' && *c != '.' && (*c < '0' || *c > '9')) { is_num = 0; break; }
        }
        
        if (is_num && end > p && *p != '.') {
            size_t len = end - p;
            memcpy(wp, p, len); wp += len;
        } else {
            *wp++ = '"';
            size_t len = end - p;
            memcpy(wp, p, len); wp += len;
            *wp++ = '"';
        }
        
        if (i < len - 1) *wp++ = ',';
        if (indent > 0) *wp++ = '\n';
        p = (*end == '\x1f') ? end + 1 : end;
    }
    
    if (indent > 0 && len > 0) {
        for (int s = 0; s < indent - 2; s++) *wp++ = ' ';
    }
    *wp++ = ']';
    *wp = '\0';
    return r;
}

char* light_list_to_json(const char* list, int indent) {
    return list_to_json_inner(list, indent, 0);
}

/* ================================================================
 * 系统操作
 * ================================================================ */

char* dv_getenv(const char* name) {
    if (!name) return dv_strdup("");
    const char* val = getenv(name);
    return dv_strdup(val ? val : "");
}

char* dv_str_join(const char* list, const char* sep) {
    if (!list || strncmp(list, "list:", 5) != 0) return dv_strdup("");
    
    const char* colon = strchr(list + 5, ':');
    if (!colon) return dv_strdup("");
    
    int64_t len = atoll(list + 5);
    if (len <= 0) return dv_strdup("");
    
    size_t sep_len = sep ? strlen(sep) : 0;
    size_t total = 0;
    const char* p = colon + 1;
    
    for (int64_t i = 0; i < len; i++) {
        const char* end = strchr(p, '\x1f');
        if (!end) end = p + strlen(p);
        total += (end - p);
        if (i < len - 1) total += sep_len;
        p = end + 1;
    }
    
    char* result = (char*)malloc(total + 1);
    if (!result) return dv_strdup("");
    
    char* wp = result;
    p = colon + 1;
    
    for (int64_t i = 0; i < len; i++) {
        const char* end = strchr(p, '\x1f');
        if (!end) end = p + strlen(p);
        size_t elen = end - p;
        memcpy(wp, p, elen);
        wp += elen;
        if (i < len - 1 && sep_len > 0) {
            memcpy(wp, sep, sep_len);
            wp += sep_len;
        }
        p = end + 1;
    }
    
    *wp = '\0';
    return result;
}

int dv_setenv(const char* name, const char* value) {
    if (!name || !value) return -1;
#ifdef _WIN32
    return _putenv_s(name, value) == 0 ? 0 : -1;
#else
    return setenv(name, value, 1);
#endif
}

char* dv_getcwd(void) {
    char buf[4096];
#ifdef _WIN32
    if (_getcwd(buf, sizeof(buf)) == NULL) return dv_strdup("");
#else
    if (getcwd(buf, sizeof(buf)) == NULL) return dv_strdup("");
#endif
    return dv_strdup(buf);
}

int dv_chdir(const char* path) {
    if (!path) return -1;
#ifdef _WIN32
    return _chdir(path);
#else
    return chdir(path);
#endif
}

int dv_system(const char* cmd) {
    if (!cmd) return -1;
    return system(cmd);
}

void dv_exit(int code) {
    exit(code);
}

static int _dv_argc = 0;
static char** _dv_argv = NULL;

void dv_init_args(int argc, char** argv) {
    _dv_argc = argc;
    _dv_argv = argv;
}

void dv_get_args(LightValue* result) {
    dv_list_new(result);
    if (_dv_argc <= 0 || !_dv_argv) return;
    for (int i = 0; i < _dv_argc; i++) {
        LightValue elem;
        dv_str(&elem, _dv_argv[i]);
        LightValue tmp;
        dv_list_append(&tmp, result, &elem);
        dv_free(result);
        dv_clone(result, &tmp);
        dv_free(&elem);
        dv_free(&tmp);
    }
}

/* ================================================================
 * 异常处理 (Try/Catch/Throw)
 * ================================================================ */

#include <setjmp.h>

#define MAX_TRY_DEPTH 16
static jmp_buf __dv_jmp_bufs[MAX_TRY_DEPTH];
static int __dv_try_level = -1;
static char __dv_exception_str[1024];
static void* __dv_current_jmp_buf = NULL;  // 当前活跃的 jmp_buf

/* 调用栈追踪系统 */
#define MAX_CALL_STACK 64
#define MAX_STACK_ENTRY_LEN 128
typedef struct {
    char func_name[MAX_STACK_ENTRY_LEN];
    char file_name[MAX_STACK_ENTRY_LEN];
    int line_number;
} StackEntry;

static StackEntry __dv_call_stack[MAX_CALL_STACK];
static int __dv_call_stack_size = 0;

void dv_stack_push(const char* func_name, const char* file_name, int line_number) {
    if (__dv_call_stack_size < MAX_CALL_STACK) {
        StackEntry* entry = &__dv_call_stack[__dv_call_stack_size];
        strncpy(entry->func_name, func_name ? func_name : "unknown", MAX_STACK_ENTRY_LEN - 1);
        entry->func_name[MAX_STACK_ENTRY_LEN - 1] = '\0';
        strncpy(entry->file_name, file_name ? file_name : "", MAX_STACK_ENTRY_LEN - 1);
        entry->file_name[MAX_STACK_ENTRY_LEN - 1] = '\0';
        entry->line_number = line_number;
        __dv_call_stack_size++;
    }
}

void dv_stack_pop(void) {
    if (__dv_call_stack_size > 0) {
        __dv_call_stack_size--;
    }
}

int dv_get_stack_trace(char* buf, int buf_size) {
    if (!buf || buf_size <= 0) return 0;
    buf[0] = '\0';
    
    for (int i = __dv_call_stack_size - 1; i >= 0; i--) {
        StackEntry* entry = &__dv_call_stack[i];
        char entry_str[MAX_STACK_ENTRY_LEN * 2];
        if (entry->line_number > 0) {
            snprintf(entry_str, sizeof(entry_str), "    at %s (%s:%d)\n",
                    entry->func_name, entry->file_name, entry->line_number);
        } else {
            snprintf(entry_str, sizeof(entry_str), "    at %s\n", entry->func_name);
        }
        strncat(buf, entry_str, buf_size - strlen(buf) - 1);
    }
    return (int)strlen(buf);
}

int dv_get_stack_size(void) {
    return __dv_call_stack_size;
}

void dv_clear_stack_trace(void) {
    __dv_call_stack_size = 0;
}

void dv_try_enter(int* result, void* jmp_buf_ptr) {
    __dv_try_level++;
    if (__dv_try_level < MAX_TRY_DEPTH) {
        int r = setjmp(__dv_jmp_bufs[__dv_try_level]);
        *result = r;
        if (r != 0) {
            __dv_try_level--;
            return;
        }
    } else {
        *result = 0;
    }
}

void* dv_try_push(void) {
    __dv_try_level++;
    if (__dv_try_level >= MAX_TRY_DEPTH) {
        __dv_try_level--;
        return NULL;
    }
    return (void*)__dv_jmp_bufs[__dv_try_level];
}

int dv_setjmp_at_level(int level) {
    if (level < 0 || level >= MAX_TRY_DEPTH) return -1;
    return setjmp(__dv_jmp_bufs[level]);
}

void dv_try_pop(void) {
    if (__dv_try_level >= 0) {
        __dv_try_level--;
    }
}

void dv_try_end(void) {
    if (__dv_try_level >= 0) __dv_try_level--;
}

void dv_throw(LightValue* exc) {
    if (__dv_try_level < 0 || __dv_try_level >= MAX_TRY_DEPTH) return;
    char* s = dv_to_string(exc);
    strncpy(__dv_exception_str, s ? s : "unknown", 1023);
    __dv_exception_str[1023] = '\0';
    free(s);
    int level = __dv_try_level;
    longjmp(__dv_jmp_bufs[level], 1);
}

char* dv_get_exception_str(void) {
    return __dv_exception_str;
}

void dv_clear_exception(void) {
    __dv_exception_str[0] = '\0';
}

/* ================================================================
 * 异常类系统（基于类系统的异常）
 * ================================================================ */

/* 前置声明和常量 */
#ifndef MAX_CLASS_NAME_LEN
#define MAX_CLASS_NAME_LEN 64
#endif
void dv_get_class_name(LightValue* obj, char* buf, int buf_size);
int dv_is_object(LightValue* v);
int dv_isinstance(LightValue* obj, const char* class_name);
void dv_class_get_member(LightValue* result, LightValue* obj, const char* field_name);
void dv_class_set_member(LightValue* obj, const char* field_name, LightValue* value);
void dv_class_new_named(LightValue* result, const char* class_name);  // 前向声明

static LightValue __dv_current_exception_obj;
static int __dv_has_exception_obj = 0;

void dv_throw_exception(LightValue* exception_obj) {
    /* 获取当前栈追踪 */
    char stack_trace[4096];
    dv_get_stack_trace(stack_trace, sizeof(stack_trace));
    
    /* 设置异常的栈追踪属性 */
    LightValue stack_val;
    dv_str(&stack_val, stack_trace);
    dv_class_set_member(exception_obj, "栈追踪", &stack_val);
    dv_free(&stack_val);
    
    if (__dv_try_level < 0 || __dv_try_level >= MAX_TRY_DEPTH) {
        /* 没有 try 块，直接打印错误信息并退出 */
        char class_name[MAX_CLASS_NAME_LEN];
        dv_get_class_name(exception_obj, class_name, sizeof(class_name));
        
        LightValue msg_val;
        dv_null(&msg_val);
        dv_class_get_member(&msg_val, exception_obj, "消息");
        char* msg_str = dv_to_string(&msg_val);
        
        fprintf(stderr, "未捕获的异常: %s: %s\n", 
                class_name[0] ? class_name : "未知异常",
                msg_str ? msg_str : "");
        if (stack_trace[0]) {
            fprintf(stderr, "调用栈:\n%s", stack_trace);
        }
        free(msg_str);
        dv_free(&msg_val);
        exit(1);
    }
    
    /* 保存异常对象 */
    dv_clone(&__dv_current_exception_obj, exception_obj);
    __dv_has_exception_obj = 1;
    
    /* 同时保存字符串形式，用于向后兼容 */
    char* s = dv_to_string(exception_obj);
    strncpy(__dv_exception_str, s ? s : "unknown", 1023);
    __dv_exception_str[1023] = '\0';
    free(s);
    
    int level = __dv_try_level;
    longjmp(__dv_jmp_bufs[level], 1);
}

/* 创建带原因的异常 */
void dv_create_exception_with_cause(LightValue* result, const char* class_name, 
                                   const char* message, LightValue* cause) {
    /* 先创建普通异常对象 */
    dv_class_new_named(result, class_name);
    
    /* 设置消息 */
    LightValue msg_val;
    dv_str(&msg_val, message ? message : "");
    dv_class_set_member(result, "消息", &msg_val);
    dv_free(&msg_val);
    
    /* 如果有原因，设置原因属性 */
    if (cause) {
        LightValue cause_clone;
        dv_clone(&cause_clone, cause);
        dv_class_set_member(result, "原因", &cause_clone);
        dv_free(&cause_clone);
    }
    
    /* 设置空栈追踪（稍后抛出时会填充） */
    LightValue empty_stack;
    dv_str(&empty_stack, "");
    dv_class_set_member(result, "栈追踪", &empty_stack);
    dv_free(&empty_stack);
}

/* 获取异常的完整描述（包括原因链） */
int dv_exception_to_full_string(LightValue* exception_obj, char* buf, int buf_size) {
    if (!buf || buf_size <= 0) return 0;
    buf[0] = '\0';
    
    LightValue current_ex;
    dv_clone(&current_ex, exception_obj);
    
    int depth = 0;
    while (current_ex.type == 6 && dv_is_object(&current_ex)) {  // TYPE_OBJ
        if (depth > 0) {
            strncat(buf, "\n原因: ", buf_size - strlen(buf) - 1);
        }
        
        char class_name[MAX_CLASS_NAME_LEN];
        dv_get_class_name(&current_ex, class_name, sizeof(class_name));
        
        LightValue msg_val;
        dv_null(&msg_val);
        dv_class_get_member(&msg_val, &current_ex, "消息");
        char* msg_str = dv_to_string(&msg_val);
        
        char ex_line[512];
        snprintf(ex_line, sizeof(ex_line), "%s: %s", 
                class_name[0] ? class_name : "异常",
                msg_str ? msg_str : "");
        strncat(buf, ex_line, buf_size - strlen(buf) - 1);
        
        free(msg_str);
        dv_free(&msg_val);
        
        /* 获取栈追踪 */
        LightValue stack_val;
        dv_null(&stack_val);
        dv_class_get_member(&stack_val, &current_ex, "栈追踪");
        char* stack_str = dv_to_string(&stack_val);
        if (stack_str && stack_str[0]) {
            strncat(buf, "\n调用栈:\n", buf_size - strlen(buf) - 1);
            strncat(buf, stack_str, buf_size - strlen(buf) - 1);
        }
        free(stack_str);
        dv_free(&stack_val);
        
        /* 获取原因，继续循环 */
        LightValue next_ex;
        dv_null(&next_ex);
        dv_class_get_member(&next_ex, &current_ex, "原因");
        
        dv_free(&current_ex);
        
        if (next_ex.type == 6 && dv_is_object(&next_ex)) {
            dv_clone(&current_ex, &next_ex);
            dv_free(&next_ex);
            depth++;
        } else {
            dv_free(&next_ex);
            break;
        }
        
        if (depth > 10) break;  // 防止循环引用
    }
    
    dv_free(&current_ex);
    return (int)strlen(buf);
}

void dv_get_current_exception(LightValue* result) {
    if (__dv_has_exception_obj) {
        dv_clone(result, &__dv_current_exception_obj);
    } else {
        dv_str(result, __dv_exception_str);
    }
}

int dv_exception_match(LightValue* ex, const char* type_name) {
    if (!ex || !type_name) return 0;
    
    /* 如果是对象，使用 isinstance 检查 */
    if (dv_is_object(ex)) {
        return dv_isinstance(ex, type_name);
    }
    
    /* 字符串异常：特殊处理，匹配 "异常" 或 "Exception" */
    if (ex->type == 3 && ex->str) {
        if (strcmp(type_name, "异常") == 0 || strcmp(type_name, "Exception") == 0) {
            return 1;
        }
    }
    
    return 0;
}

void dv_clear_exception_obj(void) {
    if (__dv_has_exception_obj) {
        dv_free(&__dv_current_exception_obj);
        __dv_has_exception_obj = 0;
    }
    __dv_exception_str[0] = '\0';
}

/* 转换为字符串 */
/* ================================================================
 * 类型转换
 * ================================================================ */

void dv_to_int(LightValue* result, LightValue* v) {
    if (v->type == 1) {
        dv_clone(result, v);
        return;
    }
    if (v->type == 2) {
        result->type = 1;
        result->i64 = (int64_t)v->f64;
        result->f64 = 0.0;
        result->str = NULL;
        result->boolean = 0;
        return;
    }
    if (v->type == 3 && v->str) {
        int64_t val = 0;
        if (v->str[0] == '-' || v->str[0] == '+') {
            int sign = (v->str[0] == '-') ? -1 : 1;
            val = 0;
            for (const char* p = v->str + 1; *p; p++) {
                if (*p >= '0' && *p <= '9') {
                    val = val * 10 + (*p - '0');
                } else {
                    break;
                }
            }
            val *= sign;
        } else {
            val = 0;
            for (const char* p = v->str; *p; p++) {
                if (*p >= '0' && *p <= '9') {
                    val = val * 10 + (*p - '0');
                } else {
                    break;
                }
            }
        }
        result->type = 1;
        result->i64 = val;
        result->f64 = 0.0;
        result->str = NULL;
        result->boolean = 0;
        return;
    }
    result->type = 1;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = NULL;
    result->boolean = 0;
}

void dv_to_float(LightValue* result, LightValue* v) {
    if (v->type == 2) {
        dv_clone(result, v);
        return;
    }
    if (v->type == 1) {
        result->type = 2;
        result->i64 = 0;
        result->f64 = (double)v->i64;
        result->str = NULL;
        result->boolean = 0;
        return;
    }
    if (v->type == 3 && v->str) {
        double val = 0.0;
        int i = 0;
        int sign = 1;
        if (v->str[0] == '-') {
            sign = -1;
            i = 1;
        } else if (v->str[0] == '+') {
            i = 1;
        }
        for (; v->str[i]; i++) {
            if (v->str[i] >= '0' && v->str[i] <= '9') {
                val = val * 10 + (v->str[i] - '0');
            } else if (v->str[i] == '.') {
                double frac = 0.1;
                i++;
                for (; v->str[i]; i++) {
                    if (v->str[i] >= '0' && v->str[i] <= '9') {
                        val += (v->str[i] - '0') * frac;
                        frac *= 0.1;
                    } else {
                        break;
                    }
                }
                break;
            } else {
                break;
            }
        }
        result->type = 2;
        result->i64 = 0;
        result->f64 = val * sign;
        result->str = NULL;
        result->boolean = 0;
        return;
    }
    result->type = 2;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = NULL;
    result->boolean = 0;
}

void dv_to_bool_val(LightValue* result, LightValue* v) {
    int b = dv_to_bool(v);
    result->type = 5;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = NULL;
    result->boolean = b;
}

void dv_value_to_string(LightValue* result, LightValue* v) {
    char* s = dv_to_string(v);
    result->type = 3;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = dv_strdup(s ? s : "");
    result->boolean = 0;
    free(s);
}

/* ================================================================
 * 类 / 对象支持
 * ================================================================ */

/* 对象内部表示: "obj:field1\x1evalue1\x1efield2\x1evalue2..." */
#define OBJ_PREFIX "obj:"

/* ----------------------------------------------------------------
 * 对象缓冲唯一所有权辅助（P0-2 验收④：消除 dv_class_set_member 的 UAF 止血泄漏）
 *
 * 原生腿中对象以 type==3 字符串（"obj:" 前缀）表示，str 指向一块堆缓冲。
 * 该缓冲会被 dv_class_set_member 反复 free+realloc，且方法 prologue 会把 %self
 * 按值拷进局部 己（共享同一缓冲指针）——若直接 free 会造成 UAF。故采用「唯一所有权
 * + 深拷贝」模型（不需要全局引用计数）：
 *   - dv_obj_deepcopy_self：prologue / 赋值时把持有者的对象缓冲深拷贝到独立堆块，
 *     使每个持有者各有独立缓冲，set_member 的 free+realloc 不再波及他人（修复 UAF）。
 *   - dv_obj_release_slot：覆盖写前释放槽位旧有的对象缓冲（writeback 把 己 归位到
 *     %self 前，调用方旧缓冲已无其它持有者，可安全释放 → 消除 per-set_member 增长）。
 *   - dv_value_disown：writeback 移动后清空槽位 str，使后续释放对该槽位为无操作，
 *     避免与调用方/方法出口的重复释放造成双重释放。
 * 对象缓冲是普通 malloc 字符串，由 dv_free 的 type-3 分支统一 free（程序退出时
 * 由 OS 回收；本仓代码生成器不在局部槽位出口 emit dv_free，属既有模型）。
 * ---------------------------------------------------------------- */
int dv_is_obj_buffer(const char* s) {
    return s && strncmp(s, OBJ_PREFIX, strlen(OBJ_PREFIX)) == 0;
}
void dv_obj_release_slot(LightValue* v) {
    if (v && v->type == 3 && dv_is_obj_buffer(v->str)) {
        free(v->str);
        v->str = NULL;
    }
}
void dv_obj_deepcopy_self(LightValue* v) {
    if (v && v->type == 3 && dv_is_obj_buffer(v->str)) {
        char* d = dv_strdup(v->str);
        if (d) v->str = d;
    }
}
void dv_value_disown(LightValue* v) {
    if (v) v->str = NULL;
}

void dv_class_new(LightValue* result, int num_fields) {
    char prefix[32];
    snprintf(prefix, sizeof(prefix), "%s%d:", OBJ_PREFIX, num_fields);
    result->type = 3;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = dv_strdup(prefix);
    result->boolean = 0;
}

/* ================================================================
 * 字段值的有类型序列化（让列表/字典等类型能在对象字段的字符串存储中无损往返）
 *
 * 原生腿的对象字段原本只能用 int/float/字符串三种类型：列表/字典经 dv_to_string
 * 变成字符串、读回时又被当成字符串，导致 己.字段.追加 每次都从空列表重新开始
 * （SSE 等依赖「列表型实例字段」的模块在原生后端产出 0 事件的根因）。
 *
 * 这里把字段值序列化为「带类型标记的自描述字符串」，格式（均不含 \x1F 字段分隔符）：
 *   N              空
 *   B0 / B1        布尔
 *   I<十进制>      整数
 *   F<十进制>      浮点
 *   S<len>:<raw>   字符串，len 为字符数，后跟 ':' 与原始内容
 *   L<count>:<e1><e2>...  列表，count 为元素数，各元素为完整自描述编码
 *   D<count>:<k1><v1>...  字典，count 为键值对数
 * ================================================================ */
static char* dv_serialize_typed(LightValue* v) {
    v = dv_deref(v);
    if (!v) return dv_strdup("N");
    switch (v->type) {
        case 0: return dv_strdup("N");
        case 5: return dv_strdup(v->boolean ? "B1" : "B0");
        case 1: { char b[64]; snprintf(b, sizeof(b), "I%lld", (long long)v->i64); return dv_strdup(b); }
        case 2: { char b[64]; snprintf(b, sizeof(b), "F%g", v->f64); return dv_strdup(b); }
        case 3: {
            size_t len = v->str ? strlen(v->str) : 0;
            char* out = (char*)malloc(len + 24);
            if (!out) return dv_strdup("S0:");
            int n = snprintf(out, len + 24, "S%zu:", len);
            if (len && v->str) memcpy(out + n, v->str, len);
            out[n + len] = '\0';
            return out;
        }
        case 4: {
            size_t cap = 32;
            for (int i = 0; i < v->list_size; i++) {
                char* e = dv_serialize_typed(v->list_data[i]);
                cap += strlen(e) + 1;
                free(e);
            }
            char* out = (char*)malloc(cap);
            if (!out) return dv_strdup("L0:");
            int n = snprintf(out, cap, "L%d:", v->list_size);
            size_t pos = (size_t)n;
            for (int i = 0; i < v->list_size; i++) {
                char* e = dv_serialize_typed(v->list_data[i]);
                size_t el = strlen(e);
                memcpy(out + pos, e, el);
                pos += el;
                free(e);
            }
            out[pos] = '\0';
            return out;
        }
        case 7: {
            int pairs = v->list_size;
            size_t cap = 32;
            for (int i = 0; i < pairs * 2; i++) {
                char* e = dv_serialize_typed(v->list_data[i]);
                cap += strlen(e) + 1;
                free(e);
            }
            char* out = (char*)malloc(cap);
            if (!out) return dv_strdup("D0:");
            int n = snprintf(out, cap, "D%d:", pairs);
            size_t pos = (size_t)n;
            for (int i = 0; i < pairs * 2; i++) {
                char* e = dv_serialize_typed(v->list_data[i]);
                size_t el = strlen(e);
                memcpy(out + pos, e, el);
                pos += el;
                free(e);
            }
            out[pos] = '\0';
            return out;
        }
        default: return dv_strdup("N");
    }
}

/* 跳过十进制整数/浮点数的尾部 */
static const char* dv_skip_number(const char* s) {
    if (*s == '+' || *s == '-') s++;
    while (*s >= '0' && *s <= '9') s++;
    if (*s == '.') { s++; while (*s >= '0' && *s <= '9') s++; }
    if (*s == 'e' || *s == 'E') {
        s++;
        if (*s == '+' || *s == '-') s++;
        while (*s >= '0' && *s <= '9') s++;
    }
    return s;
}

/* 解析一个自描述编码的值，*pp 前进到该值之后；结果写入 result */
static void dv_parse_typed(const char** pp, LightValue* result) {
    const char* s = *pp;
    if (!s || !*s) { dv_null(result); *pp = s; return; }
    char tag = s[0];
    if (tag == 'N') { dv_null(result); *pp = s + 1; return; }
    if (tag == 'B') {
        result->type = 5; result->i64 = 0; result->f64 = 0.0; result->str = NULL;
        result->boolean = (s[1] == '1'); result->list_data = NULL; result->list_size = 0; result->list_capacity = 0;
        *pp = s + 2; return;
    }
    if (tag == 'I') {
        result->type = 1; result->i64 = atoll(s + 1); result->f64 = 0.0; result->str = NULL;
        result->boolean = 0; result->list_data = NULL; result->list_size = 0; result->list_capacity = 0;
        *pp = dv_skip_number(s + 1); return;
    }
    if (tag == 'F') {
        result->type = 2; result->f64 = atof(s + 1); result->i64 = 0; result->str = NULL;
        result->boolean = 0; result->list_data = NULL; result->list_size = 0; result->list_capacity = 0;
        *pp = dv_skip_number(s + 1); return;
    }
    if (tag == 'S') {
        const char* p = s + 1;
        size_t len = 0;
        while (*p >= '0' && *p <= '9') { len = len * 10 + (size_t)(*p - '0'); p++; }
        if (*p == ':') p++;
        char* buf = (char*)malloc(len + 1);
        if (!buf) { dv_str(result, ""); *pp = p; return; }
        memcpy(buf, p, len);
        buf[len] = '\0';
        result->type = 3; result->i64 = 0; result->f64 = 0.0; result->str = buf;
        result->boolean = 0; result->list_data = NULL; result->list_size = 0; result->list_capacity = 0;
        *pp = p + len; return;
    }
    if (tag == 'L') {
        const char* p = s + 1;
        int count = 0;
        while (*p >= '0' && *p <= '9') { count = count * 10 + (*p - '0'); p++; }
        if (*p == ':') p++;
        dv_list_new(result);
        for (int i = 0; i < count; i++) {
            LightValue elem;
            memset(&elem, 0, sizeof(elem));
            dv_parse_typed(&p, &elem);
            dv_list_append(result, result, &elem);
            dv_free(&elem);
        }
        *pp = p; return;
    }
    if (tag == 'D') {
        const char* p = s + 1;
        int count = 0;
        while (*p >= '0' && *p <= '9') { count = count * 10 + (*p - '0'); p++; }
        if (*p == ':') p++;
        dv_dict_new(result);
        for (int i = 0; i < count; i++) {
            LightValue k, val;
            memset(&k, 0, sizeof(k));
            memset(&val, 0, sizeof(val));
            dv_parse_typed(&p, &k);
            dv_parse_typed(&p, &val);
            dv_dict_set(result, result, &k, &val);
            dv_free(&k);
            dv_free(&val);
        }
        *pp = p; return;
    }
    /* 兜底：无标记值按字符串（到 \x1F 或行尾） */
    {
        const char* p = s;
        while (*p && *p != '\x1F') p++;
        size_t len = (size_t)(p - s);
        char* buf = (char*)malloc(len + 1);
        if (!buf) { dv_str(result, ""); *pp = p; return; }
        memcpy(buf, s, len);
        buf[len] = '\0';
        result->type = 3; result->i64 = 0; result->f64 = 0.0; result->str = buf;
        result->boolean = 0; result->list_data = NULL; result->list_size = 0; result->list_capacity = 0;
        *pp = p; return;
    }
}

void dv_class_set_member(LightValue* obj, const char* field_name, LightValue* value) {
    if (!obj || obj->type != 3 || !obj->str) return;
    if (strncmp(obj->str, OBJ_PREFIX, strlen(OBJ_PREFIX)) != 0) return;
    char* field_str = dv_serialize_typed(value);
    size_t field_name_len = strlen(field_name);
    size_t field_str_len = strlen(field_str);
    
    const char* data_start = obj->str + strlen(OBJ_PREFIX);
    const char* p = data_start;
    
    /* 查找字段是否已存在 */
    char search[512];
    size_t search_len = field_name_len + 1;
    if (search_len >= sizeof(search)) {
        free(field_str);
        return;
    }
    memcpy(search, field_name, field_name_len);
    search[field_name_len] = '\x1F';
    search[field_name_len + 1] = '\0';

    const char* found = strstr(p, search);
    int field_exists = (found != NULL);
    
    if (field_exists) {
        /* 字段已存在，更新其值 */
        const char* val_start = found + search_len;
        const char* val_end = strchr(val_start, '\x1F');
        if (!val_end) val_end = val_start + strlen(val_start);

        size_t old_val_len = val_end - val_start;
        size_t before_len = val_start - obj->str;
        size_t after_len = strlen(val_end);

        size_t new_len = before_len + field_str_len + after_len + 1;
        char* new_str = (char*)malloc(new_len);
        if (new_str) {
            memcpy(new_str, obj->str, before_len);
            memcpy(new_str + before_len, field_str, field_str_len);
            memcpy(new_str + before_len + field_str_len, val_end, after_len);
            new_str[before_len + field_str_len + after_len] = '\0';
            free(obj->str);
            obj->str = new_str;
        }
    } else {
        /* 字段不存在，追加 */
        size_t new_len = strlen(obj->str) + field_name_len + field_str_len + 3;
        char* new_str = (char*)malloc(new_len);
        if (new_str) {
            size_t pos = 0;
            memcpy(new_str + pos, obj->str, strlen(obj->str));
            pos += strlen(obj->str);
            memcpy(new_str + pos, field_name, field_name_len);
            pos += field_name_len;
            new_str[pos++] = '\x1F';
            memcpy(new_str + pos, field_str, field_str_len);
            pos += field_str_len;
            new_str[pos++] = '\x1F';
            new_str[pos] = '\0';
            free(obj->str);
            obj->str = new_str;
        }
    }
    free(field_str);
}

void dv_class_get_member(LightValue* result, LightValue* obj, const char* field_name) {
    if (!obj || obj->type != 3 || !obj->str) {
        dv_str(result, "");
        return;
    }
    if (strncmp(obj->str, OBJ_PREFIX, strlen(OBJ_PREFIX)) != 0) {
        dv_str(result, "");
        return;
    }
    
    /* 查找 field_name\x1Evalue\x1E */
    const char* p = obj->str + strlen(OBJ_PREFIX);
    char search[256];
    snprintf(search, sizeof(search), "%s%c", field_name, '\x1F');

    const char* found = strstr(p, search);
    if (!found) {
        dv_str(result, "");
        return;
    }
    
    found += strlen(search);
    const char* end = strchr(found, '\x1F');
    if (!end) end = found + strlen(found);
    
    size_t len = end - found;
    char* val = (char*)malloc(len + 1);
    if (val) {
        memcpy(val, found, len);
        val[len] = '\0';

        /* 有类型标记的值（列表/字典/整数/浮点/布尔/空）按自描述编码还原类型 */
        char tag = val[0];
        if (tag == 'N' || tag == 'B' || tag == 'I' || tag == 'F' || tag == 'S' || tag == 'L' || tag == 'D') {
            const char* p = val;
            dv_parse_typed(&p, result);
            free(val);
            return;
        }

        /* 兜底：无标记值（类默认空值 / __class__）按原启发式判定类型 */
        /* 检测类型并返回 */
        int is_int = 1, is_float = 0, dot = 0;
        int neg = (len > 0 && val[0] == '-') ? 1 : 0;
        for (size_t i = neg; i < len; i++) {
            if (val[i] < '0' || val[i] > '9') { is_int = 0; break; }
        }
        if (is_int && len > (size_t)neg) {
            result->type = 1;
            result->i64 = atoll(val);
            result->f64 = 0.0;
            result->str = NULL;
            result->boolean = 0;
            free(val);
            return;
        }
        neg = (len > 0 && val[0] == '-') ? 1 : 0;
        for (size_t i = neg; i < len; i++) {
            if (val[i] == '.') { dot++; continue; }
            if (val[i] < '0' || val[i] > '9') { is_float = 0; break; }
            is_float = 1;
        }
        if (is_float && dot == 1) {
            result->type = 2;
            result->i64 = 0;
            result->f64 = atof(val);
            result->str = NULL;
            result->boolean = 0;
            free(val);
            return;
        }
        result->type = 3;
        result->i64 = 0;
        result->f64 = 0.0;
        result->str = val;
        result->boolean = 0;
        return;
    }
    dv_str(result, "");
}

/* ================================================================
 * 类元信息系统
 * ================================================================ */

#define MAX_CLASS_NAME_LEN 64
#define CLASS_FIELD_PREFIX "__class__"
#define CLASS_FIELD_PREFIX_LEN 9  /* strlen("__class__") */
#define MAX_INHERIT_DEPTH 32

#define MAX_CLASSES 128
#define MAX_METHODS_PER_CLASS 64
#define MAX_ATTRS_PER_CLASS 128
#define MAX_INTERFACES 64
#define MAX_METHODS_PER_INTERFACE 32

typedef struct {
    char name[MAX_CLASS_NAME_LEN];
    int num_methods;
    char method_names[MAX_METHODS_PER_INTERFACE][MAX_CLASS_NAME_LEN];
    char method_signatures[MAX_METHODS_PER_INTERFACE][MAX_CLASS_NAME_LEN];
} LightInterfaceInfo;

typedef struct {
    char name[MAX_CLASS_NAME_LEN];
    char super_name[MAX_CLASS_NAME_LEN];
    int num_methods;
    char method_names[MAX_METHODS_PER_CLASS][MAX_CLASS_NAME_LEN];
    void* method_ptrs[MAX_METHODS_PER_CLASS];
    int method_flags[MAX_METHODS_PER_CLASS];  /* 0=实例方法, 1=类方法, 2=静态方法 */
    int num_attrs;
    char attr_names[MAX_ATTRS_PER_CLASS][MAX_CLASS_NAME_LEN];
    int num_implemented_interfaces;
    char implemented_interfaces[MAX_INTERFACES][MAX_CLASS_NAME_LEN];
} LightClassInfo;

static LightClassInfo __dv_classes[MAX_CLASSES];
static int __dv_num_classes = 0;
static LightInterfaceInfo __dv_interfaces[MAX_INTERFACES];
static int __dv_num_interfaces = 0;

/* 前置声明 */
LightClassInfo* dv_find_class(const char* name);

/* 注册类，返回类索引，失败返回 -1 */
int dv_register_class(const char* name, const char* super_name) {
    if (!name || !name[0]) return -1;
    if (__dv_num_classes >= MAX_CLASSES) return -1;
    
    /* 检查是否已存在 */
    LightClassInfo* existing = dv_find_class(name);
    if (existing) {
        return (int)(existing - __dv_classes);
    }
    
    LightClassInfo* cls = &__dv_classes[__dv_num_classes];
    memset(cls, 0, sizeof(LightClassInfo));
    strncpy(cls->name, name, MAX_CLASS_NAME_LEN - 1);
    cls->name[MAX_CLASS_NAME_LEN - 1] = '\0';
    if (super_name && super_name[0]) {
        strncpy(cls->super_name, super_name, MAX_CLASS_NAME_LEN - 1);
        cls->super_name[MAX_CLASS_NAME_LEN - 1] = '\0';
    }
    cls->num_methods = 0;
    cls->num_attrs = 0;
    
    __dv_num_classes++;
    return __dv_num_classes - 1;
}

/* 按名查找类，找不到返回 NULL */
LightClassInfo* dv_find_class(const char* name) {
    if (!name || !name[0]) return NULL;
    for (int i = 0; i < __dv_num_classes; i++) {
        if (strcmp(__dv_classes[i].name, name) == 0) {
            return &__dv_classes[i];
        }
    }
    return NULL;
}

/* 注册方法（内部通用函数），method_flag: 0=实例方法, 1=类方法, 2=静态方法 */
static int dv_register_method_internal(const char* class_name, const char* method_name, void* func_ptr, int method_flag) {
    if (!class_name || !method_name || !func_ptr) return -1;
    
    LightClassInfo* cls = dv_find_class(class_name);
    if (!cls) return -1;
    if (cls->num_methods >= MAX_METHODS_PER_CLASS) return -1;
    
    /* 检查方法是否已存在 */
    for (int i = 0; i < cls->num_methods; i++) {
        if (strcmp(cls->method_names[i], method_name) == 0) {
            cls->method_ptrs[i] = func_ptr;
            cls->method_flags[i] = method_flag;
            return 0;
        }
    }
    
    strncpy(cls->method_names[cls->num_methods], method_name, MAX_CLASS_NAME_LEN - 1);
    cls->method_names[cls->num_methods][MAX_CLASS_NAME_LEN - 1] = '\0';
    cls->method_ptrs[cls->num_methods] = func_ptr;
    cls->method_flags[cls->num_methods] = method_flag;
    cls->num_methods++;
    return 0;
}

/* 注册实例方法，成功返回 0，失败返回 -1 */
int dv_register_method(const char* class_name, const char* method_name, void* func_ptr) {
    return dv_register_method_internal(class_name, method_name, func_ptr, 0);
}

/* 注册类方法，成功返回 0，失败返回 -1 */
int dv_register_class_method(const char* class_name, const char* method_name, void* func_ptr) {
    return dv_register_method_internal(class_name, method_name, func_ptr, 1);
}

/* 注册静态方法，成功返回 0，失败返回 -1 */
int dv_register_static_method(const char* class_name, const char* method_name, void* func_ptr) {
    return dv_register_method_internal(class_name, method_name, func_ptr, 2);
}

/* 内部辅助：递归查找方法（带深度限制） */
static void* dv_find_method_inner(const char* class_name, const char* method_name, int depth) {
    if (!class_name || !method_name) return NULL;
    if (depth > MAX_INHERIT_DEPTH) return NULL;
    
    LightClassInfo* cls = dv_find_class(class_name);
    if (!cls) return NULL;
    
    /* 在当前类中查找 */
    for (int i = 0; i < cls->num_methods; i++) {
        if (strcmp(cls->method_names[i], method_name) == 0) {
            return cls->method_ptrs[i];
        }
    }
    
    /* 递归查找父类 */
    if (cls->super_name[0] != '\0') {
        return dv_find_method_inner(cls->super_name, method_name, depth + 1);
    }
    
    return NULL;
}

/* 查找方法（递归查找父类），找不到返回 NULL */
void* dv_find_method(const char* class_name, const char* method_name) {
    return dv_find_method_inner(class_name, method_name, 0);
}

/* 注册属性，成功返回 0，失败返回 -1 */
int dv_register_attr(const char* class_name, const char* attr_name) {
    if (!class_name || !attr_name) return -1;
    
    LightClassInfo* cls = dv_find_class(class_name);
    if (!cls) return -1;
    if (cls->num_attrs >= MAX_ATTRS_PER_CLASS) return -1;
    
    /* 检查属性是否已存在 */
    for (int i = 0; i < cls->num_attrs; i++) {
        if (strcmp(cls->attr_names[i], attr_name) == 0) {
            return 0;
        }
    }
    
    strncpy(cls->attr_names[cls->num_attrs], attr_name, MAX_CLASS_NAME_LEN - 1);
    cls->attr_names[cls->num_attrs][MAX_CLASS_NAME_LEN - 1] = '\0';
    cls->num_attrs++;
    return 0;
}

/* ================================================================
 * 接口系统（Level 7）
 * ================================================================ */

/* 查找接口，找不到返回 NULL */
static LightInterfaceInfo* dv_find_interface(const char* name) {
    if (!name) return NULL;
    for (int i = 0; i < __dv_num_interfaces; i++) {
        if (strcmp(__dv_interfaces[i].name, name) == 0) {
            return &__dv_interfaces[i];
        }
    }
    return NULL;
}

/* 注册接口，返回 0 表示成功，-1 表示失败 */
int dv_register_interface(const char* name) {
    if (!name) return -1;

    /* 已存在则跳过 */
    if (dv_find_interface(name)) return 0;

    if (__dv_num_interfaces >= MAX_INTERFACES) return -1;

    LightInterfaceInfo* iface = &__dv_interfaces[__dv_num_interfaces];
    memset(iface, 0, sizeof(LightInterfaceInfo));
    strncpy(iface->name, name, MAX_CLASS_NAME_LEN - 1);
    iface->name[MAX_CLASS_NAME_LEN - 1] = '\0';
    __dv_num_interfaces++;
    return 0;
}

/* 注册接口方法，返回 0 表示成功，-1 表示失败
 * signature 格式："方法名/参数个数"
 */
int dv_register_interface_method(const char* interface_name, const char* method_name, const char* signature) {
    if (!interface_name || !method_name) return -1;

    LightInterfaceInfo* iface = dv_find_interface(interface_name);
    if (!iface) return -1;

    if (iface->num_methods >= MAX_METHODS_PER_INTERFACE) return -1;

    /* 检查是否已注册 */
    for (int i = 0; i < iface->num_methods; i++) {
        if (strcmp(iface->method_names[i], method_name) == 0) {
            return 0;
        }
    }

    strncpy(iface->method_names[iface->num_methods], method_name, MAX_CLASS_NAME_LEN - 1);
    iface->method_names[iface->num_methods][MAX_CLASS_NAME_LEN - 1] = '\0';
    if (signature) {
        strncpy(iface->method_signatures[iface->num_methods], signature, MAX_CLASS_NAME_LEN - 1);
        iface->method_signatures[iface->num_methods][MAX_CLASS_NAME_LEN - 1] = '\0';
    }
    iface->num_methods++;
    return 0;
}

/* 检查类是否实现指定接口，返回 1 表示实现，0 表示未实现
 * 注意：当前实现仅基于显式声明，未来可扩展为基于方法签名检查
 */
/* 注册类实现的接口，返回 0 表示成功，-1 表示失败 */
int dv_register_class_implements(const char* class_name, const char* interface_name) {
    if (!class_name || !interface_name) return -1;

    LightClassInfo* cls = dv_find_class(class_name);
    if (!cls) return -1;

    if (cls->num_implemented_interfaces >= MAX_INTERFACES) return -1;

    /* 检查是否已注册 */
    for (int i = 0; i < cls->num_implemented_interfaces; i++) {
        if (strcmp(cls->implemented_interfaces[i], interface_name) == 0) {
            return 0;
        }
    }

    strncpy(cls->implemented_interfaces[cls->num_implemented_interfaces],
            interface_name, MAX_CLASS_NAME_LEN - 1);
    cls->implemented_interfaces[cls->num_implemented_interfaces][MAX_CLASS_NAME_LEN - 1] = '\0';
    cls->num_implemented_interfaces++;
    return 0;
}

int dv_class_implements_interface(const char* class_name, const char* interface_name) {
    if (!class_name || !interface_name) return 0;

    LightClassInfo* cls = dv_find_class(class_name);
    if (!cls) return 0;

    /* 显式声明检查 */
    for (int i = 0; i < cls->num_implemented_interfaces; i++) {
        if (strcmp(cls->implemented_interfaces[i], interface_name) == 0) {
            return 1;
        }
    }

    /* 递归检查父类 */
    if (cls->super_name[0] != '\0') {
        return dv_class_implements_interface(cls->super_name, interface_name);
    }

    return 0;
}

/* 通过接口调用方法（接口 vtable 分发）
 *
 * 根据对象类型查找方法，验证对象类是否实现了指定接口，
 * 然后调用该方法。这是接口多态的核心实现。
 *
 * 参数：
 *   result: 输出结果
 *   obj: 对象指针
 *   interface_name: 接口名
 *   method_name: 方法名
 *   args: 参数数组
 *   num_args: 参数个数
 *
 * 返回：0 表示成功，-1 表示失败（接口未实现或方法未找到）
 */
int dv_call_interface_method(DuanValue* result, DuanValue* obj,
                              const char* interface_name, const char* method_name,
                              DuanValue* args, int num_args) {
    if (!result || !obj || !interface_name || !method_name) {
        if (result) dv_null(result);
        return -1;
    }

    /* 获取对象类名 */
    char class_name[MAX_CLASS_NAME_LEN];
    dv_get_class_name(obj, class_name, sizeof(class_name));
    if (!class_name[0]) {
        dv_null(result);
        return -1;
    }

    /* 验证类是否实现了指定接口 */
    if (!dv_class_implements_interface(class_name, interface_name)) {
        dv_null(result);
        return -1;
    }

    /* 在类层次中查找方法 */
    void* func_ptr = dv_find_method(class_name, method_name);
    if (!func_ptr) {
        dv_null(result);
        return -1;
    }

    /* 调用方法 */
    DuanMethodFunc method = (DuanMethodFunc)func_ptr;
    dv_null(result);
    method(result, obj, args, num_args);
    return 0;
}

/* 内部辅助：递归收集父类所有属性（带深度限制） */
static void collect_all_attrs_inner(const char* class_name, char attrs[][MAX_CLASS_NAME_LEN], int* count, int depth) {
    if (!class_name || !class_name[0] || !attrs || !count) return;
    if (depth > MAX_INHERIT_DEPTH) return;
    
    LightClassInfo* cls = dv_find_class(class_name);
    if (!cls) return;
    
    /* 先递归收集父类属性 */
    if (cls->super_name[0] != '\0') {
        collect_all_attrs_inner(cls->super_name, attrs, count, depth + 1);
    }
    
    /* 添加当前类的属性（去重） */
    for (int i = 0; i < cls->num_attrs; i++) {
        int found = 0;
        for (int j = 0; j < *count; j++) {
            if (strcmp(attrs[j], cls->attr_names[i]) == 0) {
                found = 1;
                break;
            }
        }
        if (!found && *count < MAX_ATTRS_PER_CLASS) {
            strncpy(attrs[*count], cls->attr_names[i], MAX_CLASS_NAME_LEN - 1);
            attrs[*count][MAX_CLASS_NAME_LEN - 1] = '\0';
            (*count)++;
        }
    }
}

/* 递归收集父类所有属性 */
static void collect_all_attrs(const char* class_name, char attrs[][MAX_CLASS_NAME_LEN], int* count) {
    collect_all_attrs_inner(class_name, attrs, count, 0);
}

/* 带类名的对象创建 */
void dv_class_new_named(LightValue* result, const char* class_name) {
    if (!result || !class_name || !class_name[0]) {
        dv_str(result, "");
        return;
    }
    
    char safe_name[MAX_CLASS_NAME_LEN];
    size_t name_len = strlen(class_name);
    if (name_len > MAX_CLASS_NAME_LEN - 1) name_len = MAX_CLASS_NAME_LEN - 1;
    memcpy(safe_name, class_name, name_len);
    safe_name[name_len] = '\0';
    
    /* 收集所有属性 */
    char all_attrs[MAX_ATTRS_PER_CLASS][MAX_CLASS_NAME_LEN];
    int num_all_attrs = 0;
    memset(all_attrs, 0, sizeof(all_attrs));
    collect_all_attrs(safe_name, all_attrs, &num_all_attrs);
    
    /* 计算字符串长度：
       "obj:__class__\x1fClassName\x1fattr1\x1f\x1fattr2\x1f\x1f..."
    */
    size_t total_len = strlen(OBJ_PREFIX) + CLASS_FIELD_PREFIX_LEN + 1 + name_len + 1; /* "__class__" + \x1f + class_name + \x1f */
    for (int i = 0; i < num_all_attrs; i++) {
        total_len += strlen(all_attrs[i]) + 2; /* attr + \x1f + \x1f */
    }
    total_len += 1; /* 终止符 */
    
    char* buf = (char*)malloc(total_len);
    if (!buf) {
        dv_str(result, "");
        return;
    }
    
    /* 构建对象字符串 */
    size_t pos = 0;
    memcpy(buf + pos, OBJ_PREFIX, strlen(OBJ_PREFIX));
    pos += strlen(OBJ_PREFIX);
    
    /* 添加 __class__ 字段 */
    memcpy(buf + pos, CLASS_FIELD_PREFIX, CLASS_FIELD_PREFIX_LEN);
    pos += CLASS_FIELD_PREFIX_LEN;
    buf[pos++] = '\x1F';
    memcpy(buf + pos, safe_name, name_len);
    pos += name_len;
    buf[pos++] = '\x1F';
    
    /* 添加所有属性，初始值为空 */
    for (int i = 0; i < num_all_attrs; i++) {
        memcpy(buf + pos, all_attrs[i], strlen(all_attrs[i]));
        pos += strlen(all_attrs[i]);
        buf[pos++] = '\x1F';
        buf[pos++] = '\x1F';
    }
    
    buf[pos] = '\0';
    
    result->type = 3;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = buf;
    result->boolean = 0;
}

/* 获取对象类名 */
void dv_get_class_name(LightValue* obj, char* buf, int buf_size) {
    if (!buf || buf_size <= 0) return;
    buf[0] = '\0';
    
    if (!obj || obj->type != 3 || !obj->str) return;
    if (strncmp(obj->str, OBJ_PREFIX, strlen(OBJ_PREFIX)) != 0) return;
    
    const char* p = obj->str + strlen(OBJ_PREFIX);
    
    /* 构建 "__class__\x1f" 用于比较 */
    char class_field[CLASS_FIELD_PREFIX_LEN + 2];
    memcpy(class_field, CLASS_FIELD_PREFIX, CLASS_FIELD_PREFIX_LEN);
    class_field[CLASS_FIELD_PREFIX_LEN] = '\x1f';
    class_field[CLASS_FIELD_PREFIX_LEN + 1] = '\0';
    size_t class_field_len = CLASS_FIELD_PREFIX_LEN + 1;
    
    if (strncmp(p, class_field, class_field_len) != 0) {
        return;
    }
    
    const char* class_start = p + class_field_len;
    const char* end = strchr(class_start, '\x1F');
    if (!end) end = class_start + strlen(class_start);
    
    size_t len = end - class_start;
    if (len > (size_t)(buf_size - 1)) len = (size_t)(buf_size - 1);
    memcpy(buf, class_start, len);
    buf[len] = '\0';
}

/* 方法函数指针类型 */
typedef void (*LightMethodFunc)(LightValue* result, LightValue* self, LightValue* args, int num_args);

/* 调用对象方法 */
void dv_call_method(LightValue* result, LightValue* obj, const char* method_name, LightValue* args, int num_args) {
    if (!result || !obj || !method_name) {
        if (result) dv_null(result);
        return;
    }
    
    char class_name[MAX_CLASS_NAME_LEN];
    dv_get_class_name(obj, class_name, sizeof(class_name));
    
    if (!class_name[0]) {
        dv_null(result);
        return;
    }
    
    void* func_ptr = dv_find_method(class_name, method_name);
    if (!func_ptr) {
        dv_null(result);
        return;
    }
    
    LightMethodFunc method = (LightMethodFunc)func_ptr;
    dv_null(result);
    method(result, obj, args, num_args);
}

/* 调用父类方法（从指定类的父类开始查找） */
void dv_call_super_method(LightValue* result, LightValue* obj, const char* class_name, const char* method_name, LightValue* args, int num_args) {
    if (!result || !obj || !class_name || !method_name) {
        if (result) dv_null(result);
        return;
    }
    
    LightClassInfo* cls = dv_find_class(class_name);
    if (!cls || cls->super_name[0] == '\0') {
        dv_null(result);
        return;
    }
    
    void* func_ptr = dv_find_method(cls->super_name, method_name);
    if (!func_ptr) {
        dv_null(result);
        return;
    }
    
    LightMethodFunc method = (LightMethodFunc)func_ptr;
    dv_null(result);
    method(result, obj, args, num_args);
}

/* 内部辅助：递归查找方法及类型（带深度限制） */
static void* dv_find_method_with_flag_inner(const char* class_name, const char* method_name, int* out_flag, int depth) {
    if (!class_name || !method_name) return NULL;
    if (depth > MAX_INHERIT_DEPTH) return NULL;
    
    LightClassInfo* cls = dv_find_class(class_name);
    if (!cls) return NULL;
    
    /* 在当前类中查找 */
    for (int i = 0; i < cls->num_methods; i++) {
        if (strcmp(cls->method_names[i], method_name) == 0) {
            if (out_flag) *out_flag = cls->method_flags[i];
            return cls->method_ptrs[i];
        }
    }
    
    /* 递归查找父类 */
    if (cls->super_name[0] != '\0') {
        return dv_find_method_with_flag_inner(cls->super_name, method_name, out_flag, depth + 1);
    }
    
    return NULL;
}

/* 查找方法并返回类型，找不到返回 NULL */
static void* dv_find_method_with_flag(const char* class_name, const char* method_name, int* out_flag) {
    return dv_find_method_with_flag_inner(class_name, method_name, out_flag, 0);
}

/* 类方法函数指针类型：第一个参数是类名（字符串LightValue*） */
typedef void (*LightClassMethodFunc)(LightValue* result, LightValue* cls_val, LightValue* args, int num_args);

/* 静态方法函数指针类型：没有 self/cls 参数 */
typedef void (*LightStaticMethodFunc)(LightValue* result, LightValue* args, int num_args);

/* 调用类方法（通过类名调用） */
void dv_call_class_method(LightValue* result, const char* class_name, const char* method_name, LightValue* args, int num_args) {
    if (!result || !class_name || !method_name) {
        if (result) dv_null(result);
        return;
    }
    
    int method_flag = 0;
    void* func_ptr = dv_find_method_with_flag(class_name, method_name, &method_flag);
    if (!func_ptr) {
        dv_null(result);
        return;
    }
    
    /* 构建类值（用字符串表示类对象，内容为类名） */
    LightValue cls_val;
    dv_str(&cls_val, class_name);
    
    if (method_flag == 1) {
        /* 类方法：签名 void func(result, cls_val, args, num_args) */
        LightClassMethodFunc method = (LightClassMethodFunc)func_ptr;
        dv_null(result);
        method(result, &cls_val, args, num_args);
    } else if (method_flag == 2) {
        /* 静态方法：签名 void func(result, args, num_args) */
        LightStaticMethodFunc method = (LightStaticMethodFunc)func_ptr;
        dv_null(result);
        method(result, args, num_args);
    } else {
        /* 实例方法不能通过类名直接调用，返回空 */
        dv_null(result);
    }
    
    dv_free(&cls_val);
}

/* 调用静态方法（通过类名调用） */
void dv_call_static_method(LightValue* result, const char* class_name, const char* method_name, LightValue* args, int num_args) {
    if (!result || !class_name || !method_name) {
        if (result) dv_null(result);
        return;
    }
    
    int method_flag = 0;
    void* func_ptr = dv_find_method_with_flag(class_name, method_name, &method_flag);
    if (!func_ptr) {
        dv_null(result);
        return;
    }
    
    if (method_flag == 2) {
        /* 静态方法：签名 void func(result, args, num_args) */
        LightStaticMethodFunc method = (LightStaticMethodFunc)func_ptr;
        dv_null(result);
        method(result, args, num_args);
    } else if (method_flag == 1) {
        /* 类方法也可以通过静态方式调用，传入类名 */
        LightValue cls_val;
        dv_str(&cls_val, class_name);
        LightClassMethodFunc method = (LightClassMethodFunc)func_ptr;
        dv_null(result);
        method(result, &cls_val, args, num_args);
        dv_free(&cls_val);
    } else {
        /* 实例方法不能通过类名直接调用，返回空 */
        dv_null(result);
    }
}

/* ================================================================
 * 运算符重载支持
 * ================================================================ */

int dv_is_object(LightValue* v) {
    if (!v || v->type != 3 || !v->str) return 0;
    return strncmp(v->str, OBJ_PREFIX, strlen(OBJ_PREFIX)) == 0;
}

static int dv_try_operator_overload(LightValue* result, LightValue* a, LightValue* b, const char* op_name_cn, const char* op_name_en) {
    if (!dv_is_object(a)) return 0;
    
    char class_name[MAX_CLASS_NAME_LEN];
    dv_get_class_name(a, class_name, sizeof(class_name));
    if (!class_name[0]) return 0;
    
    void* func_ptr = dv_find_method(class_name, op_name_cn);
    if (!func_ptr) {
        func_ptr = dv_find_method(class_name, op_name_en);
    }
    if (!func_ptr) return 0;
    
    LightValue args[1];
    dv_clone(&args[0], b);
    
    LightMethodFunc method = (LightMethodFunc)func_ptr;
    method(result, a, args, 1);
    
    dv_free(&args[0]);
    return 1;
}

void dv_add(LightValue* result, LightValue* a, LightValue* b) {
    if (dv_try_operator_overload(result, a, b, "加", "__add__")) {
        return;
    }
    dv_add_default(result, a, b);
}

void dv_sub(LightValue* result, LightValue* a, LightValue* b) {
    if (dv_try_operator_overload(result, a, b, "减", "__sub__")) {
        return;
    }
    dv_sub_default(result, a, b);
}

void dv_mul(LightValue* result, LightValue* a, LightValue* b) {
    if (dv_try_operator_overload(result, a, b, "乘", "__mul__")) {
        return;
    }
    dv_mul_default(result, a, b);
}

void dv_div(LightValue* result, LightValue* a, LightValue* b) {
    if (dv_try_operator_overload(result, a, b, "除", "__div__")) {
        return;
    }
    dv_div_default(result, a, b);
}

/* ================================================================
 * 类型判断与 isinstance
 * ================================================================ */

static int dv_isinstance_inner(const char* class_name, const char* target_class, int depth) {
    if (!class_name || !target_class) return 0;
    if (depth > MAX_INHERIT_DEPTH) return 0;
    
    if (strcmp(class_name, target_class) == 0) {
        return 1;
    }
    
    LightClassInfo* cls = dv_find_class(class_name);
    if (!cls) return 0;
    
    if (cls->super_name[0] != '\0') {
        return dv_isinstance_inner(cls->super_name, target_class, depth + 1);
    }
    
    return 0;
}

int dv_isinstance(LightValue* obj, const char* class_name) {
    if (!obj || !class_name || !class_name[0]) return 0;
    
    if (obj->type != 3 || !obj->str) return 0;
    if (strncmp(obj->str, OBJ_PREFIX, strlen(OBJ_PREFIX)) != 0) return 0;
    
    char obj_class[MAX_CLASS_NAME_LEN];
    dv_get_class_name(obj, obj_class, sizeof(obj_class));
    
    if (!obj_class[0]) return 0;
    
    return dv_isinstance_inner(obj_class, class_name, 0);
}

void dv_get_type_name(LightValue* obj, char* buf, int buf_size) {
    if (!buf || buf_size <= 0) return;
    buf[0] = '\0';
    
    if (!obj) return;
    
    switch (obj->type) {
        case 0:
            strncpy(buf, "NoneType", buf_size - 1);
            buf[buf_size - 1] = '\0';
            break;
        case 1:
            strncpy(buf, "int", buf_size - 1);
            buf[buf_size - 1] = '\0';
            break;
        case 2:
            strncpy(buf, "float", buf_size - 1);
            buf[buf_size - 1] = '\0';
            break;
        case 3:
            if (obj->str && strncmp(obj->str, OBJ_PREFIX, strlen(OBJ_PREFIX)) == 0) {
                dv_get_class_name(obj, buf, buf_size);
            } else if (obj->str && strncmp(obj->str, "list:", 5) == 0) {
                strncpy(buf, "list", buf_size - 1);
                buf[buf_size - 1] = '\0';
            } else {
                strncpy(buf, "str", buf_size - 1);
                buf[buf_size - 1] = '\0';
            }
            break;
        case 4:
            strncpy(buf, "list", buf_size - 1);
            buf[buf_size - 1] = '\0';
            break;
        case 5:
            strncpy(buf, "bool", buf_size - 1);
            buf[buf_size - 1] = '\0';
            break;
        case 6:
            dv_get_class_name(obj, buf, buf_size);
            break;
        case 7:
            strncpy(buf, "dict", buf_size - 1);
            buf[buf_size - 1] = '\0';
            break;
        case 8: {
            /* REF：解引用一层返回底层类型名 */
            LightValue* inner = (LightValue*)obj->str;
            if (inner) dv_get_type_name(inner, buf, buf_size);
            else { strncpy(buf, "NoneType", buf_size - 1); buf[buf_size - 1] = '\0'; }
            break;
        }
        default:
            strncpy(buf, "未知", buf_size - 1);
            buf[buf_size - 1] = '\0';
            break;
    }
}

/* ================================================================
 * 协程/异步支持
 * ================================================================ */

/* 协程状态枚举 */
#define DV_CORO_READY    0  /* 就绪，可运行 */
#define DV_CORO_RUNNING  1  /* 运行中 */
#define DV_CORO_SUSPENDED 2 /* 已挂起（等待中） */
#define DV_CORO_DONE     3  /* 已完成 */
#define DV_CORO_ERROR    4  /* 出错 */

/* 协程函数指针类型：
   void coro_func(LightValue* result, void* coro_handle, LightValue* args, int num_args)
   
   协程函数通过 coro_handle 中的 resume_point 控制执行位置（Duff's device）。
*/
typedef void (*LightCoroFunc)(LightValue*, void*, LightValue*, int);

/* 最大协程数 */
#define DV_MAX_COROUTINES 4096

/* 协程句柄结构体 */
typedef struct LightCoroutine {
    int state;             /* 协程状态：DV_CORO_* */
    int resume_point;      /* 恢复点（Duff's device 的 case 标签） */
    LightCoroFunc func;     /* 协程函数指针 */
    LightValue result;      /* 返回值/当前结果 */
    LightValue* args;       /* 参数数组（堆分配） */
    int num_args;          /* 参数数量 */
    /* 局部变量槽位（用于保存挂起时的局部变量状态） */
    LightValue* locals;     /* 局部变量数组（堆分配） */
    int num_locals;        /* 局部变量数量 */
    /* 等待的 Future（如果在等待某个异步操作） */
    struct LightFuture* waiting_for;
    /* 关联的 Future（当协程完成时自动完成此 future） */
    struct LightFuture* future;
    /* 调度器链表指针 */
    struct LightCoroutine* next;
} LightCoroutine;

/* Future/Promise 结构体 */
typedef struct LightFuture {
    int ready;             /* 是否已完成 */
    LightValue result;      /* 结果值 */
    int has_error;         /* 是否有错误 */
    char error_msg[256];   /* 错误消息 */
    /* 等待这个 future 的协程链表 */
    LightCoroutine* waiters;
} LightFuture;

/* 协程调度器 */
typedef struct LightScheduler {
    LightCoroutine* run_queue;   /* 可运行队列 */
    LightCoroutine* all_coros;   /* 所有协程（用于清理） */
    int num_coros;              /* 当前协程数 */
} LightScheduler;

/* 全局调度器实例 */
static LightScheduler g_scheduler = { NULL, NULL, 0 };

/* 前置声明 */
LightFuture* dv_future_create(void);
void dv_future_complete(LightFuture* f, LightValue* result);

/* 内部：创建协程 */
LightCoroutine* dv_coro_create(LightCoroFunc func, LightValue* args, int num_args, int num_locals) {
    if (g_scheduler.num_coros >= DV_MAX_COROUTINES) {
        return NULL;
    }
    LightCoroutine* coro = (LightCoroutine*)malloc(sizeof(LightCoroutine));
    if (!coro) return NULL;
    
    coro->state = DV_CORO_READY;
    coro->resume_point = 0;
    coro->func = func;
    dv_null(&coro->result);
    
    /* 复制参数 */
    coro->num_args = num_args;
    if (num_args > 0 && args) {
        coro->args = (LightValue*)malloc(sizeof(LightValue) * num_args);
        if (coro->args) {
            memcpy(coro->args, args, sizeof(LightValue) * num_args);
        }
    } else {
        coro->args = NULL;
    }
    
    /* 分配局部变量槽位 */
    coro->num_locals = num_locals;
    if (num_locals > 0) {
        coro->locals = (LightValue*)malloc(sizeof(LightValue) * num_locals);
        if (coro->locals) {
            for (int i = 0; i < num_locals; i++) {
                dv_null(&coro->locals[i]);
            }
        }
    } else {
        coro->locals = NULL;
    }
    
    coro->waiting_for = NULL;
    coro->future = dv_future_create();
    coro->next = NULL;
    
    /* 添加到调度器的可运行队列 */
    if (g_scheduler.run_queue == NULL) {
        g_scheduler.run_queue = coro;
    } else {
        LightCoroutine* c = g_scheduler.run_queue;
        while (c->next) c = c->next;
        c->next = coro;
    }
    
    g_scheduler.num_coros++;
    
    return coro;
}

/* 内部：恢复协程（执行一步） */
static int dv_coro_resume(LightCoroutine* coro) {
    if (!coro || coro->state == DV_CORO_DONE || coro->state == DV_CORO_ERROR) {
        return -1;
    }
    
    coro->state = DV_CORO_RUNNING;
    
    /* 调用协程函数，它会根据 resume_point 从正确的位置继续 */
    coro->func(&coro->result, coro, coro->args, coro->num_args);
    
    if (coro->state == DV_CORO_RUNNING) {
        /* 函数返回了但没挂起，说明执行完毕 */
        coro->state = DV_CORO_DONE;
    }
    
    return 0;
}

/* 创建 Future */
LightFuture* dv_future_create() {
    LightFuture* f = (LightFuture*)malloc(sizeof(LightFuture));
    if (!f) return NULL;
    f->ready = 0;
    dv_null(&f->result);
    f->has_error = 0;
    f->error_msg[0] = '\0';
    f->waiters = NULL;
    return f;
}

/* 完成 Future（设置结果） */
void dv_future_complete(LightFuture* f, LightValue* result) {
    if (!f || f->ready) return;
    
    dv_clone(&f->result, result);
    f->ready = 1;
    
    /* 唤醒所有等待的协程 */
    LightCoroutine* c = f->waiters;
    while (c) {
        LightCoroutine* next = c->next;
        c->state = DV_CORO_READY;
        /* 注意：不清除 waiting_for，因为 dv_coro_get_await_result 需要从中读取结果 */
        c->next = NULL;
        /* 添加回可运行队列 */
        if (g_scheduler.run_queue == NULL) {
            g_scheduler.run_queue = c;
        } else {
            LightCoroutine* r = g_scheduler.run_queue;
            while (r->next) r = r->next;
            r->next = c;
        }
        c = next;
    }
    f->waiters = NULL;
}

/* 协程挂起自己，等待另一个协程完成
 * 注意：第二个参数是目标协程（LightCoroutine*），不是 LightFuture*
 * 这是为了支持 "await 另一个协程" 的常见模式
 */
void dv_coro_await(LightCoroutine* coro, LightCoroutine* target) {
    if (!coro || !target) return;
    
    /* 获取目标协程关联的 future */
    LightFuture* future = target->future;
    if (!future) return;
    
    if (future->ready) {
        /* 目标已经完成，直接返回（不挂起） */
        coro->waiting_for = future;
        return;
    }
    
    /* 如果目标还未运行，确保它会被加入 run_queue */
    if (target->state == DV_CORO_READY) {
        /* 检查是否已在 run_queue 中 */
        int in_queue = 0;
        LightCoroutine* c = g_scheduler.run_queue;
        while (c) {
            if (c == target) {
                in_queue = 1;
                break;
            }
            c = c->next;
        }
        if (!in_queue) {
            target->next = NULL;
            if (g_scheduler.run_queue == NULL) {
                g_scheduler.run_queue = target;
            } else {
                LightCoroutine* last = g_scheduler.run_queue;
                while (last->next) last = last->next;
                last->next = target;
            }
        }
    }
    
    /* 挂起当前协程，等待 future */
    coro->state = DV_CORO_SUSPENDED;
    coro->waiting_for = future;
    
    /* 添加到 future 的等待链表 */
    coro->next = future->waiters;
    future->waiters = coro;
}

/* 运行调度器（直到没有可运行的协程） */
void dv_scheduler_run() {
    while (g_scheduler.run_queue) {
        /* 取出第一个协程 */
        LightCoroutine* coro = g_scheduler.run_queue;
        g_scheduler.run_queue = coro->next;
        coro->next = NULL;
        
        /* 恢复执行 */
        dv_coro_resume(coro);
    }
}

/* 启动协程并运行到完成（阻塞式，用于顶层异步调用） */
void dv_coro_run_to_completion(LightCoroutine* coro) {
    if (!coro) return;
    
    /* 如果协程已经完成，直接返回 */
    if (coro->state == DV_CORO_DONE || coro->state == DV_CORO_ERROR) {
        return;
    }
    
    /* 如果协程是 READY 状态且不在 run_queue 中，把它加进去 */
    if (coro->state == DV_CORO_READY) {
        /* 检查是否已经在 run_queue 中（简单检查：遍历队列） */
        int in_queue = 0;
        LightCoroutine* c = g_scheduler.run_queue;
        while (c) {
            if (c == coro) {
                in_queue = 1;
                break;
            }
            c = c->next;
        }
        if (!in_queue) {
            /* 添加到队列尾部 */
            coro->next = NULL;
            if (g_scheduler.run_queue == NULL) {
                g_scheduler.run_queue = coro;
            } else {
                LightCoroutine* last = g_scheduler.run_queue;
                while (last->next) last = last->next;
                last->next = coro;
            }
        }
    }
    
    dv_scheduler_run();
}

/* 获取协程结果（必须在完成后调用） */
LightValue* dv_coro_get_result(LightCoroutine* coro) {
    if (!coro) return NULL;
    return &coro->result;
}

/* 获取协程局部变量的指针（用于跨 await 持久化局部变量）
 * 返回 coro->locals[index] 的指针
 */
LightValue* dv_coro_get_local(LightCoroutine* coro, int index) {
    if (!coro || !coro->locals || index < 0 || index >= coro->num_locals) {
        return NULL;
    }
    return &coro->locals[index];
}

/* 获取协程参数的指针
 * 返回 coro->args[index] 的指针
 */
LightValue* dv_coro_get_arg(LightCoroutine* coro, int index) {
    if (!coro || !coro->args || index < 0 || index >= coro->num_args) {
        return NULL;
    }
    return &coro->args[index];
}

/* 获取 await 的结果：从 coro->waiting_for->result 复制到 out */
void dv_coro_get_await_result(LightCoroutine* coro, LightValue* out) {
    if (!coro || !out) return;
    if (coro->waiting_for && coro->waiting_for->ready) {
        dv_clone(out, &coro->waiting_for->result);
    } else {
        dv_null(out);
    }
    /* 清除 waiting_for 引用 */
    coro->waiting_for = NULL;
}

/* 设置协程结果 */
void dv_coro_set_result(LightCoroutine* coro, LightValue* val) {
    if (!coro || !val) return;
    dv_clone(&coro->result, val);
    /* 同时完成关联的 future（唤醒等待者） */
    if (coro->future && !coro->future->ready) {
        dv_future_complete(coro->future, val);
    }
}

/* 检查协程是否完成 */
int dv_coro_is_done(LightCoroutine* coro) {
    return coro && (coro->state == DV_CORO_DONE || coro->state == DV_CORO_ERROR);
}

/* 把 LightValue 包装成 Future（同步值 → 已完成的 Future） */
LightFuture* dv_future_from_value(LightValue* val) {
    LightFuture* f = dv_future_create();
    if (f && val) {
        dv_clone(&f->result, val);
        f->ready = 1;
    }
    return f;
}

/* ================================================================
 * B1: 网络/Socket 原语
 * ================================================================ */

#ifdef _WIN32
static int g_winsock_initialized = 0;

static void dv_winsock_init(void) {
    if (!g_winsock_initialized) {
        WSADATA wsa;
        WSAStartup(MAKEWORD(2, 2), &wsa);
        g_winsock_initialized = 1;
    }
}

/* MSVC 没有 __attribute__((constructor))，用 CRT 段注册 */
#if defined(_MSC_VER)
#pragma section(".CRT$XCU", read)
static void __cdecl dv_winsock_ctor(void) { dv_winsock_init(); }
__declspec(allocate(".CRT$XCU")) void (*dv_winsock_ptr)(void) = dv_winsock_ctor;
#endif
#endif /* _WIN32 */

static char g_socket_error_msg[256] = {0};
static int g_socket_error_code = 0;

int dv_socket_create(int domain, int type) {
#ifdef _WIN32
    dv_winsock_init();
#endif
    int fd = (int)socket(domain, type, 0);
    if (fd < 0) {
#ifdef _WIN32
        g_socket_error_code = WSAGetLastError();
#else
        g_socket_error_code = errno;
#endif
    }
    return fd;
}

int dv_socket_connect(int fd, const char* host, int port) {
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons((u_short)port);

    /* 尝试直接 inet_addr，失败则 getaddrinfo */
    unsigned long ip = inet_addr(host);
    if (ip == INADDR_NONE) {
        struct hostent* he = gethostbyname(host);
        if (!he) {
            g_socket_error_code = -1;
            snprintf(g_socket_error_msg, sizeof(g_socket_error_msg), "无法解析主机: %s", host);
            return -1;
        }
        memcpy(&addr.sin_addr, he->h_addr_list[0], he->h_length);
    } else {
        addr.sin_addr.s_addr = ip;
    }

    int ret = connect(fd, (struct sockaddr*)&addr, sizeof(addr));
    if (ret < 0) {
#ifdef _WIN32
        g_socket_error_code = WSAGetLastError();
        snprintf(g_socket_error_msg, sizeof(g_socket_error_msg), "connect: errno %d", g_socket_error_code);
#else
        g_socket_error_code = errno;
        snprintf(g_socket_error_msg, sizeof(g_socket_error_msg), "connect: errno %d (%s)", errno, strerror(errno));
#endif
    }
    return ret;
}

int dv_socket_bind(int fd, const char* host, int port) {
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons((u_short)port);
    addr.sin_addr.s_addr = (host && host[0]) ? inet_addr(host) : htonl(INADDR_ANY);
    return bind(fd, (struct sockaddr*)&addr, sizeof(addr));
}

int dv_socket_listen(int fd, int backlog) {
    return listen(fd, backlog);
}

int dv_socket_accept(int fd) {
    struct sockaddr_in addr;
    socklen_t len = sizeof(addr);
    return (int)accept(fd, (struct sockaddr*)&addr, &len);
}

int dv_socket_send(int fd, const char* data) {
    if (!data) return 0;
    int len = (int)strlen(data);
    return (int)send(fd, data, len, 0);
}

void dv_socket_recv(LightValue* result, int fd, int max_bytes) {
    if (!result) return;
    if (max_bytes <= 0) max_bytes = 4096;
    char* buf = (char*)malloc(max_bytes + 1);
    if (!buf) { dv_null(result); return; }
    int n = (int)recv(fd, buf, max_bytes, 0);
    if (n <= 0) {
        free(buf);
        dv_str(result, "");
        return;
    }
    buf[n] = '\0';
    dv_str(result, buf);
    free(buf);
}

int dv_socket_close(int fd) {
#ifdef _WIN32
    return closesocket(fd);
#else
    return close(fd);
#endif
}

int dv_socket_shutdown(int fd, int how) {
    return shutdown(fd, how);
}

int dv_socket_set_nonblocking(int fd, int enable) {
#ifdef _WIN32
    u_long mode = enable ? 1 : 0;
    return ioctlsocket(fd, FIONBIO, &mode);
#else
    int flags = fcntl(fd, F_GETFL, 0);
    if (flags < 0) return -1;
    if (enable) flags |= O_NONBLOCK; else flags &= ~O_NONBLOCK;
    return fcntl(fd, F_SETFL, flags);
#endif
}

const char* dv_socket_last_error(void) {
    return g_socket_error_msg;
}

int dv_socket_last_error_code(void) {
    return g_socket_error_code;
}

const char* dv_socket_get_peer_addr(int fd) {
    static char buf[64];
    struct sockaddr_in addr;
    socklen_t len = sizeof(addr);
    if (getpeername(fd, (struct sockaddr*)&addr, &len) == 0) {
        snprintf(buf, sizeof(buf), "%s:%d", inet_ntoa(addr.sin_addr), ntohs(addr.sin_port));
    } else {
        buf[0] = '\0';
    }
    return buf;
}

/* ================================================================
 * B2: IO 多路复用 (WSAPoll / poll，select 为编译期 fallback)
 *
 * 后端选择是**编译期**的，不做运行期动态选择（运行期选择会引入难查的
 * 平台差异）：
 *   - Windows           → WSAPoll（Vista+）
 *   - POSIX             → poll
 *   - -DDV_POLLER_FORCE_SELECT → select（保留的 fallback）
 *
 * 上限：WSAPoll/poll 两条路径**没有 FD_SETSIZE 硬上限**，注册表按需
 * 翻倍增长。select fallback 仍受 FD_SETSIZE 限制，超限时
 * dv_poller_register 返回 -1 并写 g_poller_error，**绝不静默丢 fd**。
 * ================================================================ */

#define DV_POLL_READ  1
#define DV_POLL_WRITE 2

/* 兼容旧口径：初始容量，不再是硬上限（select fallback 除外） */
#define DV_POLLER_MAX 256

#if defined(DV_POLLER_FORCE_SELECT)
#  define DV_POLLER_BACKEND_SELECT 1
#  define DV_POLLER_BACKEND_NAME "select"
#elif defined(_WIN32)
#  define DV_POLLER_BACKEND_WSAPOLL 1
#  define DV_POLLER_BACKEND_NAME "WSAPoll"
#else
#  define DV_POLLER_BACKEND_POLL 1
#  define DV_POLLER_BACKEND_NAME "poll"
#endif

#if defined(DV_POLLER_BACKEND_POLL)
#include <poll.h>
#endif

/* 三条后端的字段/标志名对齐 */
#if defined(DV_POLLER_BACKEND_WSAPOLL)
#  define SOCKET_LIKE_FD    SOCKET
#  define POLLRDNORM_COMPAT POLLRDNORM
#  define POLLWRNORM_COMPAT POLLWRNORM
#  define POLLHUP_COMPAT    POLLHUP
#  define POLLERR_COMPAT    POLLERR
#  define POLLNVAL_COMPAT   POLLNVAL
#elif defined(DV_POLLER_BACKEND_POLL)
#  define SOCKET_LIKE_FD    int
#  define POLLRDNORM_COMPAT (POLLIN | POLLRDNORM)
#  define POLLWRNORM_COMPAT (POLLOUT | POLLWRNORM)
#  define POLLHUP_COMPAT    POLLHUP
#  define POLLERR_COMPAT    POLLERR
#  define POLLNVAL_COMPAT   POLLNVAL
#endif


typedef struct {
    int* registered_fds;       /* 按需增长 */
    int* registered_events;
    int num_registered;
    int capacity;
#if defined(DV_POLLER_BACKEND_WSAPOLL)
    WSAPOLLFD* pfds;
    int pfds_capacity;
#elif defined(DV_POLLER_BACKEND_POLL)
    struct pollfd* pfds;
    int pfds_capacity;
#else
    fd_set read_fds;
    fd_set write_fds;
    int max_fd;
#endif
} LightPoller;

static char g_poller_error[256] = {0};

const char* dv_poller_last_error(void) {
    return g_poller_error;
}

const char* dv_poller_backend(void) {
    return DV_POLLER_BACKEND_NAME;
}

LightPoller* dv_poller_create(void) {
    LightPoller* p = (LightPoller*)calloc(1, sizeof(LightPoller));
    if (!p) return NULL;
    p->capacity = DV_POLLER_MAX;
    p->registered_fds = (int*)calloc(p->capacity, sizeof(int));
    p->registered_events = (int*)calloc(p->capacity, sizeof(int));
    if (!p->registered_fds || !p->registered_events) {
        free(p->registered_fds);
        free(p->registered_events);
        free(p);
        return NULL;
    }
    return p;
}

/* 把注册表扩到至少 need 个槽位。成功返回 0，失败返回 -1（并写错误文本） */
static int dv_poller_grow(LightPoller* p, int need) {
    if (need <= p->capacity) return 0;
    int cap = p->capacity ? p->capacity : DV_POLLER_MAX;
    while (cap < need) cap *= 2;
    /* 两步 realloc：先 realloc 到临时指针，都成功才 swap + 更新 capacity。
     * 避免第二个 realloc 失败时 registered_fds 已更新但 capacity 未更新，
     * 导致后续操作读写不匹配的缓冲区。 */
    int* nf = (int*)realloc(p->registered_fds, (size_t)cap * sizeof(int));
    int* ne = nf ? (int*)realloc(p->registered_events, (size_t)cap * sizeof(int)) : NULL;
    if (!nf || !ne) {
        /* realloc 失败时原指针仍有效，不需要 free 原来的；
         * 但 nf 可能在 ne 失败前已分配，需要释放 */
        free(nf);
        free(ne);
        snprintf(g_poller_error, sizeof(g_poller_error),
                 "poller 扩容失败（目标 %d 项），拒绝注册而不静默丢 fd", cap);
        return -1;
    }
    p->registered_fds = nf;
    p->registered_events = ne;
    p->capacity = cap;
    return 0;
}

int dv_poller_register(LightPoller* p, int fd, int events) {
    if (!p) {
        snprintf(g_poller_error, sizeof(g_poller_error), "poller 为空，无法注册 fd %d", fd);
        return -1;
    }
    if (fd < 0) {
        snprintf(g_poller_error, sizeof(g_poller_error), "非法 fd %d，拒绝注册", fd);
        return -1;
    }
    /* 检查是否已注册 */
    for (int i = 0; i < p->num_registered; i++) {
        if (p->registered_fds[i] == fd) {
            p->registered_events[i] = events;
            return 0;
        }
    }
#if defined(DV_POLLER_BACKEND_SELECT)
    /* select fallback：FD_SETSIZE 是硬上限，超限必须明确报错而不是静默丢 */
    if (p->num_registered >= (int)FD_SETSIZE) {
        snprintf(g_poller_error, sizeof(g_poller_error),
                 "select 后端已达 FD_SETSIZE=%d 上限，拒绝注册 fd %d（改用 WSAPoll/poll 后端）",
                 (int)FD_SETSIZE, fd);
        return -1;
    }
#ifndef _WIN32
    /* POSIX select：fd 值本身必须 < FD_SETSIZE，否则 FD_SET 越界写 */
    if (fd >= (int)FD_SETSIZE) {
        snprintf(g_poller_error, sizeof(g_poller_error),
                 "select 后端 fd %d >= FD_SETSIZE=%d，FD_SET 会越界，拒绝注册",
                 fd, (int)FD_SETSIZE);
        return -1;
    }
#endif
#endif
    if (dv_poller_grow(p, p->num_registered + 1) != 0) return -1;
    p->registered_fds[p->num_registered] = fd;
    p->registered_events[p->num_registered] = events;
    p->num_registered++;
    return 0;
}

int dv_poller_unregister(LightPoller* p, int fd) {
    if (!p) return -1;
    for (int i = 0; i < p->num_registered; i++) {
        if (p->registered_fds[i] == fd) {
            /* 用最后一个元素填补 */
            p->num_registered--;
            p->registered_fds[i] = p->registered_fds[p->num_registered];
            p->registered_events[i] = p->registered_events[p->num_registered];
            return 0;
        }
    }
    return -1;
}

int dv_poller_count(LightPoller* p) {
    return p ? p->num_registered : -1;
}

/* 带容量的等待：out_capacity 是 out_fds/out_events 的槽位数。
 * 就绪数超过容量时**不静默截断**：返回 -1 并写错误文本。 */
int dv_poller_wait_n(LightPoller* p, int timeout_ms, int* out_fds, int* out_events,
                     int out_capacity) {
    if (!p || p->num_registered == 0) return 0;
    if (!out_fds || !out_events || out_capacity <= 0) {
        snprintf(g_poller_error, sizeof(g_poller_error), "dv_poller_wait_n 输出缓冲非法");
        return -1;
    }

#if defined(DV_POLLER_BACKEND_SELECT)
    FD_ZERO(&p->read_fds);
    FD_ZERO(&p->write_fds);
#ifndef _WIN32
    p->max_fd = -1;
#endif
    for (int i = 0; i < p->num_registered; i++) {
        int fd = p->registered_fds[i];
        int events = p->registered_events[i];
        if (events & DV_POLL_READ) FD_SET(fd, &p->read_fds);
        if (events & DV_POLL_WRITE) FD_SET(fd, &p->write_fds);
#ifndef _WIN32
        if (fd > p->max_fd) p->max_fd = fd;
#endif
    }
    struct timeval tv;
    struct timeval* ptv = NULL;
    if (timeout_ms >= 0) {
        tv.tv_sec = timeout_ms / 1000;
        tv.tv_usec = (timeout_ms % 1000) * 1000;
        ptv = &tv;
    }
    int ready;
#ifdef _WIN32
    ready = select(0, &p->read_fds, &p->write_fds, NULL, ptv);
#else
    ready = select(p->max_fd + 1, &p->read_fds, &p->write_fds, NULL, ptv);
#endif
    if (ready <= 0) return 0;
    int count = 0;
    for (int i = 0; i < p->num_registered; i++) {
        int fd = p->registered_fds[i];
        int ev = 0;
        if (FD_ISSET(fd, &p->read_fds)) ev |= DV_POLL_READ;
        if (FD_ISSET(fd, &p->write_fds)) ev |= DV_POLL_WRITE;
        if (!ev) continue;
        if (count >= out_capacity) {
            snprintf(g_poller_error, sizeof(g_poller_error),
                     "就绪 fd 数超出输出缓冲容量 %d，拒绝截断上报", out_capacity);
            return -1;
        }
        out_fds[count] = fd;
        out_events[count] = ev;
        count++;
    }
    return count;
#else
    /* WSAPoll / poll 共用路径：pollfd 数组按注册数增长 */
    if (p->pfds_capacity < p->num_registered) {
        int cap = p->pfds_capacity ? p->pfds_capacity : DV_POLLER_MAX;
        while (cap < p->num_registered) cap *= 2;
#if defined(DV_POLLER_BACKEND_WSAPOLL)
        WSAPOLLFD* np = (WSAPOLLFD*)realloc(p->pfds, (size_t)cap * sizeof(WSAPOLLFD));
#else
        struct pollfd* np = (struct pollfd*)realloc(p->pfds, (size_t)cap * sizeof(struct pollfd));
#endif
        if (!np) {
            snprintf(g_poller_error, sizeof(g_poller_error),
                     "pollfd 数组扩容失败（目标 %d 项）", cap);
            return -1;
        }
        p->pfds = np;
        p->pfds_capacity = cap;
    }

    for (int i = 0; i < p->num_registered; i++) {
        p->pfds[i].fd = (SOCKET_LIKE_FD)p->registered_fds[i];
        short ev = 0;
        if (p->registered_events[i] & DV_POLL_READ) ev |= POLLRDNORM_COMPAT;
        if (p->registered_events[i] & DV_POLL_WRITE) ev |= POLLWRNORM_COMPAT;
        p->pfds[i].events = ev;
        p->pfds[i].revents = 0;
    }

    int ready;
#if defined(DV_POLLER_BACKEND_WSAPOLL)
    ready = WSAPoll(p->pfds, (ULONG)p->num_registered, timeout_ms);
#else
    ready = poll(p->pfds, (nfds_t)p->num_registered, timeout_ms);
#endif
    if (ready < 0) {
#ifdef _WIN32
        snprintf(g_poller_error, sizeof(g_poller_error),
                 "%s 失败: errno %d", DV_POLLER_BACKEND_NAME, WSAGetLastError());
#else
        snprintf(g_poller_error, sizeof(g_poller_error),
                 "%s 失败: errno %d (%s)", DV_POLLER_BACKEND_NAME, errno, strerror(errno));
#endif
        return -1;
    }
    if (ready == 0) return 0;

    int count = 0;
    for (int i = 0; i < p->num_registered; i++) {
        short re = p->pfds[i].revents;
        if (!re) continue;
        int ev = 0;
        if (re & (POLLRDNORM_COMPAT | POLLHUP_COMPAT | POLLERR_COMPAT | POLLNVAL_COMPAT))
            ev |= DV_POLL_READ;
        if (re & POLLWRNORM_COMPAT) ev |= DV_POLL_WRITE;
        if (!ev) continue;
        if (count >= out_capacity) {
            snprintf(g_poller_error, sizeof(g_poller_error),
                     "就绪 fd 数超出输出缓冲容量 %d，拒绝截断上报", out_capacity);
            return -1;
        }
        out_fds[count] = p->registered_fds[i];
        out_events[count] = ev;
        count++;
    }
    return count;
#endif
}

/* 兼容旧 ABI：codegen 生成的调用点固定分配 256 槽位的输出数组。
 * wait_n 返回 -1 时表示真正的错误（超容量、poll 失败等），不能静默吞成 0
 * （0 表示"没有就绪"，调用方无法区分）。此处往 stderr 打错误后返回 0，
 * 保持 ABI 兼容但不再静默。 */
int dv_poller_wait(LightPoller* p, int timeout_ms, int* out_fds, int* out_events) {
    int n = dv_poller_wait_n(p, timeout_ms, out_fds, out_events, 256);
    if (n < 0) {
        fprintf(stderr, "dv_poller_wait: %s\n", dv_poller_last_error());
        return 0;
    }
    return n;
}

void dv_poller_destroy(LightPoller* p) {
    if (!p) return;
    free(p->registered_fds);
    free(p->registered_events);
#if !defined(DV_POLLER_BACKEND_SELECT)
    free(p->pfds);
#endif
    free(p);
}

/* ================================================================
 * B3: 事件循环 — 调度器 IO 唤醒 + sleep
 * ================================================================ */

/* IO 等待队列 */
typedef struct LightIOWait {
    int fd;
    int events;
    LightCoroutine* coro;
    struct LightIOWait* next;
} LightIOWait;

/* 定时器链表 */
typedef struct LightTimer {
    int64_t expire_ms;
    LightCoroutine* coro;
    struct LightTimer* next;
} LightTimer;

static LightIOWait* g_io_wait_head = NULL;
static LightTimer* g_timer_head = NULL;
static LightPoller* g_poller = NULL;

static int64_t dv_now_ms(void) {
#ifdef _WIN32
    static LARGE_INTEGER freq = {0};
    if (freq.QuadPart == 0) QueryPerformanceFrequency(&freq);
    LARGE_INTEGER now;
    QueryPerformanceCounter(&now);
    return (int64_t)(now.QuadPart * 1000 / freq.QuadPart);
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (int64_t)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
#endif
}

/* 让当前协程挂起等待 IO
 *
 * 注册失败（poller 满 / 扩容失败 / 非法 fd）时**不静默丢 fd**：
 * 往 stderr 打醒目错误，并把协程直接放回 run_queue，让它继续往下跑
 * （后续 recv 会以自己的错误路径失败），而不是永远挂在等待队列里。 */
void dv_coro_await_io(LightCoroutine* coro, int fd, int events) {
    if (!coro || fd < 0) return;
    if (!g_poller) g_poller = dv_poller_create();
    if (!g_poller) {
        fprintf(stderr, "[光明·事件循环] poller 创建失败，fd %d 无法等待 IO\n", fd);
        coro->state = DV_CORO_READY;
        coro->waiting_for = NULL;
        coro->next = g_scheduler.run_queue;
        g_scheduler.run_queue = coro;
        return;
    }
    if (dv_poller_register(g_poller, fd, events) != 0) {
        fprintf(stderr, "[光明·事件循环] fd %d 注册 poller 失败：%s\n",
                fd, dv_poller_last_error());
        coro->state = DV_CORO_READY;
        coro->waiting_for = NULL;
        coro->next = g_scheduler.run_queue;
        g_scheduler.run_queue = coro;
        return;
    }

    LightIOWait* entry = (LightIOWait*)calloc(1, sizeof(LightIOWait));
    if (!entry) {
        fprintf(stderr, "[光明·事件循环] IO 等待项分配失败，fd %d 放回就绪队列\n", fd);
        dv_poller_unregister(g_poller, fd);
        coro->state = DV_CORO_READY;
        coro->waiting_for = NULL;
        coro->next = g_scheduler.run_queue;
        g_scheduler.run_queue = coro;
        return;
    }
    entry->fd = fd;
    entry->events = events;
    entry->coro = coro;
    entry->next = g_io_wait_head;
    g_io_wait_head = entry;

    coro->state = DV_CORO_SUSPENDED;
    coro->waiting_for = (LightFuture*)entry;
}

/* 让当前协程睡眠 ms 毫秒 */
void dv_coro_sleep(LightCoroutine* coro, int ms) {
    if (!coro || ms <= 0) return;

    LightTimer* timer = (LightTimer*)calloc(1, sizeof(LightTimer));
    if (!timer) return;
    timer->expire_ms = dv_now_ms() + ms;
    timer->coro = coro;
    timer->next = NULL;

    /* 按到期时间插入排序 */
    if (!g_timer_head || timer->expire_ms < g_timer_head->expire_ms) {
        timer->next = g_timer_head;
        g_timer_head = timer;
    } else {
        LightTimer* cur = g_timer_head;
        while (cur->next && cur->next->expire_ms <= timer->expire_ms) {
            cur = cur->next;
        }
        timer->next = cur->next;
        cur->next = timer;
    }

    coro->state = DV_CORO_SUSPENDED;
    coro->waiting_for = (LightFuture*)timer;
}

/* 平台级 sleep（非协程环境） */
void dv_platform_sleep(int ms) {
#ifdef _WIN32
    Sleep(ms);
#else
    struct timespec ts;
    ts.tv_sec = ms / 1000;
    ts.tv_nsec = (ms % 1000) * 1000000;
    nanosleep(&ts, NULL);
#endif
}

/* 处理到期定时器，返回下一个定时器剩余毫秒（-1 表示无定时器） */
static int dv_process_timers(void) {
    if (!g_timer_head) return -1;

    int64_t now = dv_now_ms();
    int count = 0;

    while (g_timer_head && g_timer_head->expire_ms <= now) {
        LightTimer* t = g_timer_head;
        g_timer_head = t->next;

        /* 唤醒协程：放回 run_queue */
        t->coro->state = DV_CORO_READY;
        t->coro->waiting_for = NULL;
        t->coro->next = g_scheduler.run_queue;
        g_scheduler.run_queue = t->coro;
        free(t);
        count++;
    }

    if (g_timer_head) {
        int64_t remaining = g_timer_head->expire_ms - dv_now_ms();
        return remaining > 0 ? (int)remaining : 0;
    }
    return -1;
}

/* 事件循环主函数 */
void dv_scheduler_run_event_loop(void) {
    while (g_scheduler.run_queue || g_io_wait_head || g_timer_head) {
        /* 1. 跑完所有就绪协程 */
        while (g_scheduler.run_queue) {
            LightCoroutine* coro = g_scheduler.run_queue;
            g_scheduler.run_queue = coro->next;
            coro->next = NULL;
            dv_coro_resume(coro);
        }

        /* 2. 处理到期定时器 */
        int timer_remaining = dv_process_timers();

        /* 3. 计算 poller 超时 */
        int poll_timeout;
        if (g_io_wait_head) {
            poll_timeout = (timer_remaining >= 0) ? timer_remaining : -1;
        } else if (timer_remaining >= 0) {
            poll_timeout = timer_remaining;
        } else {
            break;  /* 没有IO等待、没有定时器、没有就绪协程 → 退出 */
        }

        /* 4. 调用 poller 等待 IO 就绪 */
        if (g_io_wait_head && g_poller) {
            /* 输出缓冲按注册数分配，就绪数永远装得下 —— 不给「静默截断」留口子 */
            int cap = dv_poller_count(g_poller);
            if (cap < 1) cap = 1;
            int* out_fds = (int*)malloc((size_t)cap * sizeof(int));
            int* out_events = (int*)malloc((size_t)cap * sizeof(int));
            if (!out_fds || !out_events) {
                free(out_fds);
                free(out_events);
                fprintf(stderr, "[光明·事件循环] 就绪缓冲分配失败，退出事件循环\n");
                break;
            }
            int ready = dv_poller_wait_n(g_poller, poll_timeout, out_fds, out_events, cap);
            if (ready < 0) {
                fprintf(stderr, "[光明·事件循环] poller 等待失败：%s\n", dv_poller_last_error());
                free(out_fds);
                free(out_events);
                break;
            }

            /* 5. 把就绪 fd 对应的协程移回 run_queue */
            for (int i = 0; i < ready; i++) {
                LightIOWait** pp = &g_io_wait_head;
                while (*pp) {
                    LightIOWait* entry = *pp;
                    if (entry->fd == out_fds[i]) {
                        *pp = entry->next;
                        entry->coro->state = DV_CORO_READY;
                        entry->coro->waiting_for = NULL;
                        entry->coro->next = g_scheduler.run_queue;
                        g_scheduler.run_queue = entry->coro;
                        dv_poller_unregister(g_poller, entry->fd);
                        free(entry);
                        break;
                    }
                    pp = &entry->next;
                }
            }
            free(out_fds);
            free(out_events);
        } else if (poll_timeout > 0) {
            /* 只有定时器，没有IO等待：睡眠到下一个定时器到期 */
            dv_platform_sleep(poll_timeout);
            dv_process_timers();
        }
    }
}

/* ================================================================
 * R10-11b（第四批B）：生成器（type=24；23 号保留给元组 LV_TYPE_TUPLE）
 *
 * 为什么不用既有协程 `dv_coro_*`：那套是**推送式**调度器模型——协程被丢进
 * run_queue 由 `dv_coro_run_to_completion` 一路跑到完，挂起点靠 sleep/io 事件
 * 驱动，消费者拿不到中间值。生成器要的是**拉取式**：挂起在 `生成` 处、把值
 * 交回消费者、下次迭代再从挂起点继续。两套状态机语义正交，混用会把「await
 * 点编号」与「yield 点编号」搅在一起，故独立实现一套轻量状态机。
 *
 * 状态机形态（Duff's device）：生成器段被编成 `void f(LightGenerator* g)`，
 * 入口按 `g->state` switch 跳到对应恢复点；`生成` 处把值存进 `g->yielded`、
 * 把下一个恢复点写进 `g->state` 然后 `ret void`。因为函数每次恢复都是**重新
 * 调用**，任何跨 `生成` 存活的状态都不能留在 C 栈上——全部变量槽（参数 + 局部
 * + 表达式临时槽）都在 `g->slots` 堆数组里，槽指针由 codegen 在 entry 块一次
 * 取好（`dv_gen_slot`），从而支配所有恢复块，不会踩 LLVM 的
 * "instruction does not dominate all uses"。
 *
 * 生命周期：本批**不回收**生成器（无 GC、无引用计数）。单个生成器结构体很小
 * （几十字节 + 槽数组），stdlib 用法是一次性消费完；登记为已知债务。
 * ================================================================ */
#define LV_TYPE_GENERATOR 24

typedef struct LightGenerator LightGenerator;
typedef void (*LightGenFunc)(LightGenerator* g);

struct LightGenerator {
    LightGenFunc func;   /* 状态机函数指针 */
    int state;           /* 0=未启动, >0=下一个恢复点, -1=已完成 */
    int num_slots;       /* 槽位数（参数 + 局部 + 临时） */
    LightValue* slots;   /* 堆上槽位数组，跨 yield 存活 */
    LightValue yielded;  /* 本轮产出值 */
};

LightGenerator* dv_gen_create(void* func, int num_slots) {
    if (!func || num_slots < 1) return NULL;
    LightGenerator* g = (LightGenerator*)malloc(sizeof(LightGenerator));
    if (!g) return NULL;
    g->func = (LightGenFunc)func;
    g->state = 0;
    g->num_slots = num_slots;
    g->slots = (LightValue*)malloc(sizeof(LightValue) * (size_t)num_slots);
    if (!g->slots) { free(g); return NULL; }
    for (int i = 0; i < num_slots; i++) dv_null(&g->slots[i]);
    dv_null(&g->yielded);
    return g;
}

void dv_gen_free(LightGenerator* g) {
    if (!g) return;
    if (g->slots) {
        for (int i = 0; i < g->num_slots; i++) dv_free(&g->slots[i]);
        free(g->slots);
        g->slots = NULL;
    }
    free(g);
}

/* 取第 idx 个槽位；越界返回槽位 0 而不是 NULL——宁可污染一个槽，也不给
   codegen 一个空指针去 store（空指针 store 是段错误，越界是可诊断的 bug）。 */
LightValue* dv_gen_slot(LightGenerator* g, int idx) {
    if (!g || !g->slots || g->num_slots < 1) return NULL;
    if (idx < 0) idx = 0;
    if (idx >= g->num_slots) idx = g->num_slots - 1;
    return &g->slots[idx];
}

int dv_gen_state(LightGenerator* g) {
    return g ? g->state : -1;
}

/* `生成 值。`：把值拷进 yielded（dv_clone 深拷贝，防调用方槽位被复用后
   产出值跟着变），写入下一个恢复点。真正的 `ret void` 由 codegen 发。 */
void dv_gen_yield(LightGenerator* g, LightValue* val, int next_state) {
    if (!g) return;
    dv_free(&g->yielded);
    if (val) dv_clone(&g->yielded, val);
    else dv_null(&g->yielded);
    g->state = next_state;
}

void dv_gen_finish(LightGenerator* g) {
    if (!g) return;
    g->state = -1;
}

/* 把生成器包成 LightValue（type=24，str 字段存 LightGenerator*）。
   注意：不接管所有权——dv_clone 对 type=24 是浅拷贝（共享指针），
   dv_free 对 type=24 是 no-op，故本批不做释放。 */
void dv_gen_make(LightValue* result, LightGenerator* g) {
    if (!result) return;
    dv_null(result);
    if (!g) return;
    result->type = LV_TYPE_GENERATOR;
    result->str = (char*)g;
    result->i64 = 0;
    result->f64 = 0.0;
    result->boolean = 0;
    result->list_size = 0; result->list_capacity = 0; result->list_data = NULL;
}

int dv_is_generator(LightValue* v) {
    return (v && v->type == LV_TYPE_GENERATOR && v->str) ? 1 : 0;
}

/* 推进一步：调用状态机一次。返回 1 = 产出了一个值（可从 dv_gen_value 取），
   0 = 生成器结束。已结束时重复调用恒返回 0（幂等，防消费者多取一次）。 */
int dv_gen_resume(LightValue* genval) {
    if (!dv_is_generator(genval)) return 0;
    LightGenerator* g = (LightGenerator*)genval->str;
    if (g->state < 0) return 0;
    g->func(g);
    return (g->state < 0) ? 0 : 1;
}

void dv_gen_value(LightValue* result, LightValue* genval) {
    if (!result) return;
    dv_null(result);
    if (!dv_is_generator(genval)) return;
    LightGenerator* g = (LightGenerator*)genval->str;
    dv_clone(result, &g->yielded);
}

/* ================================================================
 * T4c: 文件系统句柄链配套 —— 路径 dirname/basename/abspath + 递归建目录
 *
 * 语义对齐 stdlib/builtins.py 对应函数（转译腿 _light_builtin.XXX 的 Python os 层）：
 *   dv_path_dirname  = os.path.dirname （posixpath.split 的 head）
 *   dv_path_basename = os.path.basename（posixpath.split 的 tail）
 *   dv_abspath       = os.path.abspath （相对路径基于 cwd 拼接 + normpath 规范化）
 *   dv_makedirs      = os.makedirs(path, exist_ok=True)（逐级建父目录，已存在不算错）
 * 本段位于非 TLS 区域末尾；TLS 段（T7 所属）在其下方，勿动。
 * ================================================================ */

static int dv_mkdir_one(const char* path) {
    if (!path || !*path) return -1;
#ifdef _WIN32
    return _mkdir(path);
#else
    return mkdir(path, 0755);
#endif
}

void dv_path_dirname(LightValue* result, LightValue* path) {
    if (!result) return;
    dv_null(result);
    if (!path || path->type != 3 || !path->str) { dv_str(result, ""); return; }
    const char* s = path->str;
    const char* last = NULL;
    for (const char* p = s; *p; p++) {
        if (*p == '/') last = p;
    }
    size_t head_len = (last == NULL) ? 0 : (size_t)(last - s) + 1;
    int all_slash = 1;
    for (size_t i = 0; i < head_len; i++) {
        if (s[i] != '/') { all_slash = 0; break; }
    }
    if (head_len > 0 && !all_slash) {
        while (head_len > 0 && s[head_len - 1] == '/') head_len--;
    }
    char* out = (char*)malloc(head_len + 1);
    if (!out) { dv_str(result, ""); return; }
    memcpy(out, s, head_len);
    out[head_len] = '\0';
    result->type = 3;
    result->i64 = 0; result->f64 = 0.0; result->boolean = 0;
    result->list_size = 0; result->list_capacity = 0; result->list_data = NULL;
    result->str = out;
}

void dv_path_basename(LightValue* result, LightValue* path) {
    if (!result) return;
    dv_null(result);
    if (!path || path->type != 3 || !path->str) { dv_str(result, ""); return; }
    const char* s = path->str;
    const char* last = NULL;
    for (const char* p = s; *p; p++) {
        if (*p == '/') last = p;
    }
    dv_str(result, (last == NULL) ? s : (last + 1));
}

/* 路径规范化：折叠 '.'、'..' 与重复分隔符（os.path.normpath 主要语义）。
 * 输入分隔符 '/' 与 '\\' 均接受（Windows）；输出统一用 '/'。 */
static void dv_normpath(char* out, size_t outsz, const char* s) {
    if (!out || outsz == 0) return;
    char tmp[16384];
    size_t tl = 0;
    for (const char* p = s; *p && tl + 1 < sizeof(tmp); p++) {
        char c = (*p == '\\') ? '/' : *p;
        tmp[tl++] = c;
    }
    tmp[tl] = '\0';
    char drive[4] = {0};
    const char* body = tmp;
    if (tl >= 2 && tmp[1] == ':' &&
        ((tmp[0] >= 'A' && tmp[0] <= 'Z') || (tmp[0] >= 'a' && tmp[0] <= 'z'))) {
        drive[0] = tmp[0]; drive[1] = ':'; drive[2] = '\0';
        body = tmp + 2;
    }
    /* 是否绝对路径：以盘符前缀之后的 body 是否以 '/' 开头为准（修复
     * Windows 盘符绝对路径 'G:/x' 被误判为相对、盘符后分隔符丢失的问题）。 */
    int is_abs = (body[0] == '/');
    char* segs[8192];
    int n = 0;
    char* tok = strtok(body, "/");
    while (tok && n < 8192) {
        if (strcmp(tok, ".") == 0) { tok = strtok(NULL, "/"); continue; }
        if (strcmp(tok, "..") == 0) {
            if (n > 0 && strcmp(segs[n - 1], "..") != 0) { n--; }
            else if (!is_abs && !(drive[0])) { segs[n++] = tok; }
            tok = strtok(NULL, "/");
            continue;
        }
        segs[n++] = tok;
        tok = strtok(NULL, "/");
    }
    size_t o = 0;
    if (drive[0] && o + 2 < outsz) { out[o++] = drive[0]; out[o++] = ':'; }
    if (is_abs && o + 1 < outsz) out[o++] = '/';
    for (int i = 0; i < n && o < outsz; i++) {
        size_t l = strlen(segs[i]);
        if (o + l + 1 >= outsz) break;
        if (i > 0 && !(o > 0 && out[o - 1] == '/')) out[o++] = '/';
        memcpy(out + o, segs[i], l);
        o += l;
    }
    if (o == 0 && !drive[0]) { out[0] = '.'; o = 1; }
    out[o] = '\0';
}

void dv_abspath(LightValue* result, LightValue* path) {
    if (!result) return;
    dv_null(result);
    if (!path || path->type != 3 || !path->str) { dv_str(result, ""); return; }
    const char* s = path->str;
    int is_abs = 0;
#ifdef _WIN32
    if (s[0] == '/' || s[0] == '\\' ||
        (((s[0] >= 'A' && s[0] <= 'Z') || (s[0] >= 'a' && s[0] <= 'z')) && s[1] == ':')) {
        is_abs = 1;
    }
#else
    if (s[0] == '/') is_abs = 1;
#endif
    char joined[16384];
    const char* src = s;
    if (!is_abs) {
#ifdef _WIN32
        char cwd[MAX_PATH];
        if (_getcwd(cwd, sizeof(cwd)) == NULL) { dv_str(result, s); return; }
        size_t cl = strlen(cwd);
        if (cl > 0 && cwd[cl - 1] != '/' && cwd[cl - 1] != '\\') {
            snprintf(joined, sizeof(joined), "%s\\%s", cwd, s);
        } else {
            snprintf(joined, sizeof(joined), "%s%s", cwd, s);
        }
#else
        char cwd[4096];
        if (getcwd(cwd, sizeof(cwd)) == NULL) { dv_str(result, s); return; }
        size_t cl = strlen(cwd);
        if (cl > 0 && cwd[cl - 1] != '/') {
            snprintf(joined, sizeof(joined), "%s/%s", cwd, s);
        } else {
            snprintf(joined, sizeof(joined), "%s%s", cwd, s);
        }
#endif
        src = joined;
    }
    char norm[16384];
    dv_normpath(norm, sizeof(norm), src);
    dv_str(result, norm);
}

int dv_makedirs(const char* path) {
    if (!path || !*path) return -1;
    char* copy = dv_strdup(path);
    if (!copy) return -1;
    int rc = 0;
    size_t start = 1;
    if (copy[0] && copy[1] == ':') start = 2; /* Windows 盘符 "X:" 不参与逐级 */
    for (char* p = copy + start; *p; p++) {
        if (*p == '/' || *p == '\\') {
            char saved = *p;
            *p = '\0';
            if (*copy != '\0' && dv_mkdir_one(copy) != 0 && dv_is_dir(copy) != 1) {
                rc = -1; *p = saved; break;
            }
            *p = saved;
        }
    }
    if (rc == 0 && *copy != '\0') {
        if (dv_mkdir_one(copy) != 0 && dv_is_dir(copy) != 1) rc = -1;
    }
    free(copy);
    return rc;
}

/* ================================================================
 * B2-4: 原生 TLS —— Windows Schannel 客户端
 *
 * 设计口径（与 dv_socket_* 对齐 + 能和 dv_coro_await_io 协作）：
 *
 *   dv_tls_wrap(fd, host)   包一个已 connect 的 fd，不自己发起连接
 *   dv_tls_handshake(t)     可重入的握手状态机，返回
 *                           0=完成 / 1=WANT_READ / 2=WANT_WRITE / -1=错误
 *   dv_tls_want_event(t)    把 WANT_* 翻成 DV_POLL_READ/DV_POLL_WRITE，
 *                           调用方直接喂给 dv_coro_await_io，**不阻塞事件循环**
 *   dv_tls_send / dv_tls_recv / dv_tls_free
 *
 * 为什么选 Schannel 而不是 OpenSSL/mbedTLS：Schannel 是系统自带，
 * 不引入第三方依赖、不改分发形态，与本项目「不装库」的口径一致。
 *
 * 证书校验**默认开启**（g_tls_verify_default=1）。
 *   - 默认信任锚 = 系统根存储
 *   - dv_tls_add_trusted_cert_file(path) 追加显式信任锚（curl --cacert 语义），
 *     一旦设置就用「独占根」引擎，只认这一批根 —— 比系统根更严
 *   - dv_tls_set_verify(t, 0) 才关校验，且每次调用都往 stderr 打醒目告警
 * ================================================================ */

#define DV_TLS_OK          0
#define DV_TLS_WANT_READ   1
#define DV_TLS_WANT_WRITE  2
#define DV_TLS_ERROR      (-1)
#define DV_TLS_CLOSED     (-2)

static char g_tls_error[512] = {0};
static int g_tls_verify_default = 1;   /* 校验默认开启 —— 安全红线 */

const char* dv_tls_last_error(void) {
    return g_tls_error;
}

#ifdef _WIN32

#define SECURITY_WIN32
#include <sspi.h>
#include <schannel.h>
#include <wincrypt.h>
#pragma comment(lib, "secur32.lib")
#pragma comment(lib, "crypt32.lib")

/* 显式信任锚（--cacert 语义）：非 NULL 时作为独占根 */
static HCERTSTORE g_tls_extra_roots = NULL;
static HCERTCHAINENGINE g_tls_chain_engine = NULL;

typedef struct LightTLS {
    int fd;
    char host[256];
    CredHandle cred;
    CtxtHandle ctx;
    int cred_ok;
    int ctx_ok;
    int verify;                 /* 1=校验证书 */
    int handshake_done;
    int hs_started;
    int need_more_input;
    int peer_closed;
    int recv_status;            /* 最近一次 dv_tls_recv 的状态：DV_TLS_OK/WANT_READ/CLOSED/ERROR */

    char* enc;                  /* 已收到但未解密的密文 */
    int enc_len;
    int enc_cap;

    char* plain;                /* 已解密未取走的明文 */
    int plain_len;
    int plain_off;
    int plain_cap;

    char* out_pending;          /* 尚未写完的密文（非阻塞 socket 用） */
    int out_len;
    int out_off;
    int out_cap;

    SecPkgContext_StreamSizes sizes;
} LightTLS;

static int dv_tls_would_block(void) {
    int e = WSAGetLastError();
    return (e == WSAEWOULDBLOCK || e == WSAEINPROGRESS);
}

static int dv_tls_buf_reserve(char** buf, int* cap, int need) {
    if (*cap >= need) return 0;
    int c = *cap ? *cap : 4096;
    while (c < need) c *= 2;
    char* nb = (char*)realloc(*buf, (size_t)c);
    if (!nb) {
        snprintf(g_tls_error, sizeof(g_tls_error), "TLS 缓冲扩容失败（目标 %d 字节）", c);
        return -1;
    }
    *buf = nb;
    *cap = c;
    return 0;
}

/* 把 out_pending 里剩下的字节写出去。0=写完 / DV_TLS_WANT_WRITE / DV_TLS_ERROR */
static int dv_tls_flush(LightTLS* t) {
    while (t->out_off < t->out_len) {
        int n = send(t->fd, t->out_pending + t->out_off, t->out_len - t->out_off, 0);
        if (n > 0) {
            t->out_off += n;
            continue;
        }
        if (n < 0 && dv_tls_would_block()) return DV_TLS_WANT_WRITE;
        snprintf(g_tls_error, sizeof(g_tls_error), "TLS 写 socket 失败: errno %d", WSAGetLastError());
        return DV_TLS_ERROR;
    }
    t->out_off = 0;
    t->out_len = 0;
    return DV_TLS_OK;
}

static int dv_tls_queue_out(LightTLS* t, const char* data, int len) {
    if (len <= 0) return DV_TLS_OK;
    /* 先把已排队的压实 */
    if (t->out_off > 0 && t->out_off == t->out_len) { t->out_off = 0; t->out_len = 0; }
    if (dv_tls_buf_reserve(&t->out_pending, &t->out_cap, t->out_len + len) != 0) return DV_TLS_ERROR;
    memcpy(t->out_pending + t->out_len, data, (size_t)len);
    t->out_len += len;
    return dv_tls_flush(t);
}

/* 从 socket 读一批密文。>0=读到字节数 / DV_TLS_WANT_READ / 0=对端关闭 / DV_TLS_ERROR */
static int dv_tls_fill(LightTLS* t) {
    const int chunk = 8192;
    if (dv_tls_buf_reserve(&t->enc, &t->enc_cap, t->enc_len + chunk) != 0) return DV_TLS_ERROR;
    int n = recv(t->fd, t->enc + t->enc_len, chunk, 0);
    if (n > 0) {
        t->enc_len += n;
        return n;
    }
    if (n == 0) {
        t->peer_closed = 1;
        return 0;
    }
    if (dv_tls_would_block()) return DV_TLS_WANT_READ;
    snprintf(g_tls_error, sizeof(g_tls_error), "TLS 读 socket 失败: errno %d", WSAGetLastError());
    return DV_TLS_ERROR;
}

static int dv_tls_acquire_cred(LightTLS* t) {
    SCHANNEL_CRED sc;
    memset(&sc, 0, sizeof(sc));
    sc.dwVersion = SCHANNEL_CRED_VERSION;
    /* 手动校验：证书链由我们自己按 g_tls_extra_roots / 系统根判定，
       这样「显式信任锚」和「关校验」两条路径都走同一段可审计的代码 */
    sc.dwFlags = SCH_CRED_NO_DEFAULT_CREDS | SCH_CRED_MANUAL_CRED_VALIDATION;
    SECURITY_STATUS ss = AcquireCredentialsHandleA(NULL, (char*)UNISP_NAME_A, SECPKG_CRED_OUTBOUND,
                                                  NULL, &sc, NULL, NULL, &t->cred, NULL);
    if (ss != SEC_E_OK) {
        snprintf(g_tls_error, sizeof(g_tls_error), "AcquireCredentialsHandle 失败: 0x%lx", (unsigned long)ss);
        return -1;
    }
    t->cred_ok = 1;
    return 0;
}

/* 证书链校验：主机名 + 有效期 + 信任锚。0=通过 / -1=不通过（写 g_tls_error） */
static int dv_tls_verify_peer(LightTLS* t) {
    PCCERT_CONTEXT peer = NULL;
    SECURITY_STATUS ss = QueryContextAttributesA(&t->ctx, SECPKG_ATTR_REMOTE_CERT_CONTEXT, &peer);
    if (ss != SEC_E_OK || !peer) {
        snprintf(g_tls_error, sizeof(g_tls_error), "取对端证书失败: 0x%lx", (unsigned long)ss);
        return -1;
    }

    CERT_CHAIN_PARA para;
    memset(&para, 0, sizeof(para));
    para.cbSize = sizeof(para);
    LPCSTR usage[] = { szOID_PKIX_KP_SERVER_AUTH };
    para.RequestedUsage.dwType = USAGE_MATCH_TYPE_AND;
    para.RequestedUsage.Usage.cUsageIdentifier = 1;
    para.RequestedUsage.Usage.rgpszUsageIdentifier = (LPSTR*)usage;

    PCCERT_CHAIN_CONTEXT chain = NULL;
    HCERTCHAINENGINE engine = g_tls_chain_engine ? g_tls_chain_engine : HCCE_CURRENT_USER;
    if (!CertGetCertificateChain(engine, peer, NULL, peer->hCertStore, &para, 0, NULL, &chain)) {
        snprintf(g_tls_error, sizeof(g_tls_error), "构建证书链失败: 0x%lx", (unsigned long)GetLastError());
        CertFreeCertificateContext(peer);
        return -1;
    }

    /* 主机名 + SSL 策略 */
    wchar_t whost[256];
    int wn = MultiByteToWideChar(CP_UTF8, 0, t->host, -1, whost, 255);
    if (wn <= 0) whost[0] = L'\0';

    SSL_EXTRA_CERT_CHAIN_POLICY_PARA sslpara;
    memset(&sslpara, 0, sizeof(sslpara));
    sslpara.cbSize = sizeof(sslpara);
    sslpara.dwAuthType = AUTHTYPE_SERVER;
    sslpara.pwszServerName = whost;

    CERT_CHAIN_POLICY_PARA polpara;
    memset(&polpara, 0, sizeof(polpara));
    polpara.cbSize = sizeof(polpara);
    polpara.pvExtraPolicyPara = &sslpara;

    CERT_CHAIN_POLICY_STATUS polstatus;
    memset(&polstatus, 0, sizeof(polstatus));
    polstatus.cbSize = sizeof(polstatus);

    int ok = 0;
    if (!CertVerifyCertificateChainPolicy(CERT_CHAIN_POLICY_SSL, chain, &polpara, &polstatus)) {
        snprintf(g_tls_error, sizeof(g_tls_error), "证书策略校验调用失败: 0x%lx",
                 (unsigned long)GetLastError());
    } else if (polstatus.dwError != 0) {
        snprintf(g_tls_error, sizeof(g_tls_error),
                 "证书校验不通过: 0x%lx（链错误 0x%lx）",
                 (unsigned long)polstatus.dwError,
                 (unsigned long)chain->TrustStatus.dwErrorStatus);
    } else if (chain->TrustStatus.dwErrorStatus != 0) {
        snprintf(g_tls_error, sizeof(g_tls_error),
                 "证书链不可信: 0x%lx", (unsigned long)chain->TrustStatus.dwErrorStatus);
    } else {
        ok = 1;
    }

    CertFreeCertificateChain(chain);
    CertFreeCertificateContext(peer);
    return ok ? 0 : -1;
}

LightTLS* dv_tls_wrap(int fd, const char* host) {
    if (fd < 0) {
        snprintf(g_tls_error, sizeof(g_tls_error), "dv_tls_wrap: 非法 fd %d", fd);
        return NULL;
    }
    LightTLS* t = (LightTLS*)calloc(1, sizeof(LightTLS));
    if (!t) {
        snprintf(g_tls_error, sizeof(g_tls_error), "dv_tls_wrap: 内存不足");
        return NULL;
    }
    t->fd = fd;
    t->verify = g_tls_verify_default;
    if (host && host[0]) {
        strncpy(t->host, host, sizeof(t->host) - 1);
    } else {
        /* 没有主机名就无法做主机名校验 —— 明确拒绝而不是静默降级 */
        snprintf(g_tls_error, sizeof(g_tls_error),
                 "dv_tls_wrap: 必须给主机名（SNI + 主机名校验都要它），拒绝无名包装");
        free(t);
        return NULL;
    }
    return t;
}

int dv_tls_set_verify(LightTLS* t, int enable) {
    if (!t) return -1;
    t->verify = enable ? 1 : 0;
    if (!enable) {
        fprintf(stderr,
                "\n***** 【安全告警】TLS 证书校验已被显式关闭（host=%s）*****\n"
                "***** 该连接可被中间人劫持，仅允许在受控测试中使用    *****\n\n",
                t->host);
        fflush(stderr);
    }
    return 0;
}

int dv_tls_add_trusted_cert_file(const char* path) {
    if (!path || !path[0]) {
        snprintf(g_tls_error, sizeof(g_tls_error), "dv_tls_add_trusted_cert_file: 路径为空");
        return -1;
    }
    FILE* f = fopen(path, "rb");
    if (!f) {
        snprintf(g_tls_error, sizeof(g_tls_error), "打开信任锚文件失败: %s", path);
        return -1;
    }
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (sz <= 0 || sz > 4 * 1024 * 1024) {
        fclose(f);
        snprintf(g_tls_error, sizeof(g_tls_error), "信任锚文件大小异常: %ld", sz);
        return -1;
    }
    unsigned char* raw = (unsigned char*)malloc((size_t)sz + 1);
    if (!raw) { fclose(f); return -1; }
    size_t got = fread(raw, 1, (size_t)sz, f);
    fclose(f);
    raw[got] = 0;

    /* PEM → DER；不是 PEM 就按 DER 直接用 */
    unsigned char* der = NULL;
    DWORD der_len = 0;
    int der_owned = 0;
    if (strstr((char*)raw, "-----BEGIN")) {
        if (!CryptStringToBinaryA((LPCSTR)raw, (DWORD)got, CRYPT_STRING_BASE64HEADER,
                                  NULL, &der_len, NULL, NULL)) {
            free(raw);
            snprintf(g_tls_error, sizeof(g_tls_error), "PEM 解码长度探测失败: 0x%lx",
                     (unsigned long)GetLastError());
            return -1;
        }
        der = (unsigned char*)malloc(der_len);
        if (!der) { free(raw); return -1; }
        if (!CryptStringToBinaryA((LPCSTR)raw, (DWORD)got, CRYPT_STRING_BASE64HEADER,
                                  der, &der_len, NULL, NULL)) {
            free(der);
            free(raw);
            snprintf(g_tls_error, sizeof(g_tls_error), "PEM 解码失败: 0x%lx",
                     (unsigned long)GetLastError());
            return -1;
        }
        der_owned = 1;
    } else {
        der = raw;
        der_len = (DWORD)got;
    }

    if (!g_tls_extra_roots) {
        g_tls_extra_roots = CertOpenStore(CERT_STORE_PROV_MEMORY, 0, 0,
                                         CERT_STORE_CREATE_NEW_FLAG, NULL);
        if (!g_tls_extra_roots) {
            if (der_owned) free(der);
            free(raw);
            snprintf(g_tls_error, sizeof(g_tls_error), "创建信任锚存储失败");
            return -1;
        }
    }

    BOOL added = CertAddEncodedCertificateToStore(g_tls_extra_roots, X509_ASN_ENCODING,
                                                  der, der_len, CERT_STORE_ADD_ALWAYS, NULL);
    if (der_owned) free(der);
    free(raw);
    if (!added) {
        snprintf(g_tls_error, sizeof(g_tls_error), "加入信任锚失败: 0x%lx",
                 (unsigned long)GetLastError());
        return -1;
    }

    /* 用「独占根」引擎：只认显式给的这批根，比系统根更严 */
    if (g_tls_chain_engine) {
        CertFreeCertificateChainEngine(g_tls_chain_engine);
        g_tls_chain_engine = NULL;
    }
    CERT_CHAIN_ENGINE_CONFIG cfg;
    memset(&cfg, 0, sizeof(cfg));
    cfg.cbSize = sizeof(cfg);
    cfg.hExclusiveRoot = g_tls_extra_roots;
    if (!CertCreateCertificateChainEngine(&cfg, &g_tls_chain_engine)) {
        g_tls_chain_engine = NULL;
        snprintf(g_tls_error, sizeof(g_tls_error), "创建独占根链引擎失败: 0x%lx",
                 (unsigned long)GetLastError());
        return -1;
    }
    return 0;
}

int dv_tls_handshake(LightTLS* t) {
    if (!t) {
        snprintf(g_tls_error, sizeof(g_tls_error), "dv_tls_handshake: 句柄为空");
        return DV_TLS_ERROR;
    }
    if (t->handshake_done) return DV_TLS_OK;

    /* 上一轮没写完的先写完 */
    int fr = dv_tls_flush(t);
    if (fr != DV_TLS_OK) return fr;

    if (!t->cred_ok && dv_tls_acquire_cred(t) != 0) return DV_TLS_ERROR;

    DWORD req = ISC_REQ_SEQUENCE_DETECT | ISC_REQ_REPLAY_DETECT | ISC_REQ_CONFIDENTIALITY |
                ISC_RET_EXTENDED_ERROR | ISC_REQ_ALLOCATE_MEMORY | ISC_REQ_STREAM;

    if (!t->hs_started) {
        SecBuffer outb;
        outb.pvBuffer = NULL; outb.BufferType = SECBUFFER_TOKEN; outb.cbBuffer = 0;
        SecBufferDesc outd;
        outd.ulVersion = SECBUFFER_VERSION; outd.cBuffers = 1; outd.pBuffers = &outb;
        DWORD outflags = 0;
        SECURITY_STATUS ss = InitializeSecurityContextA(&t->cred, NULL, t->host, req, 0, 0,
                                                       NULL, 0, &t->ctx, &outd, &outflags, NULL);
        if (ss != SEC_I_CONTINUE_NEEDED) {
            snprintf(g_tls_error, sizeof(g_tls_error),
                     "InitializeSecurityContext(首轮) 失败: 0x%lx", (unsigned long)ss);
            return DV_TLS_ERROR;
        }
        t->ctx_ok = 1;
        t->hs_started = 1;
        int qr = DV_TLS_OK;
        if (outb.cbBuffer && outb.pvBuffer) {
            qr = dv_tls_queue_out(t, (const char*)outb.pvBuffer, (int)outb.cbBuffer);
            FreeContextBuffer(outb.pvBuffer);
        }
        if (qr != DV_TLS_OK) return qr;
        t->need_more_input = 1;
    }

    for (;;) {
        if (t->need_more_input || t->enc_len == 0) {
            int r = dv_tls_fill(t);
            if (r == DV_TLS_WANT_READ) return DV_TLS_WANT_READ;
            if (r == DV_TLS_ERROR) return DV_TLS_ERROR;
            if (r == 0) {
                snprintf(g_tls_error, sizeof(g_tls_error), "握手中对端关闭连接");
                return DV_TLS_ERROR;
            }
            t->need_more_input = 0;
        }

        SecBuffer inb[2];
        inb[0].pvBuffer = t->enc; inb[0].cbBuffer = (unsigned long)t->enc_len;
        inb[0].BufferType = SECBUFFER_TOKEN;
        inb[1].pvBuffer = NULL; inb[1].cbBuffer = 0; inb[1].BufferType = SECBUFFER_EMPTY;
        SecBufferDesc ind;
        ind.ulVersion = SECBUFFER_VERSION; ind.cBuffers = 2; ind.pBuffers = inb;

        SecBuffer outb[2];
        outb[0].pvBuffer = NULL; outb[0].cbBuffer = 0; outb[0].BufferType = SECBUFFER_TOKEN;
        outb[1].pvBuffer = NULL; outb[1].cbBuffer = 0; outb[1].BufferType = SECBUFFER_ALERT;
        SecBufferDesc outd;
        outd.ulVersion = SECBUFFER_VERSION; outd.cBuffers = 2; outd.pBuffers = outb;

        DWORD outflags = 0;
        SECURITY_STATUS ss = InitializeSecurityContextA(&t->cred, &t->ctx, t->host, req, 0, 0,
                                                       &ind, 0, NULL, &outd, &outflags, NULL);

        if (ss == SEC_E_INCOMPLETE_MESSAGE) {
            t->need_more_input = 1;
            continue;
        }

        int qr = DV_TLS_OK;
        if (outb[0].cbBuffer && outb[0].pvBuffer) {
            qr = dv_tls_queue_out(t, (const char*)outb[0].pvBuffer, (int)outb[0].cbBuffer);
        }
        if (outb[0].pvBuffer) FreeContextBuffer(outb[0].pvBuffer);
        if (outb[1].pvBuffer) FreeContextBuffer(outb[1].pvBuffer);

        /* 处理未消费的尾巴 */
        if (inb[1].BufferType == SECBUFFER_EXTRA && inb[1].cbBuffer > 0) {
            int extra = (int)inb[1].cbBuffer;
            memmove(t->enc, t->enc + (t->enc_len - extra), (size_t)extra);
            t->enc_len = extra;
        } else if (ss != SEC_E_INCOMPLETE_MESSAGE) {
            t->enc_len = 0;
        }

        if (qr == DV_TLS_ERROR) return DV_TLS_ERROR;

        if (ss == SEC_I_CONTINUE_NEEDED) {
            if (qr == DV_TLS_WANT_WRITE) return DV_TLS_WANT_WRITE;
            t->need_more_input = (t->enc_len == 0);
            continue;
        }
        if (ss == SEC_E_OK) {
            if (qr == DV_TLS_WANT_WRITE) return DV_TLS_WANT_WRITE;
            if (t->verify) {
                if (dv_tls_verify_peer(t) != 0) return DV_TLS_ERROR;
            } else {
                fprintf(stderr, "[光明·TLS] 警告：host=%s 的证书校验被跳过\n", t->host);
            }
            SECURITY_STATUS qs = QueryContextAttributesA(&t->ctx, SECPKG_ATTR_STREAM_SIZES, &t->sizes);
            if (qs != SEC_E_OK) {
                snprintf(g_tls_error, sizeof(g_tls_error), "取 StreamSizes 失败: 0x%lx",
                         (unsigned long)qs);
                return DV_TLS_ERROR;
            }
            t->handshake_done = 1;
            return DV_TLS_OK;
        }
        if (ss == SEC_I_INCOMPLETE_CREDENTIALS) {
            snprintf(g_tls_error, sizeof(g_tls_error), "对端要求客户端证书，本实现不支持");
            return DV_TLS_ERROR;
        }
        snprintf(g_tls_error, sizeof(g_tls_error), "TLS 握手失败: 0x%lx", (unsigned long)ss);
        return DV_TLS_ERROR;
    }
}

int dv_tls_want_event(LightTLS* t) {
    if (!t) return DV_POLL_READ;
    if (t->out_off < t->out_len) return DV_POLL_WRITE;
    return DV_POLL_READ;
}

int dv_tls_is_ready(LightTLS* t) {
    return (t && t->handshake_done) ? 1 : 0;
}

/* 带长度的发送：可以处理含 NUL 字节的二进制数据（如 WebSocket 二进制帧）。
 * 返回已发送的明文字节数；WANT_WRITE 时返回已排队部分；ERROR 返回 -1。 */
int dv_tls_send_n(LightTLS* t, const char* data, int len) {
    if (!t || !t->handshake_done) {
        snprintf(g_tls_error, sizeof(g_tls_error), "dv_tls_send: 握手未完成");
        return DV_TLS_ERROR;
    }
    int fr = dv_tls_flush(t);
    if (fr != DV_TLS_OK) return fr;
    if (!data || len <= 0) return 0;
    int sent = 0;
    while (sent < len) {
        int chunk = len - sent;
        if (chunk > (int)t->sizes.cbMaximumMessage) chunk = (int)t->sizes.cbMaximumMessage;
        unsigned long need = t->sizes.cbHeader + (unsigned long)chunk + t->sizes.cbTrailer;
        char* rec = (char*)malloc(need);
        if (!rec) {
            snprintf(g_tls_error, sizeof(g_tls_error), "dv_tls_send: 记录缓冲分配失败");
            return DV_TLS_ERROR;
        }
        memcpy(rec + t->sizes.cbHeader, data + sent, (size_t)chunk);

        SecBuffer b[4];
        b[0].pvBuffer = rec; b[0].cbBuffer = t->sizes.cbHeader; b[0].BufferType = SECBUFFER_STREAM_HEADER;
        b[1].pvBuffer = rec + t->sizes.cbHeader; b[1].cbBuffer = (unsigned long)chunk;
        b[1].BufferType = SECBUFFER_DATA;
        b[2].pvBuffer = rec + t->sizes.cbHeader + chunk; b[2].cbBuffer = t->sizes.cbTrailer;
        b[2].BufferType = SECBUFFER_STREAM_TRAILER;
        b[3].pvBuffer = NULL; b[3].cbBuffer = 0; b[3].BufferType = SECBUFFER_EMPTY;
        SecBufferDesc d;
        d.ulVersion = SECBUFFER_VERSION; d.cBuffers = 4; d.pBuffers = b;

        SECURITY_STATUS ss = EncryptMessage(&t->ctx, 0, &d, 0);
        if (ss != SEC_E_OK) {
            free(rec);
            snprintf(g_tls_error, sizeof(g_tls_error), "EncryptMessage 失败: 0x%lx", (unsigned long)ss);
            return DV_TLS_ERROR;
        }
        int reclen = (int)(b[0].cbBuffer + b[1].cbBuffer + b[2].cbBuffer);
        int qr = dv_tls_queue_out(t, rec, reclen);
        free(rec);
        if (qr == DV_TLS_ERROR) return DV_TLS_ERROR;
        sent += chunk;
        if (qr == DV_TLS_WANT_WRITE) {
            /* 已排队但没写完：明文层面算已接收，调用方等可写后调 dv_tls_flush_public */
            return sent;
        }
    }
    return sent;
}

/* 旧 ABI：用 strlen 限制，不能发含 NUL 的二进制数据。等价于 dv_tls_send_n(t, data, strlen(data))。 */
int dv_tls_send(LightTLS* t, const char* data) {
    return dv_tls_send_n(t, data, data ? (int)strlen(data) : 0);
}

int dv_tls_flush_public(LightTLS* t) {
    if (!t) return DV_TLS_ERROR;
    return dv_tls_flush(t);
}

/* 解密一轮：把 enc 里能解的搬到 plain。0=有进展 / WANT_READ / CLOSED / ERROR */
static int dv_tls_decrypt_step(LightTLS* t) {
    for (;;) {
        if (t->enc_len == 0) {
            int r = dv_tls_fill(t);
            if (r == DV_TLS_WANT_READ) return DV_TLS_WANT_READ;
            if (r == DV_TLS_ERROR) return DV_TLS_ERROR;
            if (r == 0) return DV_TLS_CLOSED;
        }

        SecBuffer b[4];
        b[0].pvBuffer = t->enc; b[0].cbBuffer = (unsigned long)t->enc_len;
        b[0].BufferType = SECBUFFER_DATA;
        for (int i = 1; i < 4; i++) {
            b[i].pvBuffer = NULL; b[i].cbBuffer = 0; b[i].BufferType = SECBUFFER_EMPTY;
        }
        SecBufferDesc d;
        d.ulVersion = SECBUFFER_VERSION; d.cBuffers = 4; d.pBuffers = b;

        SECURITY_STATUS ss = DecryptMessage(&t->ctx, &d, 0, NULL);
        if (ss == SEC_E_INCOMPLETE_MESSAGE) {
            int r = dv_tls_fill(t);
            if (r == DV_TLS_WANT_READ) return DV_TLS_WANT_READ;
            if (r == DV_TLS_ERROR) return DV_TLS_ERROR;
            if (r == 0) return DV_TLS_CLOSED;
            continue;
        }
        if (ss == SEC_I_CONTEXT_EXPIRED) {
            t->peer_closed = 1;
            t->enc_len = 0;
            return DV_TLS_CLOSED;
        }
        if (ss != SEC_E_OK) {
            snprintf(g_tls_error, sizeof(g_tls_error), "DecryptMessage 失败: 0x%lx", (unsigned long)ss);
            return DV_TLS_ERROR;
        }

        SecBuffer* data = NULL;
        SecBuffer* extra = NULL;
        for (int i = 0; i < 4; i++) {
            if (!data && b[i].BufferType == SECBUFFER_DATA) data = &b[i];
            else if (!extra && b[i].BufferType == SECBUFFER_EXTRA) extra = &b[i];
        }
        if (data && data->cbBuffer > 0) {
            /* 压实 plain 后追加 */
            if (t->plain_off > 0) {
                memmove(t->plain, t->plain + t->plain_off, (size_t)(t->plain_len - t->plain_off));
                t->plain_len -= t->plain_off;
                t->plain_off = 0;
            }
            if (dv_tls_buf_reserve(&t->plain, &t->plain_cap, t->plain_len + (int)data->cbBuffer) != 0)
                return DV_TLS_ERROR;
            memcpy(t->plain + t->plain_len, data->pvBuffer, data->cbBuffer);
            t->plain_len += (int)data->cbBuffer;
        }
        if (extra && extra->cbBuffer > 0) {
            memmove(t->enc, extra->pvBuffer, extra->cbBuffer);
            t->enc_len = (int)extra->cbBuffer;
        } else {
            t->enc_len = 0;
        }
        return DV_TLS_OK;
    }
}

void dv_tls_recv(LightValue* result, LightTLS* t, int max_bytes) {
    if (!result) return;
    if (!t || !t->handshake_done) {
        snprintf(g_tls_error, sizeof(g_tls_error), "dv_tls_recv: 握手未完成");
        if (t) t->recv_status = DV_TLS_ERROR;
        dv_str(result, "");
        return;
    }
    if (max_bytes <= 0) max_bytes = 4096;

    if (t->plain_off >= t->plain_len) {
        int r = dv_tls_decrypt_step(t);
        if (r != DV_TLS_OK) {
            /* 记录状态让调用方可查：WANT_READ / CLOSED / ERROR 不再混在一起 */
            t->recv_status = r;
            dv_str(result, "");
            return;
        }
    }
    int avail = t->plain_len - t->plain_off;
    if (avail <= 0) {
        t->recv_status = DV_TLS_WANT_READ;
        dv_str(result, "");
        return;
    }
    int n = avail < max_bytes ? avail : max_bytes;
    char* tmp = (char*)malloc((size_t)n + 1);
    if (!tmp) {
        t->recv_status = DV_TLS_ERROR;
        snprintf(g_tls_error, sizeof(g_tls_error), "dv_tls_recv: 临时缓冲分配失败");
        dv_str(result, "");
        return;
    }
    memcpy(tmp, t->plain + t->plain_off, (size_t)n);
    tmp[n] = '\0';
    t->plain_off += n;
    t->recv_status = DV_TLS_OK;
    dv_str(result, tmp);
    free(tmp);
}

/* 查询最近一次 dv_tls_recv 的状态：
 * DV_TLS_OK=有数据 / DV_TLS_WANT_READ=需要更多输入 / DV_TLS_CLOSED=对端关闭 / DV_TLS_ERROR=错误 */
int dv_tls_recv_status(LightTLS* t) {
    return t ? t->recv_status : DV_TLS_ERROR;
}

void dv_tls_free(LightTLS* t) {
    if (!t) return;
    if (t->ctx_ok) DeleteSecurityContext(&t->ctx);
    if (t->cred_ok) FreeCredentialsHandle(&t->cred);
    free(t->enc);
    free(t->plain);
    free(t->out_pending);
    free(t);
}

const char* dv_tls_backend(void) { return "Schannel"; }

#else  /* 非 Windows —— POSIX 原生 TLS */

/* ================================================================
 * B2-4（POSIX 补充，Task T7）：原生 TLS —— mbedTLS 客户端
 *
 * 为什么选 mbedTLS 而不是 OpenSSL：
 *   1) 原 stub 的错误文本就点名「POSIX 待补 mbedTLS」，方向既定；
 *   2) 与 Schannel 注释里「不装库 / 不改分发形态」的口径最接近：mbedTLS 体积小、
 *      可静态捆绑、无运行时依赖；OpenSSL 在 Linux 上虽普遍但 ABI 版本漂移大
 *      （1.1 vs 3.0），许可约束也比 Apache-2.0 的 mbedTLS 紧；
 *   3) mbedTLS 的 MBEDTLS_ERR_SSL_WANT_READ/WANT_WRITE 非阻塞语义与
 *      dv_tls_handshake 的可重入状态机天然对齐。
 *
 * 依赖：编译需 libmbedtls-dev（Ubuntu: apt install libmbedtls-dev），
 *       链接 -lmbedtls -lmbedx509 -lmbedcrypto。
 * 开/关：定义 LIGHT_TLS_MBEDTLS 启用真实现；未定义则保留下方 stub（保证
 *       未装 mbedTLS 的 POSIX 构建不破——「勿破坏原生腿其它部分」）。
 *
 * 行为对齐 Windows Schannel 分支（reverse-run 判据）：
 *   - 证书校验默认开启（g_tls_verify_default=1）；
 *   - dv_tls_add_trusted_cert_file 追加「独占根」信任锚（curl --cacert 语义）：
 *     一旦设置只认显式给的这批根，比系统根更严（对应 Windows hExclusiveRoot）；
 *   - 未设显式信任锚时默认信任锚 = 系统 CA 包（/etc/ssl/certs/ca-certificates.crt
 *     等，对应 Windows 系统根存储）；
 *   - 发送侧用「队列式 BIO」：mbedTLS 加密产物先进 out_pending 队列，由
 *     dv_tls_flush / dv_tls_want_event 负责非阻塞冲刷——与 Windows out_pending
 *     同构，半包写不完不阻塞事件循环。
 * ================================================================ */

#if defined(LIGHT_TLS_MBEDTLS)

#include <mbedtls/ssl.h>
#include <mbedtls/x509_crt.h>
#include <mbedtls/error.h>
#include <mbedtls/ctr_drbg.h>
#include <mbedtls/entropy.h>

typedef struct LightTLS {
    int fd;
    char host[256];
    int verify;                 /* 1=校验证书 */
    int handshake_done;
    int hs_started;             /* ssl/conf 已初始化 */
    int peer_closed;
    int recv_status;            /* 最近一次 dv_tls_recv 的状态 */

    mbedtls_ssl_context ssl;
    mbedtls_ssl_config conf;
    mbedtls_ctr_drbg_context ctr_drbg;   /* 握手随机源（mbedTLS 必须配置 RNG） */
    mbedtls_entropy_context entropy;

    char* out_pending;          /* 尚未写完的密文（非阻塞 socket，与 Windows 同构） */
    int out_len;
    int out_off;
    int out_cap;
} LightTLS;

/* ── 全局信任锚状态 ─────────────────────────────────────────── */
static mbedtls_x509_crt g_tls_ca_explicit;   /* 显式信任锚（独占根） */
static int g_tls_ca_explicit_ready = 0;
static int g_tls_roots_explicit = 0;         /* 已 add_trusted_cert_file */
static mbedtls_x509_crt g_tls_ca_default;    /* 系统默认 CA 包（懒加载） */
static int g_tls_ca_default_ready = 0;
static int g_tls_ca_default_loaded = 0;

static int dv_tls_posix_buf_reserve(char** buf, int* cap, int need) {
    if (*cap >= need) return 0;
    int c = *cap ? *cap : 4096;
    while (c < need) c *= 2;
    char* nb = (char*)realloc(*buf, (size_t)c);
    if (!nb) {
        snprintf(g_tls_error, sizeof(g_tls_error), "TLS 缓冲扩容失败（目标 %d 字节）", c);
        return -1;
    }
    *buf = nb;
    *cap = c;
    return 0;
}

/* 取当前连接应使用的 CA 链：显式信任锚（独占根）优先，否则系统默认 CA 包。 */
static mbedtls_x509_crt* dv_tls_get_ca_chain(void) {
    if (g_tls_roots_explicit) return &g_tls_ca_explicit;
    if (g_tls_ca_default_loaded) return &g_tls_ca_default;
    g_tls_ca_default_loaded = 1;
    if (!g_tls_ca_default_ready) {
        mbedtls_x509_crt_init(&g_tls_ca_default);
        g_tls_ca_default_ready = 1;
    }
    const char* envp = getenv("SSL_CERT_FILE");
    const char* std_paths[] = {
        "/etc/ssl/certs/ca-certificates.crt",        /* Debian / Ubuntu */
        "/etc/pki/tls/certs/ca-bundle.crt",          /* RHEL / Fedora */
        "/etc/ssl/ca-bundle.pem",                    /* SUSE */
        "/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem",
        "/usr/local/share/certs/ca-root-nss.crt",    /* FreeBSD */
        "/etc/ssl/cert.pem",                         /* macOS / 部分 BSD */
        NULL
    };
    const char* cands[8];
    int np = 0;
    if (envp && envp[0]) cands[np++] = envp;
    for (int i = 0; std_paths[i] && np < 8; i++) cands[np++] = std_paths[i];
    for (int i = 0; i < np; i++) {
        if (mbedtls_x509_crt_parse_file(&g_tls_ca_default, cands[i]) == 0)
            return &g_tls_ca_default;
        mbedtls_x509_crt_free(&g_tls_ca_default);
        mbedtls_x509_crt_init(&g_tls_ca_default);
    }
    snprintf(g_tls_error, sizeof(g_tls_error),
             "未找到可用的系统 CA 包（已试 %d 个候选，安装 ca-certificates 或设 SSL_CERT_FILE）", np);
    return &g_tls_ca_default;   /* 空链：verify=1 时握手必然失败（fail closed） */
}

/* 发送 BIO：把 mbedTLS 加密产物追加进 out_pending 队列（不直接写 socket）。
   返回 len=全部接收；队列积压超限返回 WANT_WRITE 施加背压。 */
static int dv_tls_bio_send(void* ctx, const unsigned char* buf, size_t len) {
    LightTLS* t = (LightTLS*)ctx;
    if (t->out_len - t->out_off > 8 * 1024 * 1024)
        return MBEDTLS_ERR_SSL_WANT_WRITE;   /* 背压：先冲刷再续 */
    if (t->out_off > 0 && t->out_off == t->out_len) { t->out_off = 0; t->out_len = 0; }
    if (dv_tls_posix_buf_reserve(&t->out_pending, &t->out_cap, t->out_len + (int)len) != 0)
        return MBEDTLS_ERR_SSL_INTERNAL_ERROR;
    memcpy(t->out_pending + t->out_len, buf, len);
    t->out_len += (int)len;
    return (int)len;
}

static int dv_tls_bio_recv(void* ctx, unsigned char* buf, size_t len) {
    LightTLS* t = (LightTLS*)ctx;
    ssize_t n = recv(t->fd, buf, len, 0);
    if (n > 0) return (int)n;
    if (n == 0) return 0;
    if (errno == EAGAIN || errno == EWOULDBLOCK) return MBEDTLS_ERR_SSL_WANT_READ;
    snprintf(g_tls_error, sizeof(g_tls_error), "TLS 读 socket 失败: errno %d", errno);
    return MBEDTLS_ERR_SSL_INTERNAL_ERROR;
}

/* 把 out_pending 里剩下的字节写出去。0=写完 / DV_TLS_WANT_WRITE / DV_TLS_ERROR */
static int dv_tls_flush(LightTLS* t) {
    while (t->out_off < t->out_len) {
        ssize_t n = send(t->fd, t->out_pending + t->out_off,
                         (size_t)(t->out_len - t->out_off), 0);
        if (n > 0) { t->out_off += (int)n; continue; }
        if (n < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) return DV_TLS_WANT_WRITE;
        snprintf(g_tls_error, sizeof(g_tls_error), "TLS 写 socket 失败: errno %d", errno);
        return DV_TLS_ERROR;
    }
    t->out_off = 0;
    t->out_len = 0;
    return DV_TLS_OK;
}

LightTLS* dv_tls_wrap(int fd, const char* host) {
    if (fd < 0) {
        snprintf(g_tls_error, sizeof(g_tls_error), "dv_tls_wrap: 非法 fd %d", fd);
        return NULL;
    }
    LightTLS* t = (LightTLS*)calloc(1, sizeof(LightTLS));
    if (!t) {
        snprintf(g_tls_error, sizeof(g_tls_error), "dv_tls_wrap: 内存不足");
        return NULL;
    }
    t->fd = fd;
    t->verify = g_tls_verify_default;
    if (host && host[0]) {
        strncpy(t->host, host, sizeof(t->host) - 1);
    } else {
        snprintf(g_tls_error, sizeof(g_tls_error),
                 "dv_tls_wrap: 必须给主机名（SNI + 主机名校验都要它），拒绝无名包装");
        free(t);
        return NULL;
    }
    return t;
}

int dv_tls_set_verify(LightTLS* t, int enable) {
    if (!t) return -1;
    t->verify = enable ? 1 : 0;
    if (!enable) {
        fprintf(stderr,
                "\n***** 【安全告警】TLS 证书校验已被显式关闭（host=%s）*****\n"
                "***** 该连接可被中间人劫持，仅允许在受控测试中使用    *****\n\n",
                t->host);
        fflush(stderr);
    }
    return 0;
}

int dv_tls_add_trusted_cert_file(const char* path) {
    if (!path || !path[0]) {
        snprintf(g_tls_error, sizeof(g_tls_error), "dv_tls_add_trusted_cert_file: 路径为空");
        return -1;
    }
    if (!g_tls_ca_explicit_ready) {
        mbedtls_x509_crt_init(&g_tls_ca_explicit);
        g_tls_ca_explicit_ready = 1;
    }
    /* PEM / DER 自动识别（对应 Windows CryptStringToBinary 语义） */
    int r = mbedtls_x509_crt_parse_file(&g_tls_ca_explicit, path);
    if (r != 0) {
        char ebuf[128];
        mbedtls_strerror(r, ebuf, sizeof(ebuf));
        snprintf(g_tls_error, sizeof(g_tls_error), "加入信任锚失败: %s（%s, -0x%04X）",
                 path, ebuf, (unsigned)(-r));
        return -1;
    }
    /* 一旦设置显式信任锚，即切换「独占根」：只认这一批根，比系统根更严 */
    g_tls_roots_explicit = 1;
    return 0;
}

int dv_tls_handshake(LightTLS* t) {
    if (!t) {
        snprintf(g_tls_error, sizeof(g_tls_error), "dv_tls_handshake: 句柄为空");
        return DV_TLS_ERROR;
    }
    if (t->handshake_done) return DV_TLS_OK;

    /* 上一轮没写完的先写完 */
    int fr = dv_tls_flush(t);
    if (fr != DV_TLS_OK) return fr;

    if (!t->hs_started) {
        mbedtls_ssl_init(&t->ssl);
        mbedtls_ssl_config_init(&t->conf);
        mbedtls_entropy_init(&t->entropy);
        mbedtls_ctr_drbg_init(&t->ctr_drbg);
        /* mbedTLS 硬性要求：不配 RNG 握手直接 -0x7400（No RNG provided） */
        int rs = mbedtls_ctr_drbg_seed(&t->ctr_drbg, mbedtls_entropy_func,
                                       &t->entropy, (const unsigned char*)"light-tls", 9);
        if (rs != 0) {
            char ebuf[128]; mbedtls_strerror(rs, ebuf, sizeof(ebuf));
            snprintf(g_tls_error, sizeof(g_tls_error), "mbedtls_ctr_drbg_seed 失败: %s", ebuf);
            return DV_TLS_ERROR;
        }
        int r0 = mbedtls_ssl_config_defaults(&t->conf, MBEDTLS_SSL_IS_CLIENT,
                                             MBEDTLS_SSL_TRANSPORT_STREAM,
                                             MBEDTLS_SSL_PRESET_DEFAULT);
        if (r0 != 0) {
            char ebuf[128]; mbedtls_strerror(r0, ebuf, sizeof(ebuf));
            snprintf(g_tls_error, sizeof(g_tls_error), "mbedtls_ssl_config_defaults 失败: %s", ebuf);
            return DV_TLS_ERROR;
        }
        mbedtls_ssl_conf_rng(&t->conf, mbedtls_ctr_drbg_random, &t->ctr_drbg);
        /* 校验默认开：verify=1 → REQUIRED（链 + 主机名）；verify=0 → NONE（全关，含主机名） */
        mbedtls_ssl_conf_authmode(&t->conf,
                                  t->verify ? MBEDTLS_SSL_VERIFY_REQUIRED : MBEDTLS_SSL_VERIFY_NONE);
        mbedtls_x509_crt* ca = dv_tls_get_ca_chain();
        if (ca) mbedtls_ssl_conf_ca_chain(&t->conf, ca, NULL);

        int r1 = mbedtls_ssl_setup(&t->ssl, &t->conf);
        if (r1 != 0) {
            char ebuf[128]; mbedtls_strerror(r1, ebuf, sizeof(ebuf));
            snprintf(g_tls_error, sizeof(g_tls_error), "mbedtls_ssl_setup 失败: %s", ebuf);
            return DV_TLS_ERROR;
        }
        /* 主机名：SNI + 主机名校验（verify=NONE 时该校验一并关闭） */
        int r2 = mbedtls_ssl_set_hostname(&t->ssl, t->host);
        if (r2 != 0) {
            char ebuf[128]; mbedtls_strerror(r2, ebuf, sizeof(ebuf));
            snprintf(g_tls_error, sizeof(g_tls_error), "mbedtls_ssl_set_hostname 失败: %s", ebuf);
            return DV_TLS_ERROR;
        }
        /* 队列式 BIO：发送走 out_pending（不阻塞事件循环），接收直读 socket */
        mbedtls_ssl_set_bio(&t->ssl, t, dv_tls_bio_send, dv_tls_bio_recv, NULL);
        t->hs_started = 1;
    }

    int r = mbedtls_ssl_handshake(&t->ssl);
    if (r == 0) {
        /* VERIFY_REQUIRED 下校验失败会让 handshake 返回负码；此处双保险确认 */
        if (t->verify) {
            uint32_t vr = mbedtls_ssl_get_verify_result(&t->ssl);
            if (vr != 0) {
                snprintf(g_tls_error, sizeof(g_tls_error),
                         "证书校验不通过: flags 0x%08X", (unsigned)vr);
                return DV_TLS_ERROR;
            }
        }
        t->handshake_done = 1;
        return DV_TLS_OK;
    }
    if (r == MBEDTLS_ERR_SSL_WANT_READ) return DV_TLS_WANT_READ;
    if (r == MBEDTLS_ERR_SSL_WANT_WRITE) return DV_TLS_WANT_WRITE;
    {
        char ebuf[128];
        mbedtls_strerror(r, ebuf, sizeof(ebuf));
        snprintf(g_tls_error, sizeof(g_tls_error), "TLS 握手失败: %s (-0x%04X)", ebuf, (unsigned)(-r));
    }
    return DV_TLS_ERROR;
}

int dv_tls_want_event(LightTLS* t) {
    if (!t) return DV_POLL_READ;
    if (t->out_off < t->out_len) return DV_POLL_WRITE;
    return DV_POLL_READ;
}

int dv_tls_is_ready(LightTLS* t) {
    return (t && t->handshake_done) ? 1 : 0;
}

/* 带长度的发送：返回已交给 mbedTLS 的明文字节数（全部或部分）；错误返回 -1。
 * 与 Windows 同口径：密文进 out_pending 队列，调用方等可写后调 dv_tls_flush_public。 */
int dv_tls_send_n(LightTLS* t, const char* data, int len) {
    if (!t || !t->handshake_done) {
        snprintf(g_tls_error, sizeof(g_tls_error), "dv_tls_send: 握手未完成");
        return DV_TLS_ERROR;
    }
    int fr = dv_tls_flush(t);
    if (fr != DV_TLS_OK) return fr;
    if (!data || len <= 0) return 0;
    int sent = 0;
    while (sent < len) {
        int n = mbedtls_ssl_write(&t->ssl, (const unsigned char*)(data + sent),
                                  (size_t)(len - sent));
        if (n > 0) { sent += n; continue; }
        if (n == MBEDTLS_ERR_SSL_WANT_WRITE || n == MBEDTLS_ERR_SSL_WANT_READ) {
            /* 背压 / 需要读输入（重协商）：已接受部分先返回，剩余靠 flush_public 续写 */
            (void)dv_tls_flush(t);
            return sent;
        }
        {
            char ebuf[128];
            mbedtls_strerror(n, ebuf, sizeof(ebuf));
            snprintf(g_tls_error, sizeof(g_tls_error), "TLS 发送失败: %s (-0x%04X)", ebuf, (unsigned)(-n));
        }
        return DV_TLS_ERROR;
    }
    (void)dv_tls_flush(t);
    return sent;
}

/* 旧 ABI：用 strlen 限制，不能发含 NUL 的二进制数据。等价于 dv_tls_send_n(t, data, strlen(data))。 */
int dv_tls_send(LightTLS* t, const char* data) {
    return dv_tls_send_n(t, data, data ? (int)strlen(data) : 0);
}

int dv_tls_flush_public(LightTLS* t) {
    if (!t) return DV_TLS_ERROR;
    return dv_tls_flush(t);
}

void dv_tls_recv(LightValue* result, LightTLS* t, int max_bytes) {
    if (!result) return;
    if (!t || !t->handshake_done) {
        snprintf(g_tls_error, sizeof(g_tls_error), "dv_tls_recv: 握手未完成");
        if (t) t->recv_status = DV_TLS_ERROR;
        dv_str(result, "");
        return;
    }
    if (max_bytes <= 0) max_bytes = 4096;
    if (max_bytes > 64 * 1024) max_bytes = 64 * 1024;
    unsigned char* tmp = (unsigned char*)malloc((size_t)max_bytes + 1);
    if (!tmp) {
        t->recv_status = DV_TLS_ERROR;
        snprintf(g_tls_error, sizeof(g_tls_error), "dv_tls_recv: 临时缓冲分配失败");
        dv_str(result, "");
        return;
    }
    int n = mbedtls_ssl_read(&t->ssl, tmp, (size_t)max_bytes);
    if (n > 0) {
        tmp[n] = '\0';
        t->recv_status = DV_TLS_OK;
        dv_str(result, (const char*)tmp);
        free(tmp);
        return;
    }
    if (n == 0 || n == MBEDTLS_ERR_SSL_PEER_CLOSE_NOTIFY
#ifdef MBEDTLS_ERR_SSL_CONN_EOF
        || n == MBEDTLS_ERR_SSL_CONN_EOF
#endif
       ) {
        t->peer_closed = 1;
        t->recv_status = DV_TLS_CLOSED;
        dv_str(result, "");
        free(tmp);
        return;
    }
    if (n == MBEDTLS_ERR_SSL_WANT_READ) {
        t->recv_status = DV_TLS_WANT_READ;
        dv_str(result, "");
        free(tmp);
        return;
    }
    if (n == MBEDTLS_ERR_SSL_WANT_WRITE) {
        /* 重协商需要发数据：尽力刷出队列 */
        (void)dv_tls_flush(t);
        t->recv_status = DV_TLS_WANT_READ;
        dv_str(result, "");
        free(tmp);
        return;
    }
    {
        char ebuf[128];
        mbedtls_strerror(n, ebuf, sizeof(ebuf));
        snprintf(g_tls_error, sizeof(g_tls_error), "TLS 读取失败: %s (-0x%04X)", ebuf, (unsigned)(-n));
    }
    t->recv_status = DV_TLS_ERROR;
    dv_str(result, "");
    free(tmp);
}

int dv_tls_recv_status(LightTLS* t) {
    return t ? t->recv_status : DV_TLS_ERROR;
}

void dv_tls_free(LightTLS* t) {
    if (!t) return;
    if (t->hs_started) {
        mbedtls_ssl_free(&t->ssl);
        mbedtls_ssl_config_free(&t->conf);
        mbedtls_ctr_drbg_free(&t->ctr_drbg);
        mbedtls_entropy_free(&t->entropy);
    }
    free(t->out_pending);
    free(t);
}

const char* dv_tls_backend(void) { return "mbedTLS"; }

#else  /* 未定义 LIGHT_TLS_MBEDTLS：保留 stub，保证无 mbedTLS 的 POSIX 构建不破 */

typedef struct LightTLS { int fd; } LightTLS;

static void dv_tls_unsupported(void) {
    snprintf(g_tls_error, sizeof(g_tls_error),
             "本平台未启用原生 TLS：需定义 LIGHT_TLS_MBEDTLS 并链接 mbedTLS"
             "（Ubuntu: apt install libmbedtls-dev）");
}

LightTLS* dv_tls_wrap(int fd, const char* host) {
    (void)fd; (void)host;
    dv_tls_unsupported();
    return NULL;
}
int dv_tls_handshake(LightTLS* t) { (void)t; dv_tls_unsupported(); return DV_TLS_ERROR; }
int dv_tls_send(LightTLS* t, const char* data) { (void)t; (void)data; dv_tls_unsupported(); return DV_TLS_ERROR; }
int dv_tls_send_n(LightTLS* t, const char* data, int len) { (void)t; (void)data; (void)len; dv_tls_unsupported(); return DV_TLS_ERROR; }
void dv_tls_recv(LightValue* result, LightTLS* t, int max_bytes) {
    (void)t; (void)max_bytes;
    dv_tls_unsupported();
    if (result) dv_str(result, "");
}
int dv_tls_recv_status(LightTLS* t) { (void)t; return DV_TLS_ERROR; }
void dv_tls_free(LightTLS* t) { free(t); }
int dv_tls_set_verify(LightTLS* t, int enable) { (void)t; (void)enable; dv_tls_unsupported(); return -1; }
int dv_tls_add_trusted_cert_file(const char* path) { (void)path; dv_tls_unsupported(); return -1; }
int dv_tls_want_event(LightTLS* t) { (void)t; return DV_POLL_READ; }
int dv_tls_is_ready(LightTLS* t) { (void)t; return 0; }
int dv_tls_flush_public(LightTLS* t) { (void)t; return DV_TLS_ERROR; }
const char* dv_tls_backend(void) { return "none"; }

#endif /* LIGHT_TLS_MBEDTLS */

#endif /* _WIN32 */

/* ================================================================
 * 元组运行时函数（type=23, LV_TYPE_TUPLE）
 * 复用 list_data/list_size/list_capacity 字段，与 LIST 结构一致。
 * 创建模式：dv_tuple_new 建空元组 → dv_tuple_append 逐元素追加（仅构造期）。
 * 读取：dv_tuple_get 按 i64 索引取元素克隆（含 REF deref）。
 * 长度：dv_tuple_len 返回 list_size（dv_len 也已适配 type=23）。
 * ================================================================ */

void dv_tuple_new(LightValue* result) {
    result->type = LV_TYPE_TUPLE;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = NULL;
    result->boolean = 0;
    result->list_size = 0;
    result->list_capacity = 4;
    result->list_data = (struct LightValue**)calloc(result->list_capacity, sizeof(LightValue*));
}

void dv_tuple_append(LightValue* result, LightValue* tuple, LightValue* elem) {
    LightValue* target = (result == tuple) ? result : tuple;

    if (target->type != LV_TYPE_TUPLE) {
        dv_tuple_new(result);
        target = result;
    }

    /* 跟随 REF，避免将 REF 存入元组（对齐 dv_dict_set 的教训） */
    elem = dv_deref(elem);

    /* 容量不足时扩容 */
    if (target->list_size >= target->list_capacity) {
        int new_cap = target->list_capacity * 2;
        struct LightValue** new_data = (struct LightValue**)calloc(new_cap, sizeof(LightValue*));
        if (target->list_data) {
            memcpy(new_data, target->list_data, target->list_size * sizeof(LightValue*));
            free(target->list_data);
        }
        target->list_data = new_data;
        target->list_capacity = new_cap;
    }

    /* 克隆元素并存入 */
    LightValue* stored = (LightValue*)malloc(sizeof(LightValue));
    dv_clone(stored, elem);
    target->list_data[target->list_size] = stored;
    target->list_size++;

    if (result != tuple) {
        dv_clone(result, target);
    }
}

void dv_tuple_get(LightValue* result, LightValue* tuple, int64_t index) {
    tuple = dv_deref(tuple);
    if (tuple->type != LV_TYPE_TUPLE || !tuple->list_data) {
        dv_null(result);
        return;
    }
    if (index < 0 || index >= tuple->list_size) {
        dv_null(result);
        return;
    }
    LightValue* elem = tuple->list_data[index];
    if (!elem) {
        dv_null(result);
        return;
    }
    dv_clone(result, elem);
}

int64_t dv_tuple_len(LightValue* v) {
    v = dv_deref(v);
    if (v->type != LV_TYPE_TUPLE) return 0;
    return v->list_size;
}

/* ── R10-11a 追加：字符串 rfind / rstrip ─────────────────── */

int64_t dv_str_rfind(LightValue* str, LightValue* sub) {
    str = dv_deref(str);
    sub = dv_deref(sub);
    if (str->type != 3 || sub->type != 3 || !str->str || !sub->str) return -1;
    const char* s = str->str;
    const char* sub_s = sub->str;
    size_t slen = strlen(s);
    size_t sublen = strlen(sub_s);
    if (sublen == 0) return (int64_t)dv_utf8_char_count(s);
    if (sublen > slen) return -1;
    /* 从右往左找最后一个匹配（字节级，UTF-8 自同步保证安全） */
    size_t found_byte = (size_t)-1;
    for (size_t i = slen - sublen + 1; i > 0; i--) {
        if (strncmp(s + i - 1, sub_s, sublen) == 0) {
            found_byte = i - 1;
            break;
        }
    }
    if (found_byte == (size_t)-1) return -1;
    /* 字节偏移 -> 字符偏移（对齐 dv_substr 的字符语义） */
    const unsigned char* p = (const unsigned char*)s;
    size_t off = 0;
    int64_t char_off = 0;
    while (off < found_byte) {
        off += dv_utf8_seq_len(p + off);
        char_off++;
    }
    return char_off;
}

void dv_str_rstrip(LightValue* result, LightValue* str, LightValue* chars) {
    str = dv_deref(str);
    if (str->type != 3 || !str->str) {
        dv_str(result, "");
        return;
    }
    const char* s = str->str;
    int len = (int)strlen(s);
    /* chars 为空或非字符串时，剥空白（对齐 Python str.rstrip()） */
    const char* strip_chars = NULL;
    if (chars && chars->type == 3 && chars->str) {
        strip_chars = chars->str;
    }
    int end = len;
    while (end > 0) {
        char c = s[end - 1];
        if (strip_chars) {
            /* 剥指定字符集 */
            if (strchr(strip_chars, c) == NULL) break;
        } else {
            /* 剥空白 */
            if (!isspace((unsigned char)c)) break;
        }
        end--;
    }
    int new_len = end;
    char* out = (char*)malloc(new_len + 1);
    if (out) {
        memcpy(out, s, new_len);
        out[new_len] = '\0';
    }
    result->type = 3;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = out;
    result->boolean = 0;
}

/* ════════════════════════════════════════════════════════════════════
 * T5C 追加：确定性随机数运行时（MT19937，对齐 CPython random 模块）
 * 独立函数区 —— 位于 TLS 段（B2-4，T7 所属）之后、文件末尾，
 * 与上方 dv_str_rfind / dv_str_rstrip 追加方式一致，未触碰 TLS 段。
 *
 * 设计说明（为什么是 MT19937 而非 LCG）：
 *   任务书写「确定性 LCG 伪随机」；但反跑判据要求「固定种子随机输出与
 *   Python random.seed(同种子) 对拍一致」。Python random 的确定性核心是
 *   MT19937（CPython Modules/_randommodule.c），LCG 无法与之逐位对齐。
 *   为实现可位级对拍，这里实现 MT19937（确定性、可复现），并在报告标注
 *   算法偏离（LCG → MT19937）。
 *
 * 对齐口径（与 CPython 3.14 逐位一致，本机实测）：
 *   dv_random_seed(s)  —— 取 |s|，按小端字节切 32 位字数组，
 *                          一律 init_by_array（本机 CPython 3.14.7 对
 *                          所有整数种子都走 init_by_array，实测确认；
 *                          老版本 CPython 对小种子走 init_genrand，
 *                          对拍以本机 3.14 为准，见 known_issues）。
 *   dv_random()        —— genrand_res53（random.random() 的逐位实现）。
 *   dv_random_bits(k)  —— getrandbits(k)，0<=k<=63 逐位对齐；k<=0 返回 0；
 *                          k>63 按 63 截断（原生腿 i64 上限，见 known_issues）。
 *   未初始化（未调用过 播种随机种子）时按当前时间自动播种，
 *   对齐 CPython Random() 构造时的系统熵自动播种（非确定）。
 * ════════════════════════════════════════════════════════════════════ */

#define LIGHT_RAND_N 624
#define LIGHT_RAND_M 397
#define LIGHT_RAND_MATRIX_A 0x9908b0dfU
#define LIGHT_RAND_UPPER_MASK 0x80000000U
#define LIGHT_RAND_LOWER_MASK 0x7fffffffU

static uint32_t dv_rand_mt[LIGHT_RAND_N];
static int dv_rand_mti = LIGHT_RAND_N + 1; /* N+1 = 未初始化标记 */

/* 前向声明（dv_rand_genrand 未初始化分支中调用） */
void dv_random_seed(int64_t seed);

/* init_genrand —— MT19937 经典单值播种（init_by_array 内部使用） */
static void dv_rand_init_genrand(uint32_t s) {
    int mti;
    dv_rand_mt[0] = s;
    for (mti = 1; mti < LIGHT_RAND_N; mti++) {
        dv_rand_mt[mti] =
            (1812433253U * (dv_rand_mt[mti - 1] ^ (dv_rand_mt[mti - 1] >> 30)) + (uint32_t)mti);
    }
    dv_rand_mti = mti;
}

/* init_by_array —— 对齐 CPython（小端 32 位字数组） */
static void dv_rand_init_by_array(uint32_t init_key[], int key_length) {
    int i, j, k;
    dv_rand_init_genrand(19650218U);
    i = 1;
    j = 0;
    k = (LIGHT_RAND_N > key_length) ? LIGHT_RAND_N : key_length;
    for (; k; k--) {
        dv_rand_mt[i] = (dv_rand_mt[i] ^
            ((dv_rand_mt[i - 1] ^ (dv_rand_mt[i - 1] >> 30)) * 1664525U))
            + init_key[j] + (uint32_t)j;
        i++;
        j++;
        if (i >= LIGHT_RAND_N) {
            dv_rand_mt[0] = dv_rand_mt[LIGHT_RAND_N - 1];
            i = 1;
        }
        if (j >= key_length) j = 0;
    }
    for (k = LIGHT_RAND_N - 1; k; k--) {
        dv_rand_mt[i] = (dv_rand_mt[i] ^
            ((dv_rand_mt[i - 1] ^ (dv_rand_mt[i - 1] >> 30)) * 1566083941U))
            - (uint32_t)i;
        i++;
        if (i >= LIGHT_RAND_N) {
            dv_rand_mt[0] = dv_rand_mt[LIGHT_RAND_N - 1];
            i = 1;
        }
    }
    dv_rand_mt[0] = 0x80000000U;
}

/* genrand_uint32 —— 对齐 CPython genrand_uint32（标准 MT19937 扭结） */
static uint32_t dv_rand_genrand(void) {
    uint32_t y;
    static const uint32_t mag01[2] = {0x0U, LIGHT_RAND_MATRIX_A};
    uint32_t *mt = dv_rand_mt;

    if (dv_rand_mti >= LIGHT_RAND_N) {
        int kk;
        if (dv_rand_mti == LIGHT_RAND_N + 1) {
            /* 未初始化：按当前时间自动播种（对齐 CPython 构造时自动播种） */
            dv_random_seed((int64_t)(dv_timestamp() * 1000.0));
        }
        for (kk = 0; kk < LIGHT_RAND_N - LIGHT_RAND_M; kk++) {
            y = (mt[kk] & LIGHT_RAND_UPPER_MASK) | (mt[kk + 1] & LIGHT_RAND_LOWER_MASK);
            mt[kk] = mt[kk + LIGHT_RAND_M] ^ (y >> 1) ^ mag01[y & 0x1U];
        }
        for (; kk < LIGHT_RAND_N - 1; kk++) {
            y = (mt[kk] & LIGHT_RAND_UPPER_MASK) | (mt[kk + 1] & LIGHT_RAND_LOWER_MASK);
            mt[kk] = mt[kk + (LIGHT_RAND_M - LIGHT_RAND_N)] ^ (y >> 1) ^ mag01[y & 0x1U];
        }
        y = (mt[LIGHT_RAND_N - 1] & LIGHT_RAND_UPPER_MASK) | (mt[0] & LIGHT_RAND_LOWER_MASK);
        mt[LIGHT_RAND_N - 1] = mt[LIGHT_RAND_M - 1] ^ (y >> 1) ^ mag01[y & 0x1U];
        dv_rand_mti = 0;
    }

    y = mt[dv_rand_mti++];
    y ^= (y >> 11);
    y ^= (y << 7) & 0x9d2c5680U;
    y ^= (y << 15) & 0xefc60000U;
    y ^= (y >> 18);
    return y;
}

/* 播种 —— 对齐 CPython 3.14 random.seed(整数)：
 *   负种子取绝对值；一律按小端 32 位字切分后 init_by_array
 *   （本机 CPython 3.14.7 实测：所有整数种子均走 init_by_array）。 */
void dv_random_seed(int64_t seed) {
    uint64_t u = (seed < 0) ? (uint64_t)(-(seed + 1)) + 1 : (uint64_t)seed;
    uint32_t words[4];
    int n = 0;
    while (u > 0 && n < 4) {
        words[n++] = (uint32_t)(u & 0xFFFFFFFFULL);
        u >>= 32;
    }
    if (n == 0) {
        words[n++] = 0; /* seed 0 → 键 [0]（CPython 一致） */
    }
    dv_rand_init_by_array(words, n);
}

/* 随机0到1 —— genrand_res53，与 Python random.random() 逐位一致 */
double dv_random(void) {
    uint32_t a = dv_rand_genrand() >> 5;
    uint32_t b = dv_rand_genrand() >> 6;
    return (a * 67108864.0 + b) / 9007199254740992.0;
}

/* 随机位 —— getrandbits(k)，k<=63 逐位对齐 CPython；k<=0 返回 0；k>63 按 63 截断 */
int64_t dv_random_bits(int64_t k) {
    int64_t kk = k;
    if (kk <= 0) return 0;
    if (kk > 63) kk = 63;
    int words = (int)((kk - 1) / 32 + 1);
    uint32_t w0 = dv_rand_genrand();
    uint32_t w1 = (words > 1) ? dv_rand_genrand() : 0;
    if (words == 1) {
        /* 单个字：右移保留高 kk 位（CPython: wordarray[words-1] >>= (32 - k%32)%32） */
        w0 >>= (32 - (int)(kk % 32)) % 32;
    } else {
        w1 >>= (32 - (int)(kk % 32)) % 32;
    }
    return (int64_t)w0 | ((int64_t)w1 << 32);
}

/* ════════════════════════════════════════════════════════════════════
 * T6B 追加：时间/系统内建 runtime（dv_sleep / dv_clock）
 * 独立函数区 —— 位于文件末尾，未触碰上方 TLS 段（B2-4，T7 所属）。
 *
 * 设计说明：
 *   dv_sleep(sec)  —— 秒级睡眠（double），对齐 Python time.sleep()。
 *                      已有 dv_platform_sleep(int ms) 是事件循环内部毫秒级，
 *                      在 B2-4 区；本函数独立实现、供 time.light 暴露秒级睡眠。
 *   dv_clock()     —— 单调高分辨率时钟秒（double），对齐 Python
 *                      time.perf_counter() / time.monotonic() 的语义
 *                      （单调、不受系统时间调整影响）。
 * ════════════════════════════════════════════════════════════════════ */

void dv_sleep(double sec) {
    if (sec <= 0) return;
#ifdef _WIN32
    Sleep((DWORD)(sec * 1000.0 + 0.5));
#else
    struct timespec ts;
    ts.tv_sec = (time_t)sec;
    ts.tv_nsec = (long)((sec - (double)ts.tv_sec) * 1000000000.0);
    if (ts.tv_nsec < 0) ts.tv_nsec = 0;
    if (ts.tv_nsec >= 1000000000L) { ts.tv_sec += 1; ts.tv_nsec -= 1000000000L; }
    nanosleep(&ts, NULL);
#endif
}

double dv_clock(void) {
#ifdef _WIN32
    static LARGE_INTEGER freq = {0};
    if (freq.QuadPart == 0) QueryPerformanceFrequency(&freq);
    LARGE_INTEGER now;
    QueryPerformanceCounter(&now);
    return (double)now.QuadPart / (double)freq.QuadPart;
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec / 1000000000.0;
#endif
}
