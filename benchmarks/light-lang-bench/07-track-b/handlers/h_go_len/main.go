// MiniBridge · h_go_len（B1 handler，Go）
//
// 契约（见 ../规格.md §3.2）：
//
//	输入：stdin 一行 JSON 记录（UTF-8）。
//	行为：剥离行尾 \r\n 后，取该行的**字节数**（不是字符数、不是码点数）。
//	输出：stdout 单行 "LEN <字节数>\n"。
//	失败：读 stdin 出错 → stderr "ERR <原因>"，退出码 1。
//
// 只依赖 Go 标准库（io）。刻意不解析 JSON：本 handler 度量的是「纯计算、
// 无状态」的外部进程调用，解析能力留给被测语言自己。
package main

import (
	"bufio"
	"fmt"
	"io"
	"os"
)

func main() {
	r := bufio.NewReaderSize(os.Stdin, 1<<20)
	// 规格要求「一行」：读到 \n 为止；不带 \n 的末行也接受（RunSuite 之外的手工调试）。
	line, err := r.ReadString('\n')
	if err != nil && err != io.EOF {
		fmt.Fprintf(os.Stderr, "ERR read: %v\n", err)
		os.Exit(1)
	}
	n := len(line)
	for n > 0 && (line[n-1] == '\n' || line[n-1] == '\r') {
		n--
	}
	if n == 0 {
		fmt.Fprintf(os.Stderr, "ERR empty_input\n")
		os.Exit(1)
	}
	fmt.Printf("LEN %d\n", n)
}
