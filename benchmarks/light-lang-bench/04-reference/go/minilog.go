// MiniLog 参考实现（Go，仅标准库）。
//
// 用途：作为第二份独立 oracle，与 04-reference/python/minilog.py 交叉对拍，
// 排除「oracle 与用例共享同一 Python 心智模型」导致的同源错误。
// 语义唯一依据：01-spec/MiniLog规格.md。本文件刻意直译本规格，不追求性能。
//
// 仅使用标准库：encoding/json / fmt / io / os / sort / strconv / strings。
package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"sort"
	"strconv"
	"strings"
)

// usageError 对应规格 §1.2 退出码 2（用法错误）。
type usageError struct{ msg string }

// ioError 对应规格 §1.2 退出码 1（I/O 错误）。
type ioError struct{ msg string }

func (e *usageError) Error() string { return e.msg }
func (e *ioError) Error() string     { return e.msg }

// required 为 §0.2 的四个必需字段，顺序即 validate 输出顺序。
var required = []string{"timestamp", "level", "service", "message"}

// record 是忽略空行之后的一条记录（非法 JSON 行也计入编号，供 tail 使用）。
type record struct {
	idx     int
	raw     []byte // 已去除行尾 \r 的原始行文本，原样输出时使用
	obj     map[string]any
	invalid bool
}

func main() {
	os.Exit(run(os.Args[1:]))
}

func run(argv []string) int {
	if len(argv) == 0 {
		fmt.Fprintln(os.Stderr, "usage error: missing subcommand")
		return 2
	}
	cmd := argv[0]

	opts, err := parseOpts(argv[1:])
	if err != nil {
		fmt.Fprintln(os.Stderr, "usage error:", err)
		return 2
	}

	// 各子命令允许的选项（§1.2 未识别选项 → 退出码 2）。
	allowed := map[string]map[string]bool{
		"filter":   {"level": true, "input": true, "output": true},
		"tail":     {"n": true, "input": true, "output": true},
		"validate": {"input": true, "output": true},
		"stats":    {"group-by": true, "input": true, "output": true},
	}
	allow, ok := allowed[cmd]
	if !ok {
		fmt.Fprintln(os.Stderr, "usage error: unknown subcommand:", cmd)
		return 2
	}
	for k := range opts {
		if !allow[k] {
			fmt.Fprintln(os.Stderr, "usage error: unknown option: --"+k)
			return 2
		}
	}

	data, err := readInput(opts)
	if err != nil {
		fmt.Fprintln(os.Stderr, "io error:", err)
		return 1
	}
	recs := records(data)

	var out [][]byte
	var warns []string
	switch cmd {
	case "filter":
		out, warns, err = cmdFilter(opts, recs)
	case "tail":
		out, warns, err = cmdTail(opts, recs)
	case "validate":
		out, warns, err = cmdValidate(recs)
	case "stats":
		out, warns, err = cmdStats(opts, recs)
	}
	if err != nil {
		if _, isUsage := err.(*usageError); isUsage {
			fmt.Fprintln(os.Stderr, "usage error:", err)
			return 2
		}
		fmt.Fprintln(os.Stderr, "io error:", err)
		return 1
	}

	if err := emit(out, opts); err != nil {
		fmt.Fprintln(os.Stderr, "io error:", err)
		return 1
	}
	// 警告走 stderr，不影响退出码（§0.3）。
	for _, w := range warns {
		os.Stderr.WriteString(w)
	}
	return 0
}

// parseOpts 解析 --key=value；拒绝重复选项与非法写法（§1 通用约定）。
func parseOpts(argv []string) (map[string]string, error) {
	opts := map[string]string{}
	for _, tok := range argv {
		if !strings.HasPrefix(tok, "--") || !strings.Contains(tok, "=") {
			return nil, &usageError{"bad option: " + tok}
		}
		body := tok[2:]
		eq := strings.Index(body, "=")
		key := body[:eq]
		val := body[eq+1:]
		if _, dup := opts[key]; dup {
			return nil, &usageError{"duplicate option: --" + key}
		}
		opts[key] = val
	}
	return opts, nil
}

// readInput 按 §1.1 读取全部输入；缺省或 --input=- 读 stdin。
func readInput(opts map[string]string) ([]byte, error) {
	src, present := opts["input"]
	if !present || src == "-" {
		return io.ReadAll(os.Stdin)
	}
	b, err := os.ReadFile(src)
	if err != nil {
		return nil, &ioError{"cannot read input: " + err.Error()}
	}
	return b, nil
}

// records 按 §0.1 切行、去 \r、忽略空白行并编号；按 §0.3 判定非法 JSON。
func records(data []byte) []record {
	lines := strings.Split(string(data), "\n")
	recs := make([]record, 0, len(lines))
	idx := 0
	for _, line := range lines {
		l := line
		if strings.HasSuffix(l, "\r") {
			l = l[:len(l)-1]
		}
		// 空白判定只认 ASCII 空白：空格、TAB、CR、LF（§0.1）。
		if strings.Trim(l, " \t\r\n") == "" {
			continue
		}
		idx++
		rec := record{idx: idx, raw: []byte(l)}
		var v any
		if err := json.Unmarshal([]byte(l), &v); err != nil {
			rec.invalid = true
		} else if v == nil {
			// JSON null：解析成功但不是对象，按非法处理（§0.3）。
			rec.invalid = true
		} else if m, ok := v.(map[string]any); ok {
			rec.obj = m
		} else {
			// 数组 / 标量 / 布尔 / 数字：同样按非法 JSON 处理（§0.3）。
			rec.invalid = true
		}
		recs = append(recs, rec)
	}
	return recs
}

// fieldStr 取字段值；仅当键存在且为 JSON 字符串时合法（§0.2）。
func fieldStr(m map[string]any, key string) (string, bool) {
	v, ok := m[key]
	if !ok {
		return "", false
	}
	s, ok := v.(string)
	return s, ok
}

func warn(idx int, warns *[]string) {
	*warns = append(*warns, fmt.Sprintf("WARN invalid_json index=%d\n", idx))
}

// cmdFilter：输出 level 精确等于给定值的合法记录（§2.1）。
func cmdFilter(opts map[string]string, recs []record) ([][]byte, []string, error) {
	level, ok := opts["level"]
	if !ok {
		return nil, nil, &usageError{"filter requires --level"}
	}
	var out [][]byte
	var warns []string
	for _, r := range recs {
		if r.invalid {
			warn(r.idx, &warns)
			continue
		}
		if lv, ok := fieldStr(r.obj, "level"); ok && lv == level {
			out = append(out, r.raw)
		}
	}
	return out, warns, nil
}

// cmdTail：输出最后 N 条；非法 JSON 行也计数并原样输出（§2.2）。
func cmdTail(opts map[string]string, recs []record) ([][]byte, []string, error) {
	nStr, ok := opts["n"]
	if !ok {
		return nil, nil, &usageError{"tail requires --n"}
	}
	if !isPositiveDecimal(nStr) {
		return nil, nil, &usageError{"--n must be a positive decimal integer"}
	}
	n, _ := strconv.Atoi(nStr) // isPositiveDecimal 已保证可解析且 >=1
	var all [][]byte
	var warns []string
	for _, r := range recs {
		if r.invalid {
			warn(r.idx, &warns)
		}
		all = append(all, r.raw)
	}
	if n > len(all) {
		n = len(all)
	}
	return all[len(all)-n:], warns, nil
}

// isPositiveDecimal：纯 ASCII 数字且 >=1；拒绝 + / 小数 / 负数 / 非数字（§2.2）。
func isPositiveDecimal(s string) bool {
	if s == "" {
		return false
	}
	for i := 0; i < len(s); i++ {
		if s[i] < '0' || s[i] > '9' {
			return false
		}
	}
	n, err := strconv.Atoi(s)
	return err == nil && n >= 1
}

// cmdValidate：输出缺失/类型不符字段的诊断（§2.3）。
func cmdValidate(recs []record) ([][]byte, []string, error) {
	var out [][]byte
	var warns []string
	for _, r := range recs {
		if r.invalid {
			warn(r.idx, &warns)
			out = append(out, []byte(fmt.Sprintf("%d\tinvalid_json", r.idx)))
			continue
		}
		for _, k := range required {
			if _, ok := fieldStr(r.obj, k); !ok {
				out = append(out, []byte(fmt.Sprintf("%d\tmissing_%s", r.idx, k)))
			}
		}
	}
	return out, warns, nil
}

type statsGroup struct {
	count int
	maxTS string
}

// cmdStats：按 service 分组统计；组间按 UTF-8 字节序升序（§3.2）。
func cmdStats(opts map[string]string, recs []record) ([][]byte, []string, error) {
	gb, ok := opts["group-by"]
	if !ok {
		return nil, nil, &usageError{"stats requires --group-by"}
	}
	if gb != "service" {
		return nil, nil, &usageError{"--group-by only supports service"}
	}
	groups := map[string]*statsGroup{}
	var warns []string
	for _, r := range recs {
		if r.invalid {
			warn(r.idx, &warns)
			continue
		}
		svc, okSvc := fieldStr(r.obj, "service")
		ts, okTs := fieldStr(r.obj, "timestamp")
		if !okSvc || !okTs {
			continue
		}
		g := groups[svc]
		if g == nil {
			g = &statsGroup{}
			groups[svc] = g
		}
		g.count++
		// 时间戳比较用 20 字符字典序（§0.2）；Go 字符串比较即字节序，
		// 与 ASCII 时间戳的码点序一致。
		if ts > g.maxTS {
			g.maxTS = ts
		}
	}
	keys := make([]string, 0, len(groups))
	for k := range groups {
		keys = append(keys, k)
	}
	sort.Strings(keys) // UTF-8 字节序升序
	var out [][]byte
	for _, k := range keys {
		g := groups[k]
		out = append(out, []byte(fmt.Sprintf("%s\t%d\t%s", k, g.count, g.maxTS)))
	}
	return out, warns, nil
}

// emit 按 §0.1 / §3.1 组装输出：行间 \n，末尾一个 \n；空结果为 0 字节。
// 指定 --output 时写文件且 stdout 为 0 字节。
func emit(lines [][]byte, opts map[string]string) error {
	var body []byte
	for i, ln := range lines {
		if i > 0 {
			body = append(body, '\n')
		}
		body = append(body, ln...)
	}
	if len(lines) > 0 {
		body = append(body, '\n')
	}
	dest, present := opts["output"]
	if !present {
		_, err := os.Stdout.Write(body)
		return err
	}
	// os.WriteFile 以 O_CREATE|O_TRUNC|O_WRONLY 打开，覆盖写即截断（§3.1）。
	if err := os.WriteFile(dest, body, 0o644); err != nil {
		return &ioError{"cannot write output: " + err.Error()}
	}
	return nil
}
