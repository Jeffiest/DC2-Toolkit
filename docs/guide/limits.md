# Capacity Limits

The game holds its content in arrays of fixed size: a map's placement table, a floor's list of
monsters, the item records, the townspeople, the Georama parts a town lists. `dc2tk` checks the
content a mod adds against those sizes and refuses what would not fit, naming the limit and both
numbers. The sizes come in two **profiles**:

| Profile | Limits | Runs on |
| --- | --- | --- |
| `retail` (the default) | The PS2 game's. | The PS2 (PCSX2) and the native port alike. |
| `port` | The raised native engine's (ChronicleTwo's `port/include/capacity.hpp`). | Only the raised engine. A PS2 build of content over a retail limit is refused or misbehaves. |

The rule: **content checked with the `port` profile runs only on the raised engine.** A mod that
needs it says so in its description, and a build for the PS2 checks it with `retail`.

Nothing about `retail` changed when profiles arrived: an unedited disc builds to the retail bytes,
and every check applies the number it always did. The only addition is one line naming the profile
at the top of the report.

## Choosing a profile

`--limits retail|port` (default `retail`) goes on the commands that check content:

```
dc2tk build extracted/scripts dc2.iso --dry-run --mod local.mymod --limits port
dc2tk mod check extracted/scripts local.mymod --disc dc2.iso --limits port
dc2tk mod build extracted/scripts dc2.iso local.mymod --limits port
dc2tk mod watch extracted/scripts dc2.iso local.mymod --limits port
dc2tk play --native dc2.iso --set my-game.json --limits port
```

`mod check` and `build --dry-run` print the profile first:

```
limits port (the raised engine's limits; the content runs only on it)
```

and the memory report (`memory:` lines, [Memory Limits](memory.md)) begins with the same line. A
limit exceeded is an error that names it and both numbers, for instance:

```
error: map m01: 330 placements, more than the 320 its placement table holds (SetPlacePartsBuff); the rest are not placed
d01f01 room 64: the rooms are 0 to 63
3 new items make 435; the game holds 432 items (local_com_itemdata), 0 more than the disc's
```

In the Blender add-on the profile is the preference **Limits** (Edit, Preferences, Add-ons, "DC2
Maps (dc2tk)"): **Validate Map** and the **Budgets** panel check placements against it, and
**Preview Changes**, **Build ISO** and **Test Here** pass it to `dc2tk build`. The add-on reads the
numbers from `dc2tk_maps/limits.json`, which `dc2tk limits --json` writes and a test of the
toolkit keeps equal to its own table.

## The limits

`dc2tk limits` prints this table. A limit the engine does not raise has the same number in both
columns: the port keeps its placement table at the retail size, reads a chest table of retail
shape, and reads at most 64 arguments of a statement, so the toolkit does too.

| Limit | Constant | What it counts | Retail | Port |
| --- | --- | --- | --- | --- |
| `town_placements` | `MAX_PLACEMENTS (SetPlacePartsBuff)` | placements in a town or interior map | 320 | 320 |
| `dungeon_placements` | `MAX_PLACEMENTS (LoadDungeonMapFile)` | placements in a dungeon map | 400 | 400 |
| `floor_monsters` | `MONSTER_LOCATE_MAX` | monsters in one floor's placement list | 32 | 128 |
| `chest_groups` | `TRESURE_BOX_FLOOR_INFO::group` | item groups in one dungeon's chest table | 64 | 64 |
| `chest_group_items` | `TRESURE_BOX_GROUP::item` | items one chest group gives | 96 | 96 |
| `chest_floor_groups` | `TRESURE_BOX_FLOOR::group_id` | groups one floor's chests draw from | 64 | 64 |
| `georama_parts` | `GEORAMA_PARTS_LIST_MAX` | Georama parts a town's editor lists | 384 | 1024 |
| `georama_placed` | `EDIT_DATA_PARTS_MAX (CEditMap::CreateTable)` | Georama parts placed in a town | 256 | 1024 |
| `townspeople` | `NpcBaseData` | townspeople records | 180 | 512 |
| `common_items` | `ITEM_COMMON_DATA_MAX` | item records | 432 | 1024 |
| `item_numbers` | `ITEM_NO_MAX - 1` | the highest item number | 511 | 2047 |
| `weapon_records` | `WEAPON_DATA_MAX (WEPNUM)` | weapon records | 116 | 512 |
| `item_records` | `ITEM_DATA_MAX (ITEMINIT)` | usable item records | 162 | 512 |
| `shop_goods` | `SHOP_ITEM_MAX` | goods one shop lists | 64 | 256 |
| `statement_args` | `SPI_STACK_SIZE` | arguments one cfg statement holds | 64 | 64 |
| `layout_rooms` | `AUTOMAP_ROOM_MAX` | room layouts one floor's generator holds | 64 | 160 |
| `layout_cells` | `CAutoMapParts` | cells of the generator's grid | 900 | 3600 |

Notes:

- A shop's goods are one `SHOP` statement whose first argument is the shop id, so a shop lists at
  most 63 goods in either profile, whatever `SHOP_ITEM_MAX` is.
- A floor's monsters are `FL` statements of pairs, and the engine reads every statement's pairs,
  so a `port` list past 32 is written as more `FL` statements of 32 pairs after the last.
  Retail's lists keep their lines as they were.
- The other item families (attachments 38, ridepod parts 68, fish 20, clothing 40) keep their
  retail sizes in the engine and so in both profiles.
- `georama_placed` counts the parts a town's data places at the start (`data:georama`, the
  `starting_parts`). The raised engine holds placed parts in a layout that grows up to
  `kPortEditSlotCeiling` (`port/include/stubs/editmap.hpp`, 32767) with no array in
  `capacity.hpp`, and 1024 is the plan's target for it.
- Limits the toolkit does not enforce (monsters out at once, treasure chests on a floor, save
  records, inventory places) are the engine's alone; DC2_PLAN.md "Where the limits are" lists them
  all.

## Keeping the two sides equal

The table lives in one place, `dc2tk-assets/src/limits.rs`, and every check reads its number from
it. Tests hold the retail column to the game's values, the Blender add-on's `limits.json` to the
table, and, with `DC2_ENGINE` set to a ChronicleTwo checkout, the port column to the constants of
`port/include/capacity.hpp`:

```
DC2_ENGINE=../ChronicleTwo cargo test --release -p dc2tk-assets limits:: -- --include-ignored
```

When the engine raises a limit, the change is one number in `limits.rs`, `dc2tk limits --json >
blender-plugin/dc2tk_maps/limits.json`, and this page.
