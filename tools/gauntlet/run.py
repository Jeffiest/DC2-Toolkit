"""The DC2-Toolkit side of the gauntlet (GAUNTLET.md here; the full protocol is ChronicleTwo/GAUNTLET.md).

  python3 -I tools/gauntlet/run.py                   every stage; stops at the first red gate
  python3 -I tools/gauntlet/run.py --gate G0         one gate (G0 crates and tools, G1 limits, G5 disc)
  python3 -I tools/gauntlet/run.py --stage clippy --stage cargo-test --update-baseline
  python3 -I tools/gauntlet/run.py --json            print only the report path

Runs this repository's checks (PLAN.md "Checks") and writes the same report schema as ChronicleTwo's
runner: tools/gauntlet/report/<timestamp>/report.json and report.md, with a `latest` symlink. The report
and baseline modules are imported from ChronicleTwo/tools/gauntlet beside this tree (or $CHRONICLE_TWO).
Exit 0 only when every stage that ran passed and no stage errored. A crate that does not compile is a
failed stage (the code under test is broken), never a crash of the runner.
"""
import argparse
import datetime
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CHRONICLE_TWO = os.environ.get("CHRONICLE_TWO") or os.path.join(os.path.dirname(ROOT), "ChronicleTwo")
sys.path.insert(0, os.path.join(CHRONICLE_TWO, "tools", "gauntlet"))
try:
    from gauntlet import baseline, report, util  # noqa: E402
except ImportError:
    sys.exit("the gauntlet package is %s/tools/gauntlet/gauntlet; set CHRONICLE_TWO to the ChronicleTwo checkout" % CHRONICLE_TWO)

GATES = ["G0", "G1", "G5"]
CRATES = ["dc2tk-disc", "dc2tk-script", "dc2tk-assets", "dc2tk"]
TOOL_TESTS = ["tools/test_engine_mods.py", "tools/test_native_prepare.py"]
# port/tests/run.py and the port build want clang 20 (the system clang is 18): this directory goes first on PATH.
CLANG_BIN = os.environ.get("DC2TK_CLANG_BIN") or "/opt/clang20/bin"
SDK = os.path.join(ROOT, "build", "port", "sdk")
DEBUG_BINARY = os.path.join(ROOT, "build", "port", "dc2-debug")
GOLDEN_BASELINE = os.path.join(ROOT, "build", "port", "golden", "baseline-linux")
EVENT_LIST = os.path.join(ROOT, "extracted", "disc", "event", "view_pal.txt")
# The release profile keeps debug = 1, which made build/release 8 GB on a shared 40 GB disk; the gauntlet's
# builds need no debug info and no incremental cache (about a third of that). The cargo commands the report
# records carry these, so a reproduction builds the same way.
CARGO_ENV = {"CARGO_INCREMENTAL": "0", "CARGO_PROFILE_RELEASE_DEBUG": "0"}
CARGO_PREFIX = " ".join("%s=%s" % kv for kv in sorted(CARGO_ENV.items()))


def _out(ctx, name):
    path = os.path.join(ctx["report_dir"], name)
    os.makedirs(path, exist_ok=True)
    return path


def _disk_guard(ctx, name, gate):
    """An error stage when the disk holding the cargo target has less than --min-free-gb free (a build on a
    full disk fails like a broken crate), else None."""
    minimum = ctx["options"].get("min_free_gb", 4.0)
    free = util.disk_free_gb(os.path.join(ROOT, "build")) if hasattr(util, "disk_free_gb") else None
    if free is None or not minimum or free >= minimum:
        return None
    return report.stage(name, gate, "error", "only %.1f GB free on the disk holding %s/build (the gauntlet wants %.1f GB, --min-free-gb): "
                        "free space first; the stage did not start" % (free, ROOT, minimum), details={"free_gb": round(free, 2)})


def _path_env():
    """clang 20 first on PATH, and the cargo settings above for any tool that builds the crates."""
    env = dict(CARGO_ENV)
    if os.path.isdir(CLANG_BIN):
        env["PATH"] = CLANG_BIN + os.pathsep + os.environ.get("PATH", "")
    return env


def _version(cmd, pattern, env=None):
    result = util.run(cmd, timeout=60, env=env)
    match = re.search(pattern, result["output"])
    return (match.group(1) if match else None), (result["output"].splitlines() or [""])[0]


def _disc(ctx):
    """The retail image the disc tools read: --iso, DC2_ISO or dc2.iso at the repository root."""
    for candidate in (ctx["options"].get("iso"), os.environ.get("DC2_ISO"), os.path.join(ROOT, "dc2.iso")):
        if candidate and os.path.isfile(candidate):
            return candidate
    return None


def stage_env(ctx):
    started = time.monotonic()
    checks = []

    def add(name, required, ok, detail):
        checks.append({"name": name, "required": required, "ok": bool(ok), "detail": detail})
    version, line = _version(["rustc", "--version"], r"rustc (\d+\.\d+)")
    add("rustc", True, version == "1.99", line or "rustc not found")
    version, line = _version(["cargo", "--version"], r"cargo (\d+\.\d+)")
    add("cargo", True, version is not None, line)
    version, line = _version(["clang", "--version"], r"clang version (\d+)", env=_path_env())
    add("clang", True, version == "20", (line or "clang not found") + " (PATH has %s first)" % CLANG_BIN if os.path.isdir(CLANG_BIN)
        else (line or "clang not found") + "; %s is absent, set DC2TK_CLANG_BIN" % CLANG_BIN)
    version, line = _version(["pkg-config", "--modversion", "sdl3"], r"(\d+\.\d+\.\d+)")
    add("sdl3", False, version is not None, line or "pkg-config finds no sdl3 (the port's SDK is built into build/port/sdk)")
    add("python", True, sys.version_info >= (3, 10), sys.version.split()[0])
    add("workspace", True, os.path.isfile(os.path.join(ROOT, "src", "Cargo.toml")), os.path.join(ROOT, "src", "Cargo.toml"))
    add("port-sdk", False, os.path.isdir(os.path.join(SDK, "include")), SDK + ("" if os.path.isdir(os.path.join(SDK, "include"))
                                                                          else " absent: tools/port_sdk.py builds it; port-tests will not run"))
    add("dc2-debug", False, os.path.isfile(DEBUG_BINARY), DEBUG_BINARY if os.path.isfile(DEBUG_BINARY) else DEBUG_BINARY + " absent (tools/port.py builds it); the disc stages will not run")
    disc = _disc(ctx)
    add("disc", False, disc is not None, disc or "no dc2.iso at the root, DC2_ISO or --iso: the disc stages will not run")
    failed = [c["name"] for c in checks if c["required"] and not c["ok"]]
    out = _out(ctx, "env")
    util.write_json(os.path.join(out, "env.json"), {"checks": checks})
    with open(os.path.join(out, "env.txt"), "w") as f:
        for c in checks:
            f.write("%-12s %-4s %s %s\n" % (c["name"], "ok" if c["ok"] else "MISS", "required" if c["required"] else "optional", c["detail"]))
    summary = "%d checks" % len(checks) + ("; required failing: " + ", ".join(failed) if failed else "")
    missing = [c["name"] for c in checks if not c["required"] and not c["ok"]]
    if missing:
        summary += "; optional absent: " + ", ".join(missing)
    return report.stage("env", "G0", "fail" if failed else "pass", summary, time.monotonic() - started,
                        "python3 -I tools/gauntlet/run.py --stage env", None, [os.path.join(out, "env.json"), os.path.join(out, "env.txt")],
                        details={"checks": checks})


def cargo_results(output):
    """The passed, failed and ignored test names in cargo test output."""
    passed, failed, ignored = [], [], []
    for line in output.splitlines():
        match = re.match(r"test (\S+) \.\.\. (ok|FAILED|ignored)", line)
        if not match:
            continue
        {"ok": passed, "FAILED": failed, "ignored": ignored}[match.group(2)].append(match.group(1))
    return passed, failed, ignored


def compile_errors(output):
    """rustc diagnostics that are not clippy lints: error[E0xxx] codes, and plain errors without a clippy help link."""
    errors = []
    for block in re.split(r"\n(?=(?:error|warning)(?:\[[^\]]*\])?: )", "\n" + output):
        head = block.strip().splitlines()[0] if block.strip() else ""
        if not head.startswith("error"):
            continue
        if re.match(r"error: (could not compile|build failed|aborting due to)", head):
            continue
        if "rust-lang.github.io/rust-clippy" in block:
            continue
        errors.append(head)
    return errors


def clippy_lints(output, crate):
    """Every clippy lint in the output as crate::lint@file (no line numbers: those move with unrelated edits)."""
    lints = []
    for block in re.split(r"\n(?=(?:error|warning)(?:\[[^\]]*\])?: )", "\n" + output):
        if "rust-lang.github.io/rust-clippy" not in block:
            continue
        lint = re.search(r"index\.html#(\w+)", block)
        where = re.search(r"-->\s+(\S+?):\d+:\d+", block)
        head = block.strip().splitlines()[0]
        name = lint.group(1) if lint else re.sub(r"\W+", "_", head.split(": ", 1)[-1]).strip("_")[:60]
        lints.append("%s::%s@%s" % (crate, name, where.group(1) if where else "?"))
    return lints


def _baseline_verdict(ctx, key, failures, ran, counts):
    data = baseline.load(ctx["baseline_path"])
    delta = baseline.diff(failures, ran, data, key)
    if ctx["options"]["update_baseline"]:
        before = {k: delta[k] for k in ("new", "known", "fixed", "has_baseline")}
        data = baseline.update(ctx["baseline_path"], key, failures, counts, head=ctx["repos"]["DC2-Toolkit"].get("head"),
                               note="written by tools/gauntlet/run.py --update-baseline")
        delta = baseline.diff(failures, ran, data, key)
        delta["written"] = ctx["baseline_path"]
        delta["before_rewrite"] = before
    if not delta["has_baseline"]:
        return "error", "; no baseline for %r in %s: run once with --update-baseline" % (key, ctx["baseline_path"]), delta
    tail = "; %d new, %d known, %d fixed against %s" % (len(delta["new"]), len(delta["known"]), len(delta["fixed"]),
                                                         os.path.basename(ctx["baseline_path"]))
    if "written" in delta:
        tail += " (baseline rewritten: %d were new, %d fixed before)" % (len(delta["before_rewrite"]["new"]), len(delta["before_rewrite"]["fixed"]))
    return ("fail" if delta["new"] else "pass"), tail, delta


def stage_fmt(ctx):
    out = _out(ctx, "fmt")
    result = util.run(["cargo", "fmt", "--all", "--", "--check"], log=os.path.join(out, "fmt.log"), cwd=os.path.join(ROOT, "src"), timeout=600)
    files = sorted(set(re.findall(r"^Diff in (\S+?):\d+", result["output"], re.M)))
    summary = "cargo fmt --check " + ("clean" if result["exit"] == 0 else "wants changes in %d file(s): %s" % (
        len(files), ", ".join(os.path.relpath(f, os.path.join(ROOT, "src")) for f in files[:6])) if files else "failed: " + util.tail(result["output"], 2))
    return report.stage("fmt", "G0", "pass" if result["exit"] == 0 else "fail", summary, result["duration"],
                        "(cd src && %s)" % result["command"], result["log"], [result["log"]], details={"files": files})


def stage_clippy(ctx):
    full = _disk_guard(ctx, "clippy", "G0")
    if full:
        return full
    out = _out(ctx, "clippy")
    lints, broken, evidence, commands = [], [], [], []
    duration = 0.0
    for crate in CRATES:
        result = util.run(["cargo", "clippy", "--release", "-p", crate, "--no-deps", "--all-targets", "--", "-D", "warnings"],
                          log=os.path.join(out, crate + ".log"), cwd=os.path.join(ROOT, "src"), timeout=ctx["options"]["timeout"], env=CARGO_ENV)
        duration += result["duration"]
        evidence.append(result["log"])
        commands.append("(cd src && %s %s)" % (CARGO_PREFIX, result["command"]))
        lints += clippy_lints(result["output"], crate)
        errors = compile_errors(result["output"])
        if errors or (result["exit"] != 0 and not lints):
            broken.append("%s: %s" % (crate, (errors or [util.tail(result["output"], 1)])[0][:160]))
    lints = sorted(set(lints))
    counts = {"crates": len(CRATES), "lints": len(lints), "did_not_compile": len(broken)}
    if broken:
        return report.stage("clippy", "G0", "fail", "%d crate(s) did not compile: %s" % (len(broken), "; ".join(broken)), duration,
                            " ; ".join(commands), None, evidence, details={"counts": counts, "lints": lints, "broken": broken})
    status, tail, delta = _baseline_verdict(ctx, "clippy", lints, lints, counts)
    summary = "%d crate(s), %d lint(s)" % (len(CRATES), len(lints)) + tail
    return report.stage("clippy", "G0", status, summary, duration, " ; ".join(commands), None, evidence, baseline=delta,
                        details={"counts": counts, "lints": lints})


def stage_cargo_test(ctx):
    full = _disk_guard(ctx, "cargo-test", "G0")
    if full:
        return full
    out = _out(ctx, "cargo-test")
    total_passed, total_failed, total_ignored, broken, evidence, commands = [], [], [], [], [], []
    duration = 0.0
    for crate in CRATES:
        result = util.run(["cargo", "test", "--release", "-p", crate], log=os.path.join(out, crate + ".log"),
                          cwd=os.path.join(ROOT, "src"), timeout=ctx["options"]["timeout"], env=CARGO_ENV)
        duration += result["duration"]
        evidence.append(result["log"])
        commands.append("(cd src && %s %s)" % (CARGO_PREFIX, result["command"]))
        passed, failed, ignored = cargo_results(result["output"])
        if result["exit"] != 0 and not failed and not passed:
            broken.append("%s: %s" % (crate, (compile_errors(result["output"]) or [util.tail(result["output"], 1)])[0][:160]))
        total_passed += ["%s::%s" % (crate, n) for n in passed]
        total_failed += ["%s::%s" % (crate, n) for n in failed]
        total_ignored += ["%s::%s" % (crate, n) for n in ignored]
    counts = {"total": len(total_passed) + len(total_failed), "passed": len(total_passed), "failed": len(total_failed),
              "ignored": len(total_ignored), "did_not_compile": len(broken)}
    if broken:
        return report.stage("cargo-test", "G0", "fail", "%d crate(s) did not build or run: %s" % (len(broken), "; ".join(broken)), duration,
                            " ; ".join(commands), None, evidence, details={"counts": counts, "failures": total_failed, "broken": broken})
    status, tail, delta = _baseline_verdict(ctx, "cargo-test", total_failed, total_passed + total_failed, counts)
    summary = "%d tests in %d crates: %d passed, %d failed, %d ignored" % (counts["total"], len(CRATES), counts["passed"], counts["failed"],
                                                                        counts["ignored"]) + tail
    return report.stage("cargo-test", "G0", status, summary, duration, " ; ".join(commands), None, evidence, baseline=delta,
                        details={"counts": counts, "failures": total_failed})


def stage_tool_tests(ctx):
    out = _out(ctx, "tool-tests")
    failed, evidence, commands = [], [], []
    duration = 0.0
    for test in TOOL_TESTS:
        result = util.run([sys.executable, "-I", test], log=os.path.join(out, os.path.basename(test) + ".log"), cwd=ROOT, timeout=1800,
                          env=_path_env())
        duration += result["duration"]
        evidence.append(result["log"])
        commands.append(result["command"])
        if result["exit"] != 0:
            failed.append("%s (exit %d: %s)" % (test, result["exit"], util.tail(result["output"], 1)[:120]))
    summary = "%d test scripts, %d failed" % (len(TOOL_TESTS), len(failed)) + (": " + "; ".join(failed) if failed else "")
    return report.stage("tool-tests", "G0", "fail" if failed else "pass", summary, duration, " ; ".join(commands), None, evidence,
                        details={"failed": failed})


def port_results(output):
    """port/tests/run.py prints `name: passed` / `name: FAILED (why)`, plus two fixed lines for math_bits and movie_decode."""
    passed = re.findall(r"^(\w+): passed$", output, re.M) + ["math_bits"] * len(re.findall(r"^math_bits: O0/O2 outputs match$", output, re.M))
    for name in re.findall(r"^(\w+) (?:checks|tests) passed$", output, re.M):  # cdvd.py's own line; kernel and co. also print name: passed
        if name not in passed:
            passed.append(name)
    failed = re.findall(r"^(\w+): FAILED", output, re.M)
    return passed, failed


def stage_port_tests(ctx):
    if not os.path.isdir(os.path.join(SDK, "include")):
        return report.stage("port-tests", "G0", "not_run", "no port SDK at %s (python3 -I tools/port_sdk.py builds it)" % SDK)
    out = _out(ctx, "port-tests")
    disc = _disc(ctx)
    cmd = [sys.executable, "-I", "port/tests/run.py"] + (["--iso", disc] if disc else [])
    result = util.run(cmd, log=os.path.join(out, "port-tests.log"), cwd=ROOT, timeout=ctx["options"]["timeout"], env=_path_env())
    passed, failed = port_results(result["output"])
    reproduce = "PATH=%s:$PATH %s" % (CLANG_BIN, result["command"])
    if not passed and not failed:
        return report.stage("port-tests", "G0", "fail", "port/tests/run.py produced no results (exit %d): %s" % (
            result["exit"], util.tail(result["output"], 3)[:300]), result["duration"], reproduce, result["log"], [result["log"]])
    if result["exit"] != 0 and not failed:
        failed = ["run.py (exit %d)" % result["exit"]]
    counts = {"total": len(passed) + len(failed), "passed": len(passed), "failed": len(failed), "iso": bool(disc)}
    status, tail, delta = _baseline_verdict(ctx, "port-tests", failed, passed + failed, counts)
    summary = "%d native checks%s: %d passed, %d failed" % (counts["total"], " (with the retail movies)" if disc else "", counts["passed"],
                                                           counts["failed"]) + tail
    return report.stage("port-tests", "G0", status, summary, result["duration"], reproduce, result["log"], [result["log"]],
                        baseline=delta, details={"counts": counts, "failures": failed})


def stage_limits(ctx):
    full = _disk_guard(ctx, "limits", "G1")
    if full:
        return full
    out = _out(ctx, "limits")
    cmd = ["cargo", "test", "--release", "-p", "dc2tk-assets", "limits"]
    result = util.run(cmd, log=os.path.join(out, "limits.log"), cwd=os.path.join(ROOT, "src"), timeout=ctx["options"]["timeout"], env=CARGO_ENV)
    passed, failed, _ = cargo_results(result["output"])
    reproduce = "(cd src && %s %s)" % (CARGO_PREFIX, result["command"])
    if result["exit"] != 0 and not passed and not failed:
        return report.stage("limits", "G1", "fail", "dc2tk-assets did not build: " + util.tail(result["output"], 2)[:300], result["duration"],
                            reproduce, result["log"], [result["log"]])
    if result["exit"] == 0 and not passed:
        return report.stage("limits", "G1", "not_run", "no dc2tk-assets test matches 'limits' yet (work package B)", result["duration"],
                            reproduce, result["log"], [result["log"]])
    status = "pass" if result["exit"] == 0 else "fail"
    summary = "%d limit test(s), %d failed" % (len(passed) + len(failed), len(failed)) + (": " + ", ".join(failed) if failed else "")
    return report.stage("limits", "G1", status, summary, result["duration"], reproduce, result["log"], [result["log"]],
                        details={"passed": passed, "failed": failed})


def _disc_ready(ctx, name):
    disc = _disc(ctx)
    if not disc:
        return report.stage(name, "G5", "not_run", "no retail disc (dc2.iso at the root, DC2_ISO or --iso)")
    if not os.path.isfile(os.path.join(ROOT, "dc2.iso")):
        return report.stage(name, "G5", "not_run", "the disc tools read dc2.iso at the repository root; link %s there" % disc)
    if not os.path.isfile(DEBUG_BINARY):
        return report.stage(name, "G5", "not_run", "no %s (python3 -I tools/port.py builds the debug port)" % DEBUG_BINARY)
    return None


def stage_port_golden(ctx):
    blocked = _disc_ready(ctx, "port-golden")
    if blocked:
        return blocked
    if not os.path.isdir(GOLDEN_BASELINE):
        return report.stage("port-golden", "G5", "not_run", "no approved golden screenshots in %s: a person looks at the shots, then "
                            "tools/golden_port.py --update writes them (hands)" % GOLDEN_BASELINE)
    out = _out(ctx, "port-golden")
    result = util.run([sys.executable, "-I", "tools/golden_port.py"], log=os.path.join(out, "golden.log"), cwd=ROOT,
                      timeout=ctx["options"]["timeout"], env=_path_env())
    match = re.search(r"^(\d+) of (\d+) scenarios passed", result["output"], re.M)
    evidence = [result["log"]]
    diff_dir = os.path.join(ROOT, "build", "port", "golden", "diff")
    if os.path.isdir(diff_dir):
        evidence.append(diff_dir)
    if not match:
        return report.stage("port-golden", "G5", "fail", "golden_port.py gave no verdict (exit %d): %s" % (result["exit"], util.tail(result["output"], 2)[:300]),
                            result["duration"], result["command"], result["log"], evidence)
    ok = result["exit"] == 0 and match.group(1) == match.group(2)
    return report.stage("port-golden", "G5", "pass" if ok else "fail", "%s of %s golden scenarios passed" % match.groups(), result["duration"],
                        result["command"], result["log"], evidence, details={"passed": int(match.group(1)), "total": int(match.group(2))})


def stage_event_sweep(ctx):
    blocked = _disc_ready(ctx, "event-sweep")
    if blocked:
        return blocked
    if not os.path.isfile(EVENT_LIST):
        return report.stage("event-sweep", "G5", "not_run", "no %s (dc2tk extract writes it)" % EVENT_LIST)
    out = _out(ctx, "event-sweep")
    result = util.run([sys.executable, "-I", "tools/event_sweep.py"], log=os.path.join(out, "sweep.log"), cwd=ROOT,
                      timeout=ctx["options"]["timeout"], env=_path_env())
    sweep = os.path.join(ROOT, "build", "port", "event-sweep.json")
    evidence = [result["log"]] + ([sweep] if os.path.isfile(sweep) else [])
    data = util.read_json(sweep, default=None)
    bad = []
    if isinstance(data, list):
        bad = [e for e in data if isinstance(e, dict) and e.get("result") not in (None, "ok", "passed")]
    elif isinstance(data, dict):
        bad = [k for k, v in data.items() if isinstance(v, dict) and v.get("result") not in (None, "ok", "passed")]
    ok = result["exit"] == 0 and not bad
    summary = "event sweep exit %d, %d event(s) crashed or hung" % (result["exit"], len(bad))
    return report.stage("event-sweep", "G5", "pass" if ok else "fail", summary, result["duration"], result["command"], result["log"],
                        evidence, details={"bad": bad[:50]})


STAGES = [("env", "G0", stage_env), ("fmt", "G0", stage_fmt), ("clippy", "G0", stage_clippy), ("cargo-test", "G0", stage_cargo_test),
          ("tool-tests", "G0", stage_tool_tests), ("port-tests", "G0", stage_port_tests), ("limits", "G1", stage_limits),
          ("port-golden", "G5", stage_port_golden), ("event-sweep", "G5", stage_event_sweep)]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--gate", action="append", default=[], choices=GATES)
    ap.add_argument("--stage", action="append", default=[], choices=[s[0] for s in STAGES])
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--update-baseline", action="store_true")
    ap.add_argument("--keep-going", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--timeout", type=int, default=3600)
    ap.add_argument("--iso", help="retail disc for port/tests/run.py --iso and the disc stages (else DC2_ISO, dc2.iso)")
    ap.add_argument("--report-dir")
    ap.add_argument("--min-free-gb", type=float, default=4.0, help="cargo stages do not start with less free disk (0: no check)")
    options = ap.parse_args(argv)
    if options.list:
        for name, gate, _ in STAGES:
            print("%s  %s" % (gate, name))
        return 0
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    report_dir = os.path.abspath(options.report_dir) if options.report_dir else os.path.join(HERE, "report", stamp)
    repos = {"DC2-Toolkit": util.git_head(ROOT), "ChronicleTwo": util.git_head(CHRONICLE_TWO)}
    ctx = {"root": ROOT, "report_dir": report_dir, "repos": repos,
           "baseline_path": os.path.join(HERE, "baselines", baseline.platform_name() + ".json"),
           "options": {"update_baseline": options.update_baseline, "timeout": options.timeout, "iso": options.iso,
                       "keep_going": options.keep_going, "min_free_gb": options.min_free_gb}}
    os.makedirs(report_dir, exist_ok=True)
    rep = report.new_report(argv, ctx["options"], repos)
    rep["repository"] = "DC2-Toolkit"
    rep["baseline"] = ctx["baseline_path"]
    chosen = [(n, g, f) for n, g, f in STAGES if (not options.gate and not options.stage) or g in options.gate or n in options.stage]
    red = None
    for name, gate, func in chosen:
        if red and gate > red and not options.keep_going:
            result = report.stage(name, gate, "not_run", "gate %s is not green; %s does not start" % (red, gate))
        else:
            if not options.json:
                print("[%s] %s ..." % (gate, name), flush=True)
            started = time.monotonic()
            try:
                result = func(ctx)
            except Exception as e:  # a bug in the stage itself is an error, never a pass
                import traceback
                result = report.stage(name, gate, "error", "stage raised %s: %s" % (type(e).__name__, e), time.monotonic() - started,
                                      details={"traceback": traceback.format_exc()})
            if result["status"] in ("fail", "error") and (red is None or gate < red):
                red = gate
        rep["stages"].append(result)
        if not options.json:
            print("[%s] %s: %s  %s" % (gate, name, result["status"].upper(), result["summary"]), flush=True)
        report.write(rep, report_dir)
    path = report.write(rep, report_dir)
    print(path if options.json else "\n%s: %s (report %s)" % (rep["verdict"].upper(), ", ".join("%s %s" % (s["name"], s["status"]) for s in rep["stages"]), path))
    return rep["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
