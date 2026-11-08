# Gauntlet report

Created 2026-11-08T04:26:32+00:00 on vm (Linux-6.18.44-fc-v310-x86_64-with-glibc2.39, 4 CPUs, 15.7 GB).
Verdict: **PASS** (exit 0).

Arguments: `--stage env --stage clippy --stage cargo-test --stage port-tests --update-baseline --keep-going --report-dir tools/gauntlet/report/baseline-linux-x86_64`

## Repositories

| Repository | Head | Branch | Dirty |
|---|---|---|---|
| DC2-Toolkit | `b5dc75ee755e` | claude/dark-cloud-2-engine-yr3rlk | yes |
| ChronicleTwo | `58dd0868a899` | claude/dark-cloud-2-engine-yr3rlk | yes |

## Stages

| Gate | Stage | Status | Time | Summary |
|---|---|---|---|---|
| G0 | env | pass | 0.1s | 9 checks; optional absent: dc2-debug, disc |
| G0 | clippy | pass | 41.5s | 4 crate(s), 1 lint(s); 0 new, 1 known, 0 fixed against linux-x86_64.json (baseline rewritten: 1 were new, 0 fixed before) |
| G0 | cargo-test | pass | 982.2s | 784 tests in 4 crates: 783 passed, 1 failed, 36 ignored; 0 new, 1 known, 0 fixed against linux-x86_64.json (baseline rewritten: 1 were new, 0 fixed before) |
| G0 | port-tests | pass | 24.4s | 23 native checks: 23 passed, 0 failed; 0 new, 0 known, 0 fixed against linux-x86_64.json (baseline rewritten: 0 were new, 0 fixed before) |

### G0 env: pass

9 checks; optional absent: dc2-debug, disc

Reproduce:

```
python3 -I tools/gauntlet/run.py --stage env
```

Evidence:

- `/home/user/DC2-Toolkit/tools/gauntlet/report/baseline-linux-x86_64/env/env.json`
- `/home/user/DC2-Toolkit/tools/gauntlet/report/baseline-linux-x86_64/env/env.txt`

### G0 clippy: pass

4 crate(s), 1 lint(s); 0 new, 1 known, 0 fixed against linux-x86_64.json (baseline rewritten: 1 were new, 0 fixed before)

Reproduce:

```
(cd src && cargo clippy --release -p dc2tk-disc --no-deps --all-targets -- -D warnings) ; (cd src && cargo clippy --release -p dc2tk-script --no-deps --all-targets -- -D warnings) ; (cd src && cargo clippy --release -p dc2tk-assets --no-deps --all-targets -- -D warnings) ; (cd src && cargo clippy --release -p dc2tk --no-deps --all-targets -- -D warnings)
```

Evidence:

- `/home/user/DC2-Toolkit/tools/gauntlet/report/baseline-linux-x86_64/clippy/dc2tk-disc.log`
- `/home/user/DC2-Toolkit/tools/gauntlet/report/baseline-linux-x86_64/clippy/dc2tk-script.log`
- `/home/user/DC2-Toolkit/tools/gauntlet/report/baseline-linux-x86_64/clippy/dc2tk-assets.log`
- `/home/user/DC2-Toolkit/tools/gauntlet/report/baseline-linux-x86_64/clippy/dc2tk.log`

Against the baseline: 0 new failure(s), 0 fixed, 1 known.

### G0 cargo-test: pass

784 tests in 4 crates: 783 passed, 1 failed, 36 ignored; 0 new, 1 known, 0 fixed against linux-x86_64.json (baseline rewritten: 1 were new, 0 fixed before)

Reproduce:

```
(cd src && cargo test --release -p dc2tk-disc) ; (cd src && cargo test --release -p dc2tk-script) ; (cd src && cargo test --release -p dc2tk-assets) ; (cd src && cargo test --release -p dc2tk)
```

Evidence:

- `/home/user/DC2-Toolkit/tools/gauntlet/report/baseline-linux-x86_64/cargo-test/dc2tk-disc.log`
- `/home/user/DC2-Toolkit/tools/gauntlet/report/baseline-linux-x86_64/cargo-test/dc2tk-script.log`
- `/home/user/DC2-Toolkit/tools/gauntlet/report/baseline-linux-x86_64/cargo-test/dc2tk-assets.log`
- `/home/user/DC2-Toolkit/tools/gauntlet/report/baseline-linux-x86_64/cargo-test/dc2tk.log`

Against the baseline: 0 new failure(s), 0 fixed, 1 known.

### G0 port-tests: pass

23 native checks: 23 passed, 0 failed; 0 new, 0 known, 0 fixed against linux-x86_64.json (baseline rewritten: 0 were new, 0 fixed before)

Reproduce:

```
PATH=/opt/clang20/bin:$PATH /usr/local/bin/python3 -I port/tests/run.py
```

Log: `/home/user/DC2-Toolkit/tools/gauntlet/report/baseline-linux-x86_64/port-tests/port-tests.log`

Evidence:

- `/home/user/DC2-Toolkit/tools/gauntlet/report/baseline-linux-x86_64/port-tests/port-tests.log`

Against the baseline: 0 new failure(s), 0 fixed, 0 known.
