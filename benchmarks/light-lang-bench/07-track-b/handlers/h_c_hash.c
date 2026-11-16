/* MiniBridge · h_c_hash（B2 handler，C）
 *
 * 契约（见 ../规格.md §3.3）：
 *   输入：一行 UTF-8 字节（stdin），行尾 \r\n 剥离后算值。
 *   行为：对该行的 UTF-8 字节序列算 FNV-1a 64，取**低 32 位**。
 *   输出：`HASH <低32位十进制>` 单行（CLI 形态）；或由调用方取值（.so 形态）。
 *
 * **唯一真身**：同一个文件编译出两个产物，绝无「另一份碰巧一样的实现」：
 *
 *   (a) B2 · 真实 FFI —— `-shared -fPIC` 编成 libh_c_hash.so，
 *       光明侧 `mb_cffi.light` 的 `引 C:` 块编译同源 C，ctypes 直调 mb_fnv1a32。
 *   (b) B1 · 进程编排 —— `-DMB_HASH_CLI` 编成可执行文件 h_c_hash，
 *       被 `mb_进程.light` 当普通外部进程起（规格 §3.1 的 handler 调用约定）。
 *
 * 之所以 B1 也要一个真正的 C 可执行文件、而不是用 Python 顶替：规格 §4.2(3)
 * 明令禁止「让别的语言假装 C」。两个产物同源，算法的正确性由
 * tests/selfcheck_handlers.sh 交叉对拍保证。
 *
 * 不用 libc 的 strlen：自己走到 NUL 为止，.so 在任何 POSIX 上都能裸加载。
 */

#include <stdio.h>
#include <string.h>

/* FNV-1a 64 位参数（规范常量，勿改） */
#define MB_FNV_OFFSET_BASIS 14695981039346656037ULL
#define MB_FNV_PRIME 1099511628211ULL

/*
 * 对以 NUL 结尾的 UTF-8 C 字符串算 FNV-1a 64 并返回低 32 位。
 * 返回值用 long long 而非 unsigned int：ctypes 侧按 长整数 绑定（c_longlong），
 * 避免「无符号 → 有符号」宽度不一致导致的符号位翻转；调用方再做 & 0xFFFFFFFF。
 */
long long mb_fnv1a32(const char *s) {
    unsigned long long h = MB_FNV_OFFSET_BASIS;
    const unsigned char *p = (const unsigned char *)s;
    if (p != 0) {
        while (*p != 0) {
            h ^= (unsigned long long)(*p);
            h *= MB_FNV_PRIME;
            ++p;
        }
    }
    return (long long)(h & 0xFFFFFFFFULL);
}

/*
 * 定长版本：给「已剥离行尾但仍然可能含 \0 的输入」用。
 * B2 主路径只用 mb_fnv1a32；本函数保留给自测与交叉对拍。
 */
long long mb_fnv1a32_n(const char *s, long long n) {
    unsigned long long h = MB_FNV_OFFSET_BASIS;
    const unsigned char *p = (const unsigned char *)s;
    long long i;
    if (p == 0 || n <= 0) {
        return (long long)(h & 0xFFFFFFFFULL);
    }
    for (i = 0; i < n; ++i) {
        h ^= (unsigned long long)(p[i]);
        h *= MB_FNV_PRIME;
    }
    return (long long)(h & 0xFFFFFFFFULL);
}

/* ------------------------------------------------------------------ */
/* B1 CLI 形态：只在 -DMB_HASH_CLI 时编进可执行文件，.so 里没有 main。   */
/* ------------------------------------------------------------------ */
#ifdef MB_HASH_CLI

#define MB_CLI_MAX 1048576

int main(void) {
    static char buf[MB_CLI_MAX + 2];
    size_t n;

    if (fgets(buf, (int)sizeof(buf), stdin) == 0) {
        fprintf(stderr, "ERR empty_input\n");
        return 1;
    }
    n = strlen(buf);
    /* 剥离行尾 \n 与 \r（CRLF 输入），与规格 §3.2「先行剥离再算字节」一致。 */
    while (n > 0 && (buf[n - 1] == '\n' || buf[n - 1] == '\r')) {
        buf[n - 1] = 0;
        --n;
    }
    if (n == 0) {
        fprintf(stderr, "ERR empty_input\n");
        return 1;
    }
    printf("HASH %lld\n", mb_fnv1a32(buf));
    return 0;
}

#endif /* MB_HASH_CLI */
