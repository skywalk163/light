# R125-C1：lightpub 独立测试子集入口（将来分仓可整体搬走）
# 只跑 tests/lightpub/（桥接层测试），不触发全量、不触发 082 远端门。
# 外网用例（httpbin.org）默认 skip；LIGHTPUB_NETWORK=1 make lightpub-test 才跑。
# -o addopts=：清空 pyproject 的 -n 4 --timeout=60，子集极小无需 xdist/pytest-timeout。
.PHONY: lightpub-test

lightpub-test:
	python -m pytest tests/lightpub -p no:randomly -q -o addopts=
