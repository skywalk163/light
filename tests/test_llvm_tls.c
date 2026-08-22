/*
 * test_llvm_tls.c - B2-4 TLS 层纯 C 单测
 *
 * 两种模式（由命令行参数选择）：
 *   positive <port> <cert_path>  添加信任锚 → 握手成功 → 收发回显
 *   negative <port>              不加信任锚 → 握手必须失败
 *
 * 编译：clang -O2 -o _taskB2_tls_test.exe tests/test_llvm_tls.c -lws2_32 -lsecur32 -lcrypt32
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* 直接包含 runtime，不走 codegen —— 和 test_llvm_c_runtime.c 同口径 */
#include "../src/llvm/runtime_typed.c"

/* ── 正例：添加信任锚 → 握手成功 → 收发 ─────────────────────── */
static int test_positive(int port, const char* cert_path) {
    int fails = 0;

    /* 1. 添加自签证书到信任锚 */
    if (dv_tls_add_trusted_cert_file(cert_path) != 0) {
        printf("[FAIL] dv_tls_add_trusted_cert_file(%s): %s\n",
               cert_path, dv_tls_last_error());
        return 1;
    }
    printf("[PASS] dv_tls_add_trusted_cert_file(%s)\n", cert_path);

    /* 2. 建立 TCP 连接 */
    int fd = dv_socket_create(AF_INET, SOCK_STREAM);
    if (fd < 0) { printf("[FAIL] dv_socket_create\n"); return 1; }
    printf("[PASS] dv_socket_create(AF_INET,SOCK_STREAM)\n");

    if (dv_socket_connect(fd, "127.0.0.1", port) != 0) {
        printf("[FAIL] dv_socket_connect(127.0.0.1,%d)\n", port);
        dv_socket_close(fd);
        return 1;
    }
    printf("[PASS] dv_socket_connect(127.0.0.1,%d)\n", port);

    /* 非阻塞模式（TLS 握手需要） */
    dv_socket_set_nonblocking(fd, 1);

    /* 3. 包装 TLS */
    LightTLS* tls = dv_tls_wrap(fd, "localhost");
    if (!tls) {
        printf("[FAIL] dv_tls_wrap: %s\n", dv_tls_last_error());
        dv_socket_close(fd);
        return 1;
    }
    printf("[PASS] dv_tls_wrap(fd,localhost)\n");

    /* 4. 握手（可重入，用 poller 等待 IO 就绪而非 sleep 轮询）
     * 这验证了 dv_tls_want_event + dv_poller_wait 的集成：
     * 握手挂回 IO 等待队列的设计目标在这里被真实验证。 */
    LightPoller* hs_poller = dv_poller_create();
    if (!hs_poller) {
        printf("[FAIL] dv_poller_create for handshake\n");
        dv_tls_free(tls);
        dv_socket_close(fd);
        return 1;
    }
    int hs_ok = 0;
    for (int i = 0; i < 200; i++) {
        int r = dv_tls_handshake(tls);
        if (r == DV_TLS_OK) { hs_ok = 1; break; }
        if (r == DV_TLS_WANT_READ || r == DV_TLS_WANT_WRITE) {
            /* 用 poller 等 IO 就绪，不再 sleep 轮询 */
            int want = dv_tls_want_event(tls);
            dv_poller_register(hs_poller, fd, want);
            int ready_fds[1];
            int ready_events[1];
            int n = dv_poller_wait_n(hs_poller, 2000, ready_fds, ready_events, 1);
            if (n < 0) {
                printf("[FAIL] dv_poller_wait_n during handshake: %s\n", dv_poller_last_error());
                dv_poller_destroy(hs_poller);
                dv_tls_free(tls);
                dv_socket_close(fd);
                return 1;
            }
            if (n == 0) {
                /* 超时，再试一轮 handshake（可能已就绪但 poller 边沿触发错过） */
                continue;
            }
            dv_poller_unregister(hs_poller, fd);
            continue;
        }
        printf("[FAIL] dv_tls_handshake round %d: %s\n", i, dv_tls_last_error());
        dv_poller_destroy(hs_poller);
        dv_tls_free(tls);
        dv_socket_close(fd);
        return 1;
    }
    dv_poller_destroy(hs_poller);
    if (!hs_ok) {
        printf("[FAIL] dv_tls_handshake timeout\n");
        dv_tls_free(tls);
        dv_socket_close(fd);
        return 1;
    }
    printf("[PASS] dv_tls_handshake\n");

    /* 5. 发送 */
    const char* msg = "hello_tls_c_unit";
    int sent = dv_tls_send(tls, msg);
    if (sent <= 0) {
        printf("[FAIL] dv_tls_send: %s\n", dv_tls_last_error());
        dv_tls_free(tls);
        dv_socket_close(fd);
        return 1;
    }
    printf("[PASS] dv_tls_send(%s)=%d\n", msg, sent);

    /* 6. 接收回显（用 poller 等待 IO 就绪，用 dv_tls_recv_status 区分状态） */
    char recv_buf[256] = {0};
    int got_it = 0;
    LightPoller* recv_poller = dv_poller_create();
    if (!recv_poller) {
        printf("[FAIL] dv_poller_create for recv\n");
        dv_tls_free(tls);
        dv_socket_close(fd);
        return 1;
    }
    for (int i = 0; i < 200; i++) {
        LightValue result;
        memset(&result, 0, sizeof(result));
        dv_tls_recv(&result, tls, 256);
        int status = dv_tls_recv_status(tls);
        if (result.type == 3 && result.str && result.str[0]) {
            strncpy(recv_buf, result.str, sizeof(recv_buf) - 1);
            dv_free(&result);
            got_it = 1;
            break;
        }
        dv_free(&result);
        /* 用 recv_status 精确判断下一步 */
        if (status == DV_TLS_WANT_READ) {
            dv_poller_register(recv_poller, fd, DV_POLL_READ);
            int ready_fds[1];
            int ready_events[1];
            int n = dv_poller_wait_n(recv_poller, 2000, ready_fds, ready_events, 1);
            if (n > 0) dv_poller_unregister(recv_poller, fd);
        } else if (status == DV_TLS_CLOSED) {
            printf("[FAIL] dv_tls_recv: peer closed before echo\n");
            break;
        } else if (status == DV_TLS_ERROR) {
            printf("[FAIL] dv_tls_recv error: %s\n", dv_tls_last_error());
            break;
        }
    }
    dv_poller_destroy(recv_poller);
    if (!got_it) {
        printf("[FAIL] dv_tls_recv: timeout, last_error=%s\n", dv_tls_last_error());
        dv_tls_free(tls);
        dv_socket_close(fd);
        return 1;
    }

    if (strcmp(recv_buf, msg) == 0) {
        printf("[PASS] dv_tls_recv(echo=%s)\n", recv_buf);
    } else {
        printf("[FAIL] dv_tls_recv: expected '%s', got '%s'\n", msg, recv_buf);
        fails++;
    }

    /* 7. 后端名称 */
    const char* backend = dv_tls_backend();
    printf("[PASS] dv_tls_backend()=%s\n", backend ? backend : "(null)");

    /* 8. 清理 */
    dv_tls_free(tls);
    dv_socket_close(fd);
    printf("[PASS] dv_tls_free + dv_socket_close\n");

    return fails;
}

/* ── 负例：不加信任锚 → 握手必须失败 ─────────────────────────── */
static int test_negative(int port) {
    int fd = dv_socket_create(AF_INET, SOCK_STREAM);
    if (fd < 0) { printf("[FAIL] dv_socket_create\n"); return 1; }

    if (dv_socket_connect(fd, "127.0.0.1", port) != 0) {
        printf("[FAIL] dv_socket_connect\n");
        dv_socket_close(fd);
        return 1;
    }
    dv_socket_set_nonblocking(fd, 1);

    LightTLS* tls = dv_tls_wrap(fd, "localhost");
    if (!tls) {
        printf("[FAIL] dv_tls_wrap: %s\n", dv_tls_last_error());
        dv_socket_close(fd);
        return 1;
    }

    /* 握手应该失败（自签证书不在系统根存储中）。
     * 用 poller 等待而非 sleep 轮询，与正例同口径。 */
    LightPoller* neg_poller = dv_poller_create();
    if (!neg_poller) {
        printf("[FAIL] dv_poller_create for negative test\n");
        dv_tls_free(tls);
        dv_socket_close(fd);
        return 1;
    }
    int hs_failed = 0;
    for (int i = 0; i < 200; i++) {
        int r = dv_tls_handshake(tls);
        if (r == DV_TLS_OK) {
            /* 握手成功了 —— 不应该！ */
            break;
        }
        if (r == DV_TLS_ERROR) {
            hs_failed = 1;
            break;
        }
        /* WANT_READ / WANT_WRITE → 用 poller 等 IO 就绪 */
        int want = dv_tls_want_event(tls);
        dv_poller_register(neg_poller, fd, want);
        int ready_fds[1];
        int ready_events[1];
        int n = dv_poller_wait_n(neg_poller, 2000, ready_fds, ready_events, 1);
        if (n > 0) dv_poller_unregister(neg_poller, fd);
    }
    dv_poller_destroy(neg_poller);

    dv_tls_free(tls);
    dv_socket_close(fd);

    if (hs_failed) {
        printf("[PASS] tls_handshake rejected untrusted cert: %s\n", dv_tls_last_error());
        return 0;
    } else {
        printf("[FAIL] tls_handshake should have failed for untrusted self-signed cert\n");
        return 1;
    }
}

int main(int argc, char* argv[]) {
    if (argc < 3) {
        printf("Usage: %s <positive|negative> <port> [cert_path]\n", argv[0]);
        return 1;
    }

    const char* mode = argv[1];
    int port = atoi(argv[2]);

    /* 初始化 Winsock（dv_socket_create 会调 dv_winsock_init，但提前调也无害） */
#ifdef _WIN32
    dv_winsock_init();
#endif

    if (strcmp(mode, "positive") == 0) {
        if (argc < 4) {
            printf("positive mode requires cert_path argument\n");
            return 1;
        }
        printf("=== TLS Positive Test (port=%d, cert=%s) ===\n", port, argv[3]);
        int fails = test_positive(port, argv[3]);
        printf("=== TLS Positive Results: %s ===\n", fails ? "FAILED" : "ALL PASSED");
        return fails;
    } else if (strcmp(mode, "negative") == 0) {
        printf("=== TLS Negative Test (port=%d) ===\n", port);
        int fails = test_negative(port);
        printf("=== TLS Negative Results: %s ===\n", fails ? "FAILED" : "ALL PASSED");
        return fails;
    }

    printf("Unknown mode: %s\n", mode);
    return 1;
}
