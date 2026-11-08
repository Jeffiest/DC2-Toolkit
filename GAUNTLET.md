# The gauntlet, toolkit side

DC2_PLAN.md (in ChronicleTwo) puts the toolkit's work package B behind gate G1 of a gauntlet an agent runs
without a person. ChronicleTwo's `GAUNTLET.md` holds the gates, the report format, the baseline rule and the
agent protocol; this file says what runs here. The runner is `tools/gauntlet/run.py` (Python 3, standard
library only, `python3 -I`), and it imports the report and baseline code from
`../ChronicleTwo/tools/gauntlet` (or `$CHRONICLE_TWO`) so both repositories write one report schema.
ChronicleTwo's runner calls it: its `toolkit` stage is this runner's G0 and G5, its `toolkit-limits` stage
is `limits` here, and both are *not run* when DC2-Toolkit is not beside the tree.

```
python3 -I tools/gauntlet/run.py                 # every stage; stops at the first red gate
python3 -I tools/gauntlet/run.py --gate G0       # the crates and tools
python3 -I tools/gauntlet/run.py --stage clippy --stage cargo-test --stage port-tests --update-baseline
python3 -I tools/gauntlet/run.py --json          # print only the report path
python3 -I tools/gauntlet/test_gauntlet.py       # the runner's parsers
```

Every cargo command runs with `CARGO_INCREMENTAL=0 CARGO_PROFILE_RELEASE_DEBUG=0` (the workspace's release
profile has `debug = 1`, which made `build/release` 8 GB on a shared 40 GB disk), and the commands the report
records carry both. The `clippy`, `cargo-test` and `limits` stages do not start with less than
`--min-free-gb` (default 4) free on the disk holding `build/`: they are an error with the free space in the
summary, since a build on a full disk fails like a broken crate. ChronicleTwo's runner passes its own
`--min-free-gb` through.

| Gate | Stage | Check | Green when |
|---|---|---|---|
| G0 | `env` | rustc 1.99, cargo, clang 20 (`/opt/clang20/bin` first on PATH, or `DC2TK_CLANG_BIN`), Python >= 3.10, `src/Cargo.toml`; sdl3, the port SDK, `dc2-debug` and a disc reported | the required ones are there |
| G0 | `fmt` | `cargo fmt --all -- --check` | clean (the files it would change are listed) |
| G0 | `clippy` | `cargo clippy --release -p <crate> --no-deps --all-targets -- -D warnings` per crate | no lint the baseline does not know; a crate that does not compile is a fail |
| G0 | `cargo-test` | `cargo test --release -p <crate>` for dc2tk-disc, dc2tk-script, dc2tk-assets, dc2tk, one at a time | no failing test the baseline does not know; a crate that does not build is a fail |
| G0 | `tool-tests` | `python3 -I tools/test_engine_mods.py`, `tools/test_native_prepare.py` | both exit 0 |
| G0 | `port-tests` | `python3 -I port/tests/run.py` with clang 20 on PATH and the SDK at `build/port/sdk` (`--iso` when a disc is named) | no new failure against the baseline; not run without the SDK |
| G1 | `limits` | `cargo test --release -p dc2tk-assets limits` | every matching test passes; not run while none matches |
| G5 | `port-golden` | `tools/golden_port.py` over `port/tests/golden/*.json` against `build/port/dc2-debug` | every scenario's screenshots within tolerance of the approved set in `build/port/golden/baseline-linux`; not run without `dc2.iso`, the debug port or an approved set |
| G5 | `event-sweep` | `tools/event_sweep.py` (every row of `extracted/disc/event/view_pal.txt`) | exit 0 and no event crashed or hung; not run without the disc, the debug port or the extracted event list |

The disc stages read `dc2.iso` at the repository root, as the tools do; `--iso` or `DC2_ISO` naming a disc
elsewhere is reported with the hint to link it there. Approving the golden screenshots
(`tools/golden_port.py --update`) is a *(hands)* step: a person looks at the pictures first.

## Baseline

`tools/gauntlet/baselines/linux-x86_64.json` holds, per key (`clippy`, `cargo-test`, `port-tests`), what
failed when it was written, with the counts, the git head and the date. The verdict is "no new failures",
and a case the baseline knows that passes now is reported as fixed. `--update-baseline` writes the current
failures; use it on a machine's first run and to record fixes, never to make a regression known.

What the baseline knows on this machine (PLAN.md "Checks" names them as predating this work):

- `clippy`: `dc2tk-assets::single_element_loop@crates/dc2tk-assets/src/map_export.rs` (clippy 1.99). Lints
  are keyed by crate, lint name and file, not line, so unrelated edits do not move them.
- `cargo-test`: none. PLAN.md says `a_disc_is_not_written_over_the_image_it_is_made_from` (dc2tk-disc)
  fails on Linux; it passed when the baseline was taken, so a failure of it now would be new and red, which
  is the right answer for a regression. The run that wrote the baseline caught
  `limits::tests::the_port_profile_holds_the_headers_values_and_retail_where_the_engine_keeps_it` failing
  in dc2tk-assets while work package B was writing it; that is in-progress work, not a known failure, and
  it was taken out of the file by hand (the file's `note` says so). A baseline written while someone else
  is editing must be read before it is trusted.
- `port-tests`: none; the 23 native checks pass with clang 20.

Reports go to `tools/gauntlet/report/<timestamp>/report.json` and `report.md` with a `latest` symlink; each
stage's logs sit beside them (`.gitignore` keeps the logs out and the two report files in). Exit 0 only when
every stage that ran passed and no stage errored. The protocol for an agent (run order, reproducing a failure
with the recorded command, never skipping a test or bumping a baseline to hide a regression, lines for a human
marked *(hands)*) is ChronicleTwo's `GAUNTLET.md`, "Agent protocol".

## Environment notes

- The system clang is 18; the port and its tests want 20, which is at `/opt/clang20/bin`. The runner puts
  it first on PATH for `env`, `port-tests`, `tool-tests` and the disc stages; a person runs
  `PATH=/opt/clang20/bin:$PATH python3 -I port/tests/run.py`.
- The port SDK (`build/port/sdk`) is built by `tools/port_sdk.py`; pkg-config does not see its SDL3, which is
  fine. `ffmpeg.org` is unreachable through this machine's proxy (connection reset), so its FFmpeg 8.0.1 was
  built from `git clone --depth 1 --branch n8.0.1 https://github.com/FFmpeg/FFmpeg
  build/port/sdk-work/ffmpeg-8.0.1`, calling `port_sdk.build_ffmpeg()` with `fetch` replaced by that folder
  (same configure flags); SDL's GitHub release tarball downloads. The work folders under `sdk-work` can go
  once the SDK is installed.
- Disk: after a gauntlet run remove `build/release` (the cargo target, a few GB even without debug info)
  unless another stage needs it next; never all of `build/`, which holds the port SDK. Check `df -h /` before
  a cargo stage; under 4 GB free, stop and say so.
- Another agent's uncommitted edits in `src/` can make `fmt` or a crate fail while they work. That is a
  stage failure in the report, as it should be, not a runner problem; rerun once they have committed.
