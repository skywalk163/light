# 在 FreeBSD 上给 gitea 挂 CI（act_runner · host 模式）

> 面向本仓库 `.gitea/workflows/ci.yml`。仓库侧文件已就位并校正；**这份是服务器侧
> 部署手册**，需要你在 FreeBSD 上手工执行。局域网 gitea 实例默认按
> `http://192.168.1.5:3000` 写；换成你自己的地址。

## 0. 为什么是 host 模式（「你懂的」那层）

FreeBSD 没有原生 Docker。Gitea act_runner 的默认 `docker` 执行器在这里跑不起来，
只能用 **host 执行器**：workflow 的每一步直接在宿主（这里是 jail）的 shell 里跑，
不进容器。代价是——**jail 里必须预装好 workflow 依赖的一切**（python、git、bash、
node），因为没有镜像兜底。这也是本仓库 workflow 用「系统 python3 建 venv」而不是
`actions/setup-python` 的原因。

act_runner 官方**不发 FreeBSD 二进制**，得用 Go 自己编。

## 1. 建 jail 并装依赖

用 bastille（或 iocage / ezjail，按你现有的来）：

```sh
# 宿主上
bastille create ci 14.2-RELEASE 192.168.1.20    # 版本/IP 换成你的
bastille console ci
```

jail 内安装依赖（**这几样缺一不可**）：

```sh
pkg install -y \
    git \
    python311 \
    bash \          # host 模式下 run: 步骤默认用 bash
    node20 npm-node20 \   # actions/checkout 是 JS action，要 node 才能跑
    go gmake         # 仅用于编译 act_runner，编完可留可删

# 让 python3 / node 落在 PATH 上
python3.11 --version
node --version

# 锁 UTF-8 locale，否则读 .light / .md 里的中文会炸（jail 默认可能是 C）
echo 'export LANG=en_US.UTF-8'  >> ~/.profile
echo 'export LC_ALL=en_US.UTF-8' >> ~/.profile
```

## 2. 编译 act_runner

```sh
cd /root
git clone https://gitea.com/gitea/act_runner
cd act_runner
gmake build          # 产出当前目录的 ./act_runner
./act_runner --version
cp act_runner /usr/local/bin/
```

## 3. 在 gitea 上取注册 token

Web 后台任选一级作用域：

- 实例级：管理后台 → Actions → Runners → 「创建 Runner」
- 组织级 / 仓库级：对应 Settings → Actions → Runners → 「创建 Runner」

复制弹出的 **registration token**。同时确认 gitea 已开 Actions：
`app.ini` 里
```ini
[actions]
ENABLED = true
```
且目标仓库 Settings → Actions → 勾选启用。

## 4. 注册 runner（关键：标签打成 `freebsd:host`）

```sh
cd /var/lib/act_runner        # 自己建个工作目录
act_runner register \
    --no-interactive \
    --instance http://192.168.1.5:3000 \
    --token   <上一步的 registration token> \
    --name    freebsd-jail \
    --labels  freebsd:host
```

- 标签 `freebsd` 必须和 workflow 里的 `runs-on: freebsd` 完全一致。
- `:host` 后缀告诉 act_runner **这个标签用 host 执行器**，不去找 docker 镜像。
  （对比：docker 模式会写成 `ubuntu-latest:docker://node:20`。）

注册成功后目录里会生成 `.runner`（含 runner 身份，别删）。

## 5. 镜像 actions/checkout（host 模式的坑）

workflow 里 checkout 写的是本地地址：

```yaml
uses: http://192.168.1.5:3000/actions/checkout@v4
```

所以你的 gitea 上必须有 `actions/checkout` 这个仓库。二选一：

**A. 在 gitea 里镜像一份（局域网离线也能用，推荐）**
1. 新建组织 `actions`。
2. 迁移仓库：`+ → 迁移 → GitHub`，源 `https://github.com/actions/checkout`，
   仓库名 `checkout`，**勾选「包括标签/分支」**（`v4` 靠 tag/branch 解析）。

**B. 让 gitea 自动回源 github（要能连外网）**
`app.ini`：
```ini
[actions]
DEFAULT_ACTIONS_URL = https://github.com
```
然后把 workflow 里那行改回裸写 `uses: actions/checkout@v4`。
局域网内网环境别选这个。

> 本 workflow 只用到 `actions/checkout` 一个 JS action（没有 upload-artifact 之类），
> 所以只需镜像这一个。

## 6. 生成配置并常驻运行

```sh
act_runner generate-config > config.yaml
```

`config.yaml` 里确认/调整：
```yaml
runner:
  labels:
    - "freebsd:host"          # 与注册一致
  capacity: 1                  # 一次跑几个 job，按机器给
container:
  # host 模式不用容器，这一段可留空
```

前台先手动验证一次：
```sh
act_runner daemon --config config.yaml
```
回到 gitea Runners 页面，应看到 `freebsd-jail` 状态 **Idle**。

装成开机服务（rc.d）——新建 `/usr/local/etc/rc.d/act_runner`：

```sh
#!/bin/sh
# PROVIDE: act_runner
# REQUIRE: NETWORKING
# KEYWORD: shutdown
. /etc/rc.subr
name=act_runner
rcvar=act_runner_enable
: ${act_runner_workdir:=/var/lib/act_runner}
pidfile="/var/run/${name}.pid"
command="/usr/sbin/daemon"
command_args="-f -p ${pidfile} -o ${act_runner_workdir}/runner.log \
    /usr/local/bin/act_runner daemon --config ${act_runner_workdir}/config.yaml"
load_rc_config $name
run_rc_command "$1"
```

```sh
chmod +x /usr/local/etc/rc.d/act_runner
sysrc act_runner_enable=YES
service act_runner start
tail -f /var/lib/act_runner/runner.log
```

## 7. 冒烟验证

往 `merge-v7` 推一个空提交（workflow 现已监听 `main` 和 `merge-v7`）：

```sh
git commit --allow-empty -m "ci: 触发 gitea act_runner 冒烟"
git push origin merge-work:merge-v7
```

gitea 仓库 → Actions 标签，应出现一条 `CI` 运行记录，runner 认领后逐步执行：
安装依赖 → 单元/集成/e2e → 根目录测试 → 统一测试运行器 → 积木库门禁。

## 8. 判绿口径：基线闸门（不是全绿）

**本仓库当前有一批存量失败**（v7 收尾期欠账，见 `docs/v7_失败用例根因聚类工单.md`，
最大一类是「单 02 · 紧凑写法分词族」）。所以 CI **不要求全绿**，判据是「不新增打红」：

- `单元 + 集成测试` / `端到端测试` 两步只跑 + 产出 junit，`|| true` 放行存量失败；
  但紧跟 `test -f`——如果 pytest 是崩溃、连 junit 都没产出，这一步必须红。
- `回归闸门` 才是判绿点：`tools/ci/check_regression.py` 拿 junit 与
  `tests/ci_baseline_failures.txt` 对比：
  - 冒出基线**之外**的失败 → 退出 1，CI 红（真回归）
  - 基线里有、这次转绿 → 放行，并打印清单提醒你刷新基线
  - 打红总数超过基线条数 → 退出 1（兜底，防基线被绕过）

用例身份用 junit 的 `classname::name`，不用文件路径——Windows 开发机与 FreeBSD
runner 的路径分隔符不一致，点号形式跨平台稳定。

**修好一批之后刷新基线**（必须做，否则基线虚高、闸门变松）：

```sh
. .venv/bin/activate
pytest tests/unit tests/integration tests/e2e -q --tb=no --junitxml=.ci/all.xml || true
python tools/ci/check_regression.py --junit .ci/all.xml \
    --write-baseline tests/ci_baseline_failures.txt
git add tests/ci_baseline_failures.txt && git commit -m "ci: 刷新回归基线"
```

基线首次固化于 2026-08-16，快照 `collected=1153 / failures=33 / skipped=54`（33 条）。
注意这 33 条只覆盖 `tests/unit + tests/integration + tests/e2e`；全套（含 `tests/` 根目录）
是 56 条，其余 23 条落在 workflow 里本来就 `|| true` 的「根目录测试」步，不进闸门分母。

## 9. 常见坑


- **卡在 checkout / `node: not found`**：jail 没装 node，或 node 不在 PATH。
  host 模式跑 JS action 靠宿主 node。
- **`bash: not found`**：host 模式 `run:` 步骤默认 bash，`pkg install bash`。
- **中文乱码 / `UnicodeDecodeError`**：locale 没设成 UTF-8（见 §1）。
- **runner 一直 Offline**：token 过期（只在注册时有效一次）、`.runner` 被删、
  或 `instance` 地址 jail 里网络不通（先 `fetch http://192.168.1.5:3000` 验通）。
- **积木库门禁那步慢/装不上第三方包**：workflow 已 `pip install ... || true` 容错，
  缺依赖的块会单列成「缺依赖」不计入分母，不致命。
- **workflow 改了不生效**：Gitea 读的是**被推分支上那一版** `.gitea/workflows/ci.yml`，
  确认改动已推到触发分支。
