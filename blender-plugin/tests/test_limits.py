"""The add-on's limits reader (dc2tk_maps/limits.py), outside Blender: the checked-in limits.json
is the toolkit's table, retail is the game's, port never lowers a limit, and a file of another
shape is an error naming it. Run `python3 -I blender-plugin/tests/test_limits.py`; the checks that
need Blender's preferences are in test_tools.py (check_budgets)."""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.join(os.path.dirname(HERE), "dc2tk_maps")
RETAIL = {
    "town_placements": 320,
    "dungeon_placements": 400,
    "floor_monsters": 32,
    "chest_groups": 64,
    "chest_group_items": 96,
    "chest_floor_groups": 64,
    "georama_parts": 0x180,
    "georama_placed": 0x100,
    "townspeople": 180,
    "common_items": 432,
    "item_numbers": 0x1FF,
    "weapon_records": 116,
    "item_records": 162,
    "shop_goods": 64,
    "statement_args": 64,
    "layout_rooms": 64,
    "layout_cells": 900,
}


def load_module():
    spec = importlib.util.spec_from_file_location("dc2tk_maps_limits", os.path.join(ADDON, "limits.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(condition, text):
    if not condition:
        raise AssertionError(text)


def refused(limits, data, wanted):
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "limits.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        try:
            limits.load(path)
        except ValueError as error:
            check(path in str(error) and wanted in str(error), "the error names the file and %r: %s" % (wanted, error))
        else:
            raise AssertionError("accepted %r" % (data,))


def main():
    limits = load_module()
    table = limits.table()
    check(list(table) == list(RETAIL), "the table lists the toolkit's limits in order: %s" % list(table))
    for name, value in RETAIL.items():
        check(limits.value(name, "retail") == value, "%s is %d in retail, not %d" % (name, value, limits.value(name, "retail")))
        check(limits.value(name, "port") >= value, "%s is lower in port" % name)
        check(table[name]["constant"] and table[name]["what"], "%s names its constant and what it counts" % name)
    check(limits.value("floor_monsters", "port") == 128, "port raises MONSTER_LOCATE_MAX")
    check(limits.value("statement_args", "port") == 64, "port keeps SPI_STACK_SIZE")
    check(limits.placements("t01", "retail") == 320 and limits.placements("d01", "retail") == 400, "placements by map kind")
    check(limits.placements("d05f", "port") == limits.value("dungeon_placements", "port"), "a dungeon's placements in port")
    check(limits.profile() == "retail", "outside Blender the profile is retail")
    check(limits.describe("retail").startswith("retail (") and "runs only on it" in limits.describe("port"), "descriptions")
    for wrong in ({"name": "x", "profile": "ps2"}, {"name": "no_such", "profile": "retail"}):
        try:
            limits.value(wrong["name"], wrong["profile"])
        except (KeyError, ValueError):
            pass
        else:
            raise AssertionError("accepted %r" % wrong)

    with open(limits.PATH, encoding="utf-8") as handle:
        data = json.load(handle)
    row = dict(data["limits"][0])
    refused(limits, {"profiles": ["retail"], "limits": data["limits"]}, "profiles")
    refused(limits, {"profiles": data["profiles"], "limits": []}, "list of limits")
    refused(limits, {"profiles": data["profiles"], "limits": [row, row]}, "listed twice")
    refused(limits, {"profiles": data["profiles"], "limits": [dict(row, port=row["retail"] - 1)]}, "lower in port")
    refused(limits, {"profiles": data["profiles"], "limits": [dict(row, retail="320")]}, "whole number")
    refused(limits, {"profiles": data["profiles"], "limits": [dict(row, retail=True)]}, "whole number")
    refused(limits, {"profiles": data["profiles"], "limits": [{"name": "", "retail": 1, "port": 1}]}, "without a name")
    refused(limits, {"profiles": data["profiles"], "limits": [dict(row, what=None)]}, "\"what\"")

    # a built dc2tk writes this very file
    root = os.path.dirname(os.path.dirname(HERE))
    for candidate in ("dc2tk", "dc2tk.exe"):
        binary = os.path.join(root, "build", "release", candidate)
        if os.path.isfile(binary):
            written = subprocess.run([binary, "limits", "--json"], capture_output=True, text=True, check=True).stdout
            with open(limits.PATH, encoding="utf-8") as handle:
                check(written == handle.read(), "dc2tk limits --json differs from limits.json")
            break
    print("limits reader: %d limits in %s pass" % (len(table), ", ".join(limits.PROFILES)))


if __name__ == "__main__":
    main()
