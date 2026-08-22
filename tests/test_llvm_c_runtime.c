/*
 * Pure C layer unit tests for runtime_typed.c (Task B2-2 option c)
 *
 * Directly tests dv_socket_*, dv_poller_*, dv_scheduler_run_event_loop
 * WITHOUT going through LLVM IR generation. This gives the C runtime
 * a real green that is independent of the codegen pipeline.
 *
 * Compile (clang): clang -O2 -o _taskB2_c_test.exe tests/test_llvm_c_runtime.c -lws2_32
 * Compile (MSVC):  cl /O2 /utf-8 /D_CRT_SECURE_NO_WARNINGS tests/test_llvm_c_runtime.c /Fe:_taskB2_c_test.exe /link ws2_32.lib
 * Run: _taskB2_c_test.exe <echo_server_port>
 *
 * Exit code 0 = all pass, 1 = at least one failure.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Include runtime directly - it has no main() */
#include "../src/llvm/runtime_typed.c"

#ifndef _WIN32
#include <sys/resource.h>
/* 把本进程的 fd 软上限抬到 need+32。
 *
 * 超容量用例要真开到 FD_SETSIZE 以上（POSIX 上是 1024+），而 FreeBSD/Linux 的
 * 默认软上限常常就卡在 1024 附近，不抬的话 socket() 会先于 poller 判据失败，
 * 「上限生效」这条断言就变成了「环境不够用」。只动软上限、且不超过硬上限，
 * 抬不动就返回 -1 让调用方把实情打出来，不静默降级。 */
static int raise_fd_limit(int need) {
    struct rlimit rl;
    rlim_t target;
    if (getrlimit(RLIMIT_NOFILE, &rl) != 0) return -1;
    target = (rlim_t)need + 32;
    if (rl.rlim_cur >= target) return (int)rl.rlim_cur;
    if (rl.rlim_max != RLIM_INFINITY && target > rl.rlim_max) target = rl.rlim_max;
    rl.rlim_cur = target;
    if (setrlimit(RLIMIT_NOFILE, &rl) != 0) return -1;
    return (int)target;
}
#endif


static int tests_total = 0;
static int tests_passed = 0;
static int tests_failed = 0;

static void test_pass(const char* name) {
    tests_total++;
    tests_passed++;
    printf("[PASS] %s\n", name);
}

static void test_fail(const char* name, const char* detail) {
    tests_total++;
    tests_failed++;
    printf("[FAIL] %s: %s\n", name, detail ? detail : "");
}

static void test_check(const char* name, int condition, const char* detail) {
    if (condition) {
        test_pass(name);
    } else {
        test_fail(name, detail);
    }
}

int main(int argc, char** argv) {
    int port = 19150;
    if (argc > 1) port = atoi(argv[1]);

    printf("=== C Layer Unit Tests (port=%d) ===\n", port);

    /* ====== B1: Socket Primitives ====== */

    /* Test 1: socket create */
    int fd = dv_socket_create(2, 1); /* AF_INET, SOCK_STREAM */
    test_check("dv_socket_create(AF_INET,SOCK_STREAM)", fd >= 0, "socket fd < 0");

    /* Test 2: socket connect */
    int ret = dv_socket_connect(fd, "127.0.0.1", port);
    test_check("dv_socket_connect(127.0.0.1,port)", ret == 0, "connect failed");

    /* Test 3: socket send */
    int sent = -1;
    if (ret == 0) {
        sent = dv_socket_send(fd, "hello_c_unit");
    }
    test_check("dv_socket_send(hello_c_unit)", sent > 0, "send returned <= 0");

    /* Test 4: socket recv (echo) */
    int recv_ok = 0;
    if (sent > 0) {
        LightValue result;
        memset(&result, 0, sizeof(result));
        dv_socket_recv(&result, fd, 1024);
        recv_ok = (result.type == 3 && result.str && strstr(result.str, "hello_c_unit") != NULL);
    }
    test_check("dv_socket_recv(echo=hello_c_unit)", recv_ok, "recv data mismatch");

    /* Test 5: socket close */
    int cl = dv_socket_close(fd);
    test_check("dv_socket_close", cl == 0, "close failed");

    /* Test 6: socket create invalid params */
    int bad_fd = dv_socket_create(999, 999);
    test_check("dv_socket_create(invalid)->-1", bad_fd < 0, "should return < 0 for invalid params");

    /* Test 7: socket connect to nonexistent server */
    int fail_fd = dv_socket_create(2, 1);
    int fail_ret = dv_socket_connect(fail_fd, "127.0.0.1", 19198); /* nothing listening */
    test_check("dv_socket_connect(nonexistent)->-1", fail_ret < 0, "should fail to connect");
    if (fail_fd >= 0) dv_socket_close(fail_fd);

    /* Test 8: socket set_nonblocking */
    fd = dv_socket_create(2, 1);
    if (fd >= 0) {
        int r1 = dv_socket_set_nonblocking(fd, 1);
        test_check("dv_socket_set_nonblocking(1)", r1 == 0, "set nonblocking failed");
        int r2 = dv_socket_set_nonblocking(fd, 0);
        test_check("dv_socket_set_nonblocking(0)", r2 == 0, "set blocking failed");
        dv_socket_close(fd);
    }

    /* Test 9: socket last_error */
    const char* err = dv_socket_last_error();
    test_check("dv_socket_last_error()!=NULL", err != NULL, "NULL error string");

    int err_code = dv_socket_last_error_code();
    (void)err_code; /* just check it doesn't crash */
    test_pass("dv_socket_last_error_code()");

    /* Test 10: socket get_peer_addr */
    fd = dv_socket_create(2, 1);
    if (fd >= 0) {
        dv_socket_connect(fd, "127.0.0.1", port);
        const char* peer = dv_socket_get_peer_addr(fd);
        int peer_ok = (peer && strlen(peer) > 0 && strstr(peer, "127.0.0.1") != NULL);
        test_check("dv_socket_get_peer_addr", peer_ok, "empty or wrong peer addr");
        dv_socket_close(fd);
    }

    /* ====== B2: Poller ====== */

    /* Test 11: poller create */
    LightPoller* p = dv_poller_create();
    test_check("dv_poller_create", p != NULL, "poller is NULL");

    /* Test 12: poller register */
    if (p) {
        int r = dv_poller_register(p, 0, 1); /* fd=0, DV_POLL_READ */
        test_check("dv_poller_register(fd=0,READ)", r == 0, "register failed");
    }

    /* Test 13: poller unregister */
    if (p) {
        int r = dv_poller_unregister(p, 0);
        test_check("dv_poller_unregister(fd=0)", r == 0, "unregister failed");
    }

    /* Test 14: poller destroy */
    if (p) {
        dv_poller_destroy(p);
        test_pass("dv_poller_destroy");
    }

    /* Test 15: poller with real socket */
    fd = dv_socket_create(2, 1);
    if (fd >= 0) {
        dv_socket_connect(fd, "127.0.0.1", port);
        dv_socket_send(fd, "poller_test");

        LightPoller* p2 = dv_poller_create();
        if (p2) {
            dv_poller_register(p2, fd, 1); /* DV_POLL_READ */
            int out_fds[256];
            int out_events[256];
            int ready = dv_poller_wait(p2, 2000, out_fds, out_events);
            int wait_ok = (ready > 0 && out_fds[0] == fd);
            test_check("dv_poller_wait(real_socket)", wait_ok, "no ready fd");

            if (ready > 0) {
                LightValue result;
                memset(&result, 0, sizeof(result));
                dv_socket_recv(&result, fd, 1024);
                int recv_ok2 = (result.type == 3 && result.str && strstr(result.str, "poller_test") != NULL);
                test_check("dv_poller_wait+recv(echo)", recv_ok2, "recv after poll failed");
            } else {
                test_fail("dv_poller_wait+recv(echo)", "poller returned 0 ready");
            }

            dv_poller_destroy(p2);
        }
        dv_socket_close(fd);
    }

    /* Test 16: poller timeout (no ready fd) */
    LightPoller* p3 = dv_poller_create();
    if (p3) {
        int out_fds[16];
        int out_events[16];
        int ready = dv_poller_wait(p3, 100, out_fds, out_events); /* 100ms timeout, nothing registered */
        test_check("dv_poller_wait(timeout,empty)", ready == 0, "should return 0 ready");
        dv_poller_destroy(p3);
    }

    /* ====== B3: Event Loop / Sleep ====== */

    /* Test 17: platform sleep */
    int64_t start = dv_now_ms();
    dv_platform_sleep(50);
    int64_t elapsed = dv_now_ms() - start;
    test_check("dv_platform_sleep(50ms)>=40ms", elapsed >= 40, "sleep too short");

    /* Test 18: dv_now_ms monotonic */
    int64_t t1 = dv_now_ms();
    dv_platform_sleep(10);
    int64_t t2 = dv_now_ms();
    test_check("dv_now_ms() monotonic", t2 > t1, "time not monotonic");

    /* ====== B2-3: poller 后端与超容量行为 ====== */

    /* Test 19: 后端名由编译期宏选出（不是运行时挑的） */
    const char* backend = dv_poller_backend();
    printf("POLLER_BACKEND=%s\n", backend ? backend : "(null)");
    int backend_ok = backend && (strcmp(backend, "WSAPoll") == 0 ||
                                 strcmp(backend, "poll") == 0 ||
                                 strcmp(backend, "select") == 0);
    test_check("dv_poller_backend() in {WSAPoll,poll,select}", backend_ok, "unknown backend");

    /* Test 20-22: 注册数超过初始容量 DV_POLLER_MAX(256)
     *
     * 可增长后端（WSAPoll/poll）应该长上去、一个不拒；
     * select 回退应该在 FD_SETSIZE 处**明确拒绝并写错误文本**。
     * 两种情况都必须满足 accepted + rejected == made ——
     * 静默丢 fd 会让这条账对不上，那是本项目最高优先级缺陷类型。 */
    {
        /* want 必须同时压过两条上限，否则判据是空的：
         *  - select 回退的 FD_SETSIZE：Windows(winsock2) 64，FreeBSD/Linux 1024
         *  - 可增长后端的初始容量 DV_POLLER_MAX(256)
         * 原先写死 300，只压得住 Windows 的 64；在 FD_SETSIZE=1024 的平台上
         * 一个都拒不掉，「上限生效」变成了一句空话 —— 这正是 FreeBSD 上
         * test_select_fallback_is_compile_time_macro 打红的真实成因。 */
        const int fd_cap = (int)FD_SETSIZE + 64;
        const int grow_cap = DV_POLLER_MAX + 44;
        const int want = fd_cap > grow_cap ? fd_cap : grow_cap;
        LightPoller* pg = dv_poller_create();
        int* gfds = (int*)calloc((size_t)want, sizeof(int));
        int made = 0, accepted = 0, rejected = 0;
        int fd_limit = -1;
#ifndef _WIN32
        fd_limit = raise_fd_limit(want);
#endif
        printf("POLLER_FD_SETSIZE=%d GROW_WANT=%d FD_LIMIT=%d\n",
               (int)FD_SETSIZE, want, fd_limit);
        if (pg && gfds) {
            for (int i = 0; i < want; i++) {
                int gfd = dv_socket_create(2, 1);
                if (gfd < 0) break;
                gfds[made++] = gfd;
                if (dv_poller_register(pg, gfd, 1) == 0) accepted++;
                else rejected++;
            }
            printf("GROW_MADE=%d GROW_ACCEPTED=%d GROW_REJECTED=%d GROW_COUNT=%d\n",
                   made, accepted, rejected, dv_poller_count(pg));

            test_check("poller over-capacity: every fd accounted (no silent drop)",
                       made > 0 && accepted + rejected == made,
                       "accepted+rejected != made -> some fd silently dropped");
            test_check("dv_poller_count == accepted",
                       dv_poller_count(pg) == accepted,
                       "registration table count disagrees with accept count");
            /* 开不满 want 个 socket 时上面两条照样过，但上限判据已经废了。
             * 这条把「环境 fd 不够」暴露成明确失败，而不是让判据静默变弱。 */
            test_check("over-capacity: could actually open GROW_WANT sockets",
                       made == want,
                       "fd 不够开满 -> 抬 ulimit -n / sysctl kern.maxfilesperproc");
            if (rejected > 0) {
                test_check("rejection writes an explicit error message",
                           dv_poller_last_error()[0] != '\0',
                           "rejected but dv_poller_last_error() is empty");
            } else {
                test_check("growable backend grew past DV_POLLER_MAX",
                           dv_poller_count(pg) > DV_POLLER_MAX,
                           "no rejection and no growth -> capacity logic broken");
            }

            for (int i = 0; i < made; i++) dv_socket_close(gfds[i]);
        } else {
            test_fail("poller over-capacity setup", "alloc failed");
            test_fail("dv_poller_count == accepted", "alloc failed");
            test_fail("over-capacity: could actually open GROW_WANT sockets", "alloc failed");
            test_fail("over-capacity behaviour", "alloc failed");
        }
        if (gfds) free(gfds);
        if (pg) dv_poller_destroy(pg);
    }


    /* ====== Summary ====== */
    printf("\n=== C Layer Results: %d/%d passed, %d failed ===\n",
           tests_passed, tests_total, tests_failed);

    return tests_failed > 0 ? 1 : 0;
}
