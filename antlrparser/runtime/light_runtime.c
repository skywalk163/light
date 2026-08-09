/*
 * 光明 (Light) 运行时库 - 完整版 v2
 * 基于字符串的动态类型系统，支持记账程序所需全部功能
 * 
 * 所有值统一存储为 char* (字符串)
 * 列表存储为 "list:N:elem0|elem1|..." 格式
 * 数字存储为字符串形式
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sys/stat.h>

#ifdef _WIN32
#include <windows.h>
#include <io.h>
#define F_OK 0
#define access _access
#else
#include <unistd.h>
#endif

// ====================================
// 内存工具
// ====================================

static char* light_strdup(const char* s) {
    if (!s) return NULL;
    size_t len = strlen(s);
    char* d = (char*)malloc(len + 1);
    if (d) memcpy(d, s, len + 1);
    return d;
}

// ====================================
// 输入输出
// ====================================

char* light_input(void) {
    static char buffer[4096];
    if (fgets(buffer, sizeof(buffer), stdin)) {
        size_t len = strlen(buffer);
        if (len > 0 && buffer[len-1] == '\n') buffer[len-1] = '\0';
        if (len > 1 && buffer[len-2] == '\r') buffer[len-2] = '\0';
        return light_strdup(buffer);
    }
    return light_strdup("");
}

void light_print(const char* s) {
    if (s) printf("%s", s);
}

void light_println(const char* s) {
    if (s) printf("%s\n", s);
}

void light_print_int(int n) {
    printf("%d\n", n);
}

// ====================================
// 字符串操作
// ====================================

char* light_concat(const char* a, const char* b) {
    if (!a) a = "";
    if (!b) b = "";
    size_t la = strlen(a), lb = strlen(b);
    char* r = (char*)malloc(la + lb + 1);
    if (r) {
        memcpy(r, a, la);
        memcpy(r + la, b, lb);
        r[la + lb] = '\0';
    }
    return r;
}

char* light_concat3(const char* a, const char* b, const char* c) {
    char* tmp = light_concat(a, b);
    char* r = light_concat(tmp, c);
    free(tmp);
    return r;
}

int light_str_eq(const char* a, const char* b) {
    if (!a && !b) return 1;
    if (!a || !b) return 0;
    return strcmp(a, b) == 0;
}

int light_str_len(const char* s) {
    return s ? (int)strlen(s) : 0;
}

// ====================================
// 数字转换
// ====================================

char* light_itoa(int n) {
    char* r = (char*)malloc(32);
    if (r) sprintf(r, "%d", n);
    return r;
}

int light_atoi(const char* s) {
    return s ? atoi(s) : 0;
}

double light_atof(const char* s) {
    return s ? atof(s) : 0.0;
}

char* light_ftoa(double d) {
    char* r = (char*)malloc(64);
    if (r) {
        sprintf(r, "%g", d);
        // 如果是整数形式，去掉 .0
        char* dot = strchr(r, '.');
        if (dot && dot[1] == '\0') *dot = '\0';
    }
    return r;
}

// ====================================
// 列表操作（格式: "list:N:elem0|elem1|..."）
// ====================================

char* light_list_new(void) {
    return light_strdup("list:0:");
}

int light_list_len(const char* list) {
    if (!list || strncmp(list, "list:", 5) != 0) return 0;
    return atoi(list + 5);
}

// 辅助函数：找到元素结束位置（处理嵌套）
// 如果元素以 "list:" 开头，读取 N 字段（元素数）并跳过 N-1 个 \x1f 分隔符
// 然后从最后一个元素开始扫描到字符串结尾（即包含最后一个元素的内容）
// 返回：元素内容结束位置（指向元素最后一个字节的下一个字节）
//   - 如果元素是普通元素：返回下一个 \x1f 位置
//   - 如果元素是嵌套 list：返回嵌套 list 字符串结尾
//   - 如果是最后一个元素：返回字符串结尾
static const char* find_elem_end(const char* p) {
    if (strncmp(p, "list:", 5) == 0) {
        // 嵌套 list：读取元素数 N
        p += 5;
        const char* colon = strchr(p, ':');
        if (!colon) return NULL;
        int n = atoi(p);
        p = colon + 1;
        // 跳过 N-1 个 \x1f 分隔符
        for (int i = 0; i < n - 1; i++) {
            const char* sep = strchr(p, '\x1f');
            if (!sep) return NULL;
            p = sep + 1;
        }
        // 现在 p 指向最后一个元素。扫描到字符串结尾
        while (*p) p++;
        return p;
    } else {
        // 普通元素：找下一个 \x1f 或字符串结尾
        const char* sep = strchr(p, '\x1f');
        if (!sep) return p + strlen(p);
        return sep;
    }
}

char* light_list_get(const char* list, int index) {
    if (!list || strncmp(list, "list:", 5) != 0) return light_strdup("");
    // 格式: "list:N:elem0\x1felem1\x1felem2\x1f..."
    // 跳过 "list:" 前缀和长度数字
    const char* p = list + 5;
    p = strchr(p, ':');
    if (!p) return light_strdup("");
    p++; // 指向第一个元素
    // 跳过 index 个元素
    for (int i = 0; i < index; i++) {
        const char* end = find_elem_end(p);
        if (!end) return light_strdup("");
        // end 指向分隔符 (\x1f) 或字符串结尾
        if (*end == '\0') return light_strdup(""); // 已经到达结尾
        p = end + 1; // 跳过 \x1f
    }
    // 找到当前元素结束位置
    const char* end = find_elem_end(p);
    if (!end) return light_strdup("");
    // end 指向 \x1f 或 null，所以 len = end - p 不含分隔符
    size_t len = end - p;
    char* r = (char*)malloc(len + 1);
    if (r) { memcpy(r, p, len); r[len] = '\0'; }
    // 不要替换 \x1f 为 |，保持数据完整性，让调用方决定如何显示
    return r;
}

char* light_list_append(char* list, const char* elem) {
    if (!list || strncmp(list, "list:", 5) != 0) {
        free(list);
        list = light_list_new();
    }
    if (!elem) elem = "";
    
    int len = light_list_len(list);
    char* prefix = (char*)malloc(32);
    sprintf(prefix, "list:%d:", len + 1);
    
    // 找到数据部分：跳过 "list:" 和数字，再跳过 ":"
    const char* data_ptr = strchr(list + 5, ':');
    if (!data_ptr) data_ptr = list + 5;
    else data_ptr++; // 跳过 ":"
    
    // 复制数据部分（避免悬空指针问题）
    size_t data_len = strlen(data_ptr);
    char* data_copy = (char*)malloc(data_len + 1);
    if (data_copy) {
        memcpy(data_copy, data_ptr, data_len + 1);
    }
    
    size_t new_size = strlen(prefix) + strlen(data_copy) + strlen(elem) + 2;
    char* r = (char*)malloc(new_size);
    if (r) {
        if (*data_copy) {
            // 使用 \x1f 作为元素分隔符（避免与子列表内的 | 冲突）
            sprintf(r, "%s%s\x1f%s", prefix, data_copy, elem);
        } else {
            sprintf(r, "%s%s", prefix, elem);
        }
    }
    free(prefix);
    free(data_copy);
    free(list);
    return r;
}

char* light_list_clear(char* list) {
    free(list);
    return light_list_new();
}

// ====================================
// 时间函数
// ====================================

double light_timestamp(void) {
    return (double)time(NULL);
}

char* light_format_time(double ts, const char* fmt) {
    if (!fmt) fmt = "%Y-%m-%d %H:%M:%S";
    time_t t = (time_t)ts;
    struct tm* tm_info = localtime(&t);
    char buffer[256];
    strftime(buffer, sizeof(buffer), fmt, tm_info);
    return light_strdup(buffer);
}

// ====================================
// 文件操作
// ====================================

int light_file_exists(const char* path) {
    if (!path) return 0;
    return access(path, F_OK) == 0;
}

char* light_read_file(const char* path) {
    if (!path) return light_strdup("");
    FILE* f = fopen(path, "rb");
    if (!f) return light_strdup("");
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);
    char* buf = (char*)malloc(size + 1);
    if (buf) {
        fread(buf, 1, size, f);
        buf[size] = '\0';
    }
    fclose(f);
    return buf ? buf : light_strdup("");
}

void light_write_file(const char* path, const char* content) {
    if (!path || !content) return;
    FILE* f = fopen(path, "wb");
    if (f) {
        fwrite(content, 1, strlen(content), f);
        fclose(f);
    }
}

// ====================================
// JSON 操作（简易实现）
// ====================================

// 将列表序列化为 JSON 数组
char* light_list_to_json(const char* list, int indent) {
    if (!list || strncmp(list, "list:", 5) != 0) return light_strdup("[]");
    int len = light_list_len(list);
    
    // 估算大小
    size_t est = 4;
    for (int i = 0; i < len; i++) {
        char* elem = light_list_get(list, i);
        if (elem) {
            // 检测是否是嵌套列表
            if (strncmp(elem, "list:", 5) == 0) {
                char* sub = light_list_to_json(elem, indent);
                est += strlen(sub) + 2;
                free(sub);
            } else {
                est += strlen(elem) + 4; // 引号和逗号
            }
            free(elem);
        }
    }
    
    char* r = (char*)malloc(est + indent * 2);
    if (!r) return light_strdup("[]");
    
    char* wp = r;
    *wp++ = '[';
    if (indent > 0) { *wp++ = '\n'; }
    
    for (int i = 0; i < len; i++) {
        char* elem = light_list_get(list, i);
        if (indent > 0) {
            for (int s = 0; s < indent; s++) *wp++ = ' ';
        }
        
        if (elem) {
            if (strncmp(elem, "list:", 5) == 0) {
                char* sub = light_list_to_json(elem, indent > 0 ? indent + 2 : 0);
                size_t slen = strlen(sub);
                memcpy(wp, sub, slen);
                wp += slen;
                free(sub);
            } else {
                // 判断是否是数字
                int is_num = 1;
                for (char* c = elem; *c; c++) {
                    if (*c != '-' && *c != '.' && (*c < '0' || *c > '9')) {
                        is_num = 0;
                        break;
                    }
                }
                if (is_num && *elem) {
                    size_t elen = strlen(elem);
                    memcpy(wp, elem, elen);
                    wp += elen;
                } else {
                    *wp++ = '"';
                    size_t elen = strlen(elem);
                    memcpy(wp, elem, elen);
                    wp += elen;
                    *wp++ = '"';
                }
            }
            free(elem);
        }
        
        if (i < len - 1) *wp++ = ',';
        if (indent > 0) *wp++ = '\n';
    }
    
    if (indent > 0 && len > 0) {
        for (int s = 0; s < indent - 2; s++) *wp++ = ' ';
    }
    *wp++ = ']';
    *wp = '\0';
    return r;
}

// 简易 JSON 解析器 - 将 JSON 数组解析为列表
char* light_json_parse(const char* json) {
    if (!json) return light_list_new();
    // 跳过空白
    while (*json == ' ' || *json == '\n' || *json == '\r' || *json == '\t') json++;
    if (*json != '[') return light_list_new();
    json++;
    
    char* list = light_list_new();
    
    while (*json) {
        while (*json == ' ' || *json == '\n' || *json == '\r' || *json == '\t' || *json == ',') json++;
        if (*json == ']') break;
        
        if (*json == '[') {
            // 嵌套数组
            const char* start = json;
            int depth = 1;
            json++;
            while (*json && depth > 0) {
                if (*json == '[') depth++;
                if (*json == ']') depth--;
                json++;
            }
            size_t len = json - start;
            char* sub = (char*)malloc(len + 1);
            if (sub) {
                memcpy(sub, start, len);
                sub[len] = '\0';
                char* parsed = light_json_parse(sub);
                list = light_list_append(list, parsed);
                free(parsed);
                free(sub);
            }
        } else if (*json == '"') {
            json++;
            const char* start = json;
            while (*json && *json != '"') {
                if (*json == '\\') json++;
                if (*json) json++;
            }
            size_t len = json - start;
            char* str = (char*)malloc(len + 1);
            if (str) {
                memcpy(str, start, len);
                str[len] = '\0';
                list = light_list_append(list, str);
                free(str);
            }
            if (*json == '"') json++;
        } else if (*json == ']') {
            break;
        } else {
            // 数字或布尔值
            const char* start = json;
            while (*json && *json != ',' && *json != ']' && *json != ' ' && *json != '\n') json++;
            size_t len = json - start;
            char* num = (char*)malloc(len + 1);
            if (num) {
                memcpy(num, start, len);
                num[len] = '\0';
                list = light_list_append(list, num);
                free(num);
            }
        }
    }
    return list;
}

// ====================================
// 简单测试 main
// ====================================
#ifdef DUAN_RUNTIME_TEST
int main() {
    printf("=== 光明运行时测试 ===\n");
    
    char* list = light_list_new();
    list = light_list_append(list, "hello");
    list = light_list_append(list, "world");
    list = light_list_append(list, "123");
    printf("列表长度: %d\n", light_list_len(list));
    printf("列表[0]: %s\n", light_list_get(list, 0));
    printf("列表[1]: %s\n", light_list_get(list, 1));
    
    char* json = light_list_to_json(list, 2);
    printf("JSON: %s\n", json);
    
    char* parsed = light_json_parse(json);
    printf("解析后长度: %d\n", light_list_len(parsed));
    
    printf("时间戳: %f\n", light_timestamp());
    printf("格式化时间: %s\n", light_format_time(light_timestamp(), "%Y-%m-%d %H:%M:%S"));
    
    char* input = light_input();
    printf("输入: %s\n", input);
    
    free(list);
    free(json);
    free(parsed);
    free(input);
    return 0;
}
#endif