# Gauntlet report

Created 2026-11-08T15:53:05+00:00 on vm (Linux-6.18.44-fc-v310-x86_64-with-glibc2.39, 4 CPUs, 15.7 GB).
Verdict: **PASS** (exit 0).

Arguments: `--stage env --stage fmt --stage tool-tests --stage port-tests --report-dir /home/user/DC2-Toolkit/tools/gauntlet/report/light-20261108`

## Repositories

| Repository | Head | Branch | Dirty |
|---|---|---|---|
| DC2-Toolkit | `8e4137172aab` | claude/dark-cloud-2-engine-yr3rlk | yes |
| ChronicleTwo | `58dd0868a899` | claude/dark-cloud-2-engine-yr3rlk | yes |

## Stages

| Gate | Stage | Status | Time | Summary |
|---|---|---|---|---|
| G0 | env | pass | 0.2s | 9 checks; optional absent: dc2-debug, disc |
| G0 | fmt | pass | 1.7s | cargo fmt --check clean |
| G0 | tool-tests | pass | 0.8s | 2 test scripts, 0 failed |
| G0 | port-tests | pass | 18.0s | 24 native checks: 24 passed, 0 failed; 0 new, 0 known, 0 fixed against linux-x86_64.json |

### G0 env: pass

9 checks; optional absent: dc2-debug, disc

Reproduce:

```
python3 -I tools/gauntlet/run.py --stage env
```

Evidence:

- `/home/user/DC2-Toolkit/tools/gauntlet/report/light-20261108/env/env.json`
- `/home/user/DC2-Toolkit/tools/gauntlet/report/light-20261108/env/env.txt`

### G0 fmt: pass

cargo fmt --check clean

Reproduce:

```
(cd src && cargo fmt --all -- --check)
```

Log: `/home/user/DC2-Toolkit/tools/gauntlet/report/light-20261108/fmt/fmt.log`

Evidence:

- `/home/user/DC2-Toolkit/tools/gauntlet/report/light-20261108/fmt/fmt.log`

### G0 tool-tests: pass

2 test scripts, 0 failed

Reproduce:

```
/usr/local/bin/python3 -I tools/test_engine_mods.py ; /usr/local/bin/python3 -I tools/test_native_prepare.py
```

Evidence:

- `/home/user/DC2-Toolkit/tools/gauntlet/report/light-20261108/tool-tests/test_engine_mods.py.log`
- `/home/user/DC2-Toolkit/tools/gauntlet/report/light-20261108/tool-tests/test_native_prepare.py.log`

### G0 port-tests: pass

24 native checks: 24 passed, 0 failed; 0 new, 0 known, 0 fixed against linux-x86_64.json

Reproduce:

```
PATH=/opt/clang20/bin:$PATH /usr/local/bin/python3 -I port/tests/run.py
```

Log: `/home/user/DC2-Toolkit/tools/gauntlet/report/light-20261108/port-tests/port-tests.log`

Evidence:

- `/home/user/DC2-Toolkit/tools/gauntlet/report/light-20261108/port-tests/port-tests.log`

Against the baseline: 0 new failure(s), 0 fixed, 0 known.
