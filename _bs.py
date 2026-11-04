import os, sys, tempfile, subprocess, io, json
sys.path.insert(0, "src")
from llvm.compiler import compile_light_typed

def run(code, tag, pre=None):
    d = tempfile.mkdtemp(prefix="_p_")
    if pre:
        for p in pre: os.makedirs(os.path.join(d, p), exist_ok=True)
    src = os.path.join(d, "主.light")
    open(src, "w", encoding="utf-8", newline="\n").write(code)
    exe = compile_light_typed(src, os.path.join(d, "产物"), optimize_level=0)
    r = subprocess.run([exe], capture_output=True, timeout=180, cwd=d)
    return {"tag": tag, "rc": r.returncode, "out": r.stdout.decode("utf-8","replace"),
            "err": r.stderr.decode("utf-8","replace")[:300],
            "tree": [os.path.relpath(os.path.join(dp,x), d) for dp,_,fs in os.walk(d) for x in fs if not x.endswith(('.light','.ll','.o','.exe'))]}

BS = chr(92)
cases=[]
cases.append(run('从 文件系统 导入 原子写入\n段落 主:\n  设 p 为 "bs1"%s%s"bs2"%s%s"a.txt"\n  输出(原子写入(p, "abc"))\n' % (BS,BS,BS,BS), "backslash-relative"))
cases.append(run('从 文件系统 导入 原子写入\n段落 主:\n  设 p 为 "bs3"%s%s"a.txt"\n  输出(原子写入(p, "abc"))\n  输出(读取文件(p))\n' % (BS,BS), "backslash-onelevel"))
io.open("_bs_out.json","w",encoding="utf-8").write(json.dumps(cases, ensure_ascii=False, indent=2))
print("ok")
