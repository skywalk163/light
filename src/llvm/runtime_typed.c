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
    if (a->type == 3 && b->type == 3) {
        return (a->str && b->str && strcmp(a->str, b->str) == 0) ||
               (!a->str && !b->str);
    }
    if (a->type == 2 || b->type == 2) {
        return dv_to_f64(a) == dv_to_f64(b);
    }
    return dv_to_i64(a) == dv_to_i64(b);
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
    if (str->type != 3 || !str->str) {
        dv_str(result, "");
        return;
    }
    const char* s = str->str;
    int64_t slen = (int64_t)strlen(s);
    if (start < 0) start = slen + start;
    if (start < 0) start = 0;
    if (start >= slen) {
        dv_str(result, "");
        return;
    }
    if (len < 0) len = slen - start;
    if (start + len > slen) len = slen - start;
    char* out = (char*)malloc(len + 1);
    if (out) {
        memcpy(out, s + start, len);
        out[len] = '\0';
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
        return (int64_t)strlen(s);
    }
    if (v->type == 4) {
        return v->list_size;
    }
    if (v->type == 7) {
        /* DICT: list_size 是键值对数量 */
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

void dv_str_get(LightValue* result, LightValue* str_val, int64_t index) {
    if (str_val->type != 3) {
        dv_null(result);
        return;
    }
    const char* s = str_val->str ? str_val->str : "";
    int64_t len = (int64_t)strlen(s);
    if (index < 0 || index >= len) {
        dv_null(result);
        return;
    }
    char buf[2];
    buf[0] = s[index];
    buf[1] = '\0';
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

void dv_class_new(LightValue* result, int num_fields) {
    char prefix[32];
    snprintf(prefix, sizeof(prefix), "%s%d:", OBJ_PREFIX, num_fields);
    result->type = 3;
    result->i64 = 0;
    result->f64 = 0.0;
    result->str = dv_strdup(prefix);
    result->boolean = 0;
}

void dv_class_set_member(LightValue* obj, const char* field_name, LightValue* value) {
    if (!obj || obj->type != 3 || !obj->str) return;
    if (strncmp(obj->str, OBJ_PREFIX, strlen(OBJ_PREFIX)) != 0) return;
    
    char* field_str = dv_to_string(value);
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
        method(result, &cls_val, args, num_args);
    } else if (method_flag == 2) {
        /* 静态方法：签名 void func(result, args, num_args) */
        LightStaticMethodFunc method = (LightStaticMethodFunc)func_ptr;
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
        method(result, args, num_args);
    } else if (method_flag == 1) {
        /* 类方法也可以通过静态方式调用，传入类名 */
        LightValue cls_val;
        dv_str(&cls_val, class_name);
        LightClassMethodFunc method = (LightClassMethodFunc)func_ptr;
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
            strncpy(buf, "空", buf_size - 1);
            buf[buf_size - 1] = '\0';
            break;
        case 1:
            strncpy(buf, "整数", buf_size - 1);
            buf[buf_size - 1] = '\0';
            break;
        case 2:
            strncpy(buf, "浮点数", buf_size - 1);
            buf[buf_size - 1] = '\0';
            break;
        case 3:
            if (obj->str && strncmp(obj->str, OBJ_PREFIX, strlen(OBJ_PREFIX)) == 0) {
                dv_get_class_name(obj, buf, buf_size);
            } else if (obj->str && strncmp(obj->str, "list:", 5) == 0) {
                strncpy(buf, "列表", buf_size - 1);
                buf[buf_size - 1] = '\0';
            } else {
                strncpy(buf, "文本", buf_size - 1);
                buf[buf_size - 1] = '\0';
            }
            break;
        case 4:
            strncpy(buf, "列表", buf_size - 1);
            buf[buf_size - 1] = '\0';
            break;
        case 5:
            strncpy(buf, "布尔", buf_size - 1);
            buf[buf_size - 1] = '\0';
            break;
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
 * B2: IO 多路复用 (select-based poller)
 * ================================================================ */

#define DV_POLL_READ  1
#define DV_POLL_WRITE 2
#define DV_POLLER_MAX 256

typedef struct {
    int registered_fds[DV_POLLER_MAX];
    int registered_events[DV_POLLER_MAX];
    int num_registered;
#ifdef _WIN32
    fd_set read_fds;
    fd_set write_fds;
#else
    fd_set read_fds;
    fd_set write_fds;
    int max_fd;
#endif
} LightPoller;

LightPoller* dv_poller_create(void) {
    LightPoller* p = (LightPoller*)calloc(1, sizeof(LightPoller));
    return p;
}

int dv_poller_register(LightPoller* p, int fd, int events) {
    if (!p || p->num_registered >= DV_POLLER_MAX) return -1;
    /* 检查是否已注册 */
    for (int i = 0; i < p->num_registered; i++) {
        if (p->registered_fds[i] == fd) {
            p->registered_events[i] = events;
            return 0;
        }
    }
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

int dv_poller_wait(LightPoller* p, int timeout_ms, int* out_fds, int* out_events) {
    if (!p || p->num_registered == 0) return 0;

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
    for (int i = 0; i < p->num_registered && count < 256; i++) {
        int fd = p->registered_fds[i];
        int events = 0;
        if (FD_ISSET(fd, &p->read_fds)) events |= DV_POLL_READ;
        if (FD_ISSET(fd, &p->write_fds)) events |= DV_POLL_WRITE;
        if (events) {
            out_fds[count] = fd;
            out_events[count] = events;
            count++;
        }
    }
    return count;
}

void dv_poller_destroy(LightPoller* p) {
    if (p) free(p);
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

/* 让当前协程挂起等待 IO */
void dv_coro_await_io(LightCoroutine* coro, int fd, int events) {
    if (!coro || fd < 0) return;
    if (!g_poller) g_poller = dv_poller_create();
    dv_poller_register(g_poller, fd, events);

    LightIOWait* entry = (LightIOWait*)calloc(1, sizeof(LightIOWait));
    if (!entry) return;
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
            int out_fds[256];
            int out_events[256];
            int ready = dv_poller_wait(g_poller, poll_timeout, out_fds, out_events);

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
        } else if (poll_timeout > 0) {
            /* 只有定时器，没有IO等待：睡眠到下一个定时器到期 */
            dv_platform_sleep(poll_timeout);
            dv_process_timers();
        }
    }
}
