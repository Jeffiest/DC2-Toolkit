"""Tests of the toolkit runner's parsers: python3 -I tools/gauntlet/test_gauntlet.py"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import run  # noqa: E402

CLIPPY = """\
    Checking dc2tk-assets v0.1.0
error: for loop over a single element
   --> crates/dc2tk-assets/src/map_export.rs:232:17
    |
232 |                 for layer in [&scene.layer] {
    |
    = help: for further information visit https://rust-lang.github.io/rust-clippy/rust-1.99.0/index.html#single_element_loop
    = note: `-D clippy::single-element-loop` implied by `-D warnings`

error: could not compile `dc2tk-assets` (lib) due to 1 previous error
warning: build failed, waiting for other jobs to finish...
"""

BROKEN = """\
   Compiling dc2tk-assets v0.1.0
error[E0425]: cannot find value `limit` in this scope
   --> crates/dc2tk-assets/src/limits.rs:10:5
error: could not compile `dc2tk-assets` (lib) due to 1 previous error
"""

CARGO = """\
running 3 tests
test rebuild::tests::a_disc_is_not_written_over_the_image_it_is_made_from ... FAILED
test text::tests::ascii_and_kana_round_trip ... ok
test slow::tests::needs_a_disc ... ignored
test result: FAILED. 1 passed; 1 failed; 1 ignored
"""

PORT = """\
devices: passed
graphics: FAILED (exit 1)
math_bits: O0/O2 outputs match
movie_decode: passed
kernel checks passed
kernel: passed
cdvd checks passed
"""


class ParserTest(unittest.TestCase):
    def test_clippy_lints_are_named_without_line_numbers(self):
        self.assertEqual(run.clippy_lints(CLIPPY, "dc2tk-assets"),
                         ["dc2tk-assets::single_element_loop@crates/dc2tk-assets/src/map_export.rs"])
        self.assertEqual(run.compile_errors(CLIPPY), [])

    def test_compile_errors_are_not_lints(self):
        self.assertEqual(run.clippy_lints(BROKEN, "dc2tk-assets"), [])
        self.assertEqual(run.compile_errors(BROKEN), ["error[E0425]: cannot find value `limit` in this scope"])

    def test_cargo_results(self):
        passed, failed, ignored = run.cargo_results(CARGO)
        self.assertEqual(failed, ["rebuild::tests::a_disc_is_not_written_over_the_image_it_is_made_from"])
        self.assertEqual(passed, ["text::tests::ascii_and_kana_round_trip"])
        self.assertEqual(ignored, ["slow::tests::needs_a_disc"])

    def test_port_results(self):
        passed, failed = run.port_results(PORT)
        self.assertEqual(sorted(passed), ["cdvd", "devices", "kernel", "math_bits", "movie_decode"])
        self.assertEqual(failed, ["graphics"])

    def test_stages_are_in_gate_order_with_unique_names(self):
        gates = [g for _, g, _ in run.STAGES]
        self.assertEqual(gates, sorted(gates))
        names = [n for n, _, _ in run.STAGES]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(run.main(["--list"]), 0)

    def test_cargo_settings_keep_the_target_small(self):
        self.assertEqual(run.CARGO_ENV, {"CARGO_INCREMENTAL": "0", "CARGO_PROFILE_RELEASE_DEBUG": "0"})
        self.assertEqual({k: run._path_env()[k] for k in run.CARGO_ENV}, run.CARGO_ENV)

    def test_disk_guard(self):
        ctx = {"options": {"min_free_gb": 0}}
        self.assertIsNone(run._disk_guard(ctx, "clippy", "G0"))
        ctx["options"]["min_free_gb"] = 1e9
        result = run._disk_guard(ctx, "clippy", "G0")
        self.assertEqual(result["status"], "error")
        self.assertIn("GB free", result["summary"])
        self.assertEqual(run.stage_clippy(ctx)["status"], "error")
        self.assertEqual(run.stage_limits(ctx)["status"], "error")


if __name__ == "__main__":
    unittest.main(verbosity=1)
