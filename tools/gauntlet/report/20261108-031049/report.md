# Gauntlet report

Created 2026-11-08T03:10:49+00:00 on vm (Linux-6.18.44-fc-v310-x86_64-with-glibc2.39, 4 CPUs, 15.7 GB).
Verdict: **FAIL** (exit 1).

Arguments: `--stage env --stage fmt`

## Repositories

| Repository | Head | Branch | Dirty |
|---|---|---|---|
| DC2-Toolkit | `b5dc75ee755e` | claude/dark-cloud-2-engine-yr3rlk | yes |
| ChronicleTwo | `cb6ae0f3ab9d` | claude/dark-cloud-2-engine-yr3rlk | yes |

## Stages

| Gate | Stage | Status | Time | Summary |
|---|---|---|---|---|
| G0 | env | pass | 0.2s | 6 checks |
| G0 | fmt | fail | 1.6s | cargo fmt --check wants changes: [m             assert_eq!(imported.models.len(), 1, "{name}: one model, however many pieces show it");              assert!(                  imported.notes.iter().any(/note/ note.contains("edited differently")), |

### G0 env: pass

6 checks

Reproduce:

```
python3 -I tools/gauntlet/run.py --stage env
```

Evidence:

- `/home/user/DC2-Toolkit/tools/gauntlet/report/20261108-031049/env/env.json`

### G0 fmt: fail

cargo fmt --check wants changes: [m             assert_eq!(imported.models.len(), 1, "{name}: one model, however many pieces show it");
             assert!(
                 imported.notes.iter().any(|note| note.contains("edited differently")),

Reproduce:

```
cargo fmt --all -- --check
```

Log: `/home/user/DC2-Toolkit/tools/gauntlet/report/20261108-031049/fmt/fmt.log`

Evidence:

- `/home/user/DC2-Toolkit/tools/gauntlet/report/20261108-031049/fmt/fmt.log`
