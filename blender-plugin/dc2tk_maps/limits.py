"""The capacity limits the add-on checks a map against, in two profiles: retail (the PS2 game's, the
default) and port (the raised native engine's; content over the retail limits runs only on it). The
numbers are limits.json beside this file, the table `dc2tk limits --json` writes, which a test of the
toolkit keeps equal to its own table (docs/guide/limits.md). The profile is the add-on preference
limits_profile; every function takes a profile, or reads that preference."""

import json
import os

PROFILES = ("retail", "port")
DEFAULT = "retail"
PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "limits.json")
DESCRIPTIONS = {
    "retail": "retail (the PS2 game's limits)",
    "port": "port (the raised engine's limits; the content runs only on it)",
}

_loaded = {}


def _whole(path, value, what):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("%s: %s is not a whole number (%r)" % (path, what, value))
    return value


def load(path=PATH):
    """The table of the JSON at path: {name: {"constant", "what", "retail", "port"}}, in the file's
    order. A file of another shape is an error naming it, never a table with holes."""
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or tuple(data.get("profiles", ())) != PROFILES:
        raise ValueError("%s: the profiles are not %s" % (path, list(PROFILES)))
    rows = data.get("limits")
    if not isinstance(rows, list) or not rows:
        raise ValueError("%s: \"limits\" is not a list of limits" % path)
    table = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("name"), str) or not row["name"]:
            raise ValueError("%s: a limit without a name" % path)
        name = row["name"]
        if name in table:
            raise ValueError("%s: %s is listed twice" % (path, name))
        for key in ("constant", "what"):
            if not isinstance(row.get(key), str):
                raise ValueError("%s: %s has no \"%s\"" % (path, name, key))
        values = {profile: _whole(path, row.get(profile), "%s %s" % (name, profile)) for profile in PROFILES}
        if values["port"] < values["retail"]:
            raise ValueError("%s: %s is lower in port than in retail" % (path, name))
        table[name] = {"constant": row["constant"], "what": row["what"], **values}
    return table


def table():
    if "table" not in _loaded:
        _loaded["table"] = load()
    return _loaded["table"]


def names():
    return list(table())


def value(name, profile):
    """The limit's value in the profile; an unknown limit or profile is an error."""
    if profile not in PROFILES:
        raise ValueError("no limits profile %s; the profiles are retail and port" % profile)
    found = table().get(name)
    if found is None:
        raise KeyError("no limit %s in %s" % (name, PATH))
    return found[profile]


def placements(map_name, profile):
    """The placements a map of this name holds: dungeons (d*) have their own table."""
    return value("dungeon_placements" if map_name.startswith("d") else "town_placements", profile)


def describe(profile):
    return DESCRIPTIONS[profile]


def profile(context=None):
    """The preference's profile; retail when the add-on's preferences are not registered (a test
    outside Blender) or hold something else."""
    try:
        from . import prefs

        found = prefs.get(context).limits_profile
    except (ImportError, AttributeError, KeyError):
        return DEFAULT
    return found if found in PROFILES else DEFAULT
