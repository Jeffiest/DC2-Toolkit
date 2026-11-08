//! The capacity limits the content checks enforce, in two profiles. `retail` holds the values of
//! the PS2 game, the ones every check applied before profiles existed, and is the default: an
//! unedited build checked with it is the retail disc. `port` holds the values of the raised
//! engine, ChronicleTwo's `port/include/capacity.hpp` (DC2_PLAN.md "Where the limits are"), and
//! content that needs it runs only on that engine. Where that header keeps retail, or names no
//! constant and the engine still reads the retail number (the placement table, mapjump.cpp
//! `0x140` and LoadDungeonMapFile 400; the chest table's arrays, dng_event.hpp; SPI_STACK_SIZE),
//! the port profile keeps retail too, so the two cannot disagree. Each check reads its limit from
//! a [`Limits`], and [`TABLE`] lists every limit with both values for `dc2tk limits` and the
//! Blender add-on's `limits.json`, which a test keeps equal to it. With `DC2_ENGINE` set to a
//! ChronicleTwo checkout, a test compares the port column with the header's constants.

use std::fmt;
use std::str::FromStr;

use serde_json::{json, Value};

/// Which engine the content is checked for.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Hash)]
pub enum Profile {
    #[default]
    Retail,
    Port,
}

impl Profile {
    pub const ALL: [Profile; 2] = [Profile::Retail, Profile::Port];

    pub fn name(self) -> &'static str {
        match self {
            Profile::Retail => "retail",
            Profile::Port => "port",
        }
    }

    pub fn limits(self) -> &'static Limits {
        match self {
            Profile::Retail => &RETAIL,
            Profile::Port => &PORT,
        }
    }
}

impl FromStr for Profile {
    type Err = String;

    fn from_str(text: &str) -> Result<Profile, String> {
        Profile::ALL
            .into_iter()
            .find(|profile| profile.name() == text)
            .ok_or_else(|| format!("no limits profile {text}; the profiles are retail and port"))
    }
}

impl fmt::Display for Profile {
    fn fmt(&self, out: &mut fmt::Formatter<'_>) -> fmt::Result {
        out.write_str(self.name())
    }
}

/// The limits of one profile.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Limits {
    pub profile: Profile,
    /// Placements a town or interior map's placement table holds (SetPlacePartsBuff, 0x140).
    pub town_placements: usize,
    /// Placements a dungeon map's placement table holds (LoadDungeonMapFile).
    pub dungeon_placements: usize,
    /// MONSTER_LOCATE_MAX: the monsters one floor's placement list holds.
    pub floor_monsters: usize,
    /// Item groups one dungeon's chest table holds (TRESURE_BOX_FLOOR_INFO::group).
    pub chest_groups: usize,
    /// Items one chest group gives (TRESURE_BOX_GROUP::item).
    pub chest_group_items: usize,
    /// Groups one floor's chests draw from (TRESURE_BOX_FLOOR::group_id).
    pub chest_floor_groups: usize,
    /// GEORAMA_PARTS_LIST_MAX: the parts a town's editor lists.
    pub georama_parts: usize,
    /// The parts placed in a town (CEditMap::CreateTable).
    pub georama_placed: usize,
    /// NpcBaseData: the townspeople records.
    pub townspeople: usize,
    /// ITEM_COMMON_DATA_MAX: the item records (local_com_itemdata).
    pub common_items: usize,
    /// The highest item number (ITEM_NO_MAX less one; local_itemdatano_converttable).
    pub item_numbers: i64,
    /// WEAPON_DATA_MAX: the weapon records (local_weapondata, WEPNUM).
    pub weapon_records: usize,
    /// ITEM_DATA_MAX: the usable item records (local_itemdata, ITEMINIT).
    pub item_records: usize,
    /// SHOP_ITEM_MAX: the goods one shop lists.
    pub shop_goods: usize,
    /// SPI_STACK_SIZE: the arguments one cfg statement holds.
    pub statement_args: usize,
    /// AUTOMAP_ROOM_MAX: the room layouts one floor's generator holds.
    pub layout_rooms: usize,
    /// CAutoMapParts: the cells of the generator's grid.
    pub layout_cells: usize,
}

pub const RETAIL: Limits = Limits {
    profile: Profile::Retail,
    town_placements: 320,
    dungeon_placements: 400,
    floor_monsters: 32,
    chest_groups: 64,
    chest_group_items: 96,
    chest_floor_groups: 64,
    georama_parts: 0x180,
    georama_placed: 0x100,
    townspeople: 180,
    common_items: 432,
    item_numbers: 0x1FF,
    weapon_records: 116,
    item_records: 162,
    shop_goods: 64,
    statement_args: 64,
    layout_rooms: 64,
    layout_cells: 900,
};

pub const PORT: Limits = Limits {
    profile: Profile::Port,
    town_placements: RETAIL.town_placements,
    dungeon_placements: RETAIL.dungeon_placements,
    floor_monsters: 128,
    chest_groups: RETAIL.chest_groups,
    chest_group_items: RETAIL.chest_group_items,
    chest_floor_groups: RETAIL.chest_floor_groups,
    georama_parts: 1024,
    georama_placed: 1024,
    townspeople: 512,
    common_items: 1024,
    item_numbers: 2048 - 1,
    weapon_records: 512,
    item_records: 512,
    shop_goods: 256,
    statement_args: RETAIL.statement_args,
    layout_rooms: 160,
    layout_cells: 60 * 60,
};

impl Limits {
    /// The goods one SHOP statement can list: the shop's goods, in a statement whose first
    /// argument is the shop id.
    pub fn shop_goods_a_statement(&self) -> usize {
        self.shop_goods.min(self.statement_args - 1)
    }

    /// The placements a map of a kind holds.
    pub fn placements(&self, dungeon: bool) -> usize {
        if dungeon {
            self.dungeon_placements
        } else {
            self.town_placements
        }
    }

    /// "retail (the PS2 game's limits)", for reports.
    pub fn describe(&self) -> String {
        match self.profile {
            Profile::Retail => "retail (the PS2 game's limits)".to_string(),
            Profile::Port => "port (the raised engine's limits; the content runs only on it)".to_string(),
        }
    }
}

/// One limit of the table: its name in JSON and `dc2tk limits`, the engine constant it is, what it
/// counts, its value in each profile, and the engine constant that gives the port value: one of
/// `capacity.hpp`, or `<= kPortEditSlotCeiling` (stubs/editmap.hpp) where the engine holds the
/// content in a growing layout and the port value is the plan's target under that ceiling; none
/// where the engine keeps retail and the header names no constant.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Limit {
    pub name: &'static str,
    pub constant: &'static str,
    pub what: &'static str,
    pub retail: u64,
    pub port: u64,
    pub capacity: Option<&'static str>,
}

pub const TABLE: [Limit; 17] = [
    Limit {
        name: "town_placements",
        constant: "MAX_PLACEMENTS (SetPlacePartsBuff)",
        what: "placements in a town or interior map",
        retail: RETAIL.town_placements as u64,
        port: PORT.town_placements as u64,
        capacity: None,
    },
    Limit {
        name: "dungeon_placements",
        constant: "MAX_PLACEMENTS (LoadDungeonMapFile)",
        what: "placements in a dungeon map",
        retail: RETAIL.dungeon_placements as u64,
        port: PORT.dungeon_placements as u64,
        capacity: None,
    },
    Limit {
        name: "floor_monsters",
        constant: "MONSTER_LOCATE_MAX",
        what: "monsters in one floor's placement list",
        retail: RETAIL.floor_monsters as u64,
        port: PORT.floor_monsters as u64,
        capacity: Some("kMonsterLocateEntries"),
    },
    Limit {
        name: "chest_groups",
        constant: "TRESURE_BOX_FLOOR_INFO::group",
        what: "item groups in one dungeon's chest table",
        retail: RETAIL.chest_groups as u64,
        port: PORT.chest_groups as u64,
        capacity: None,
    },
    Limit {
        name: "chest_group_items",
        constant: "TRESURE_BOX_GROUP::item",
        what: "items one chest group gives",
        retail: RETAIL.chest_group_items as u64,
        port: PORT.chest_group_items as u64,
        capacity: None,
    },
    Limit {
        name: "chest_floor_groups",
        constant: "TRESURE_BOX_FLOOR::group_id",
        what: "groups one floor's chests draw from",
        retail: RETAIL.chest_floor_groups as u64,
        port: PORT.chest_floor_groups as u64,
        capacity: None,
    },
    Limit {
        name: "georama_parts",
        constant: "GEORAMA_PARTS_LIST_MAX",
        what: "Georama parts a town's editor lists",
        retail: RETAIL.georama_parts as u64,
        port: PORT.georama_parts as u64,
        capacity: Some("kGeoramaPartsList"),
    },
    Limit {
        name: "georama_placed",
        constant: "EDIT_DATA_PARTS_MAX (CEditMap::CreateTable)",
        what: "Georama parts placed in a town",
        retail: RETAIL.georama_placed as u64,
        port: PORT.georama_placed as u64,
        capacity: Some("<= kPortEditSlotCeiling"),
    },
    Limit {
        name: "townspeople",
        constant: "NpcBaseData",
        what: "townspeople records",
        retail: RETAIL.townspeople as u64,
        port: PORT.townspeople as u64,
        capacity: Some("kNpcRecords"),
    },
    Limit {
        name: "common_items",
        constant: "ITEM_COMMON_DATA_MAX",
        what: "item records",
        retail: RETAIL.common_items as u64,
        port: PORT.common_items as u64,
        capacity: Some("kCommonItems"),
    },
    Limit {
        name: "item_numbers",
        constant: "ITEM_NO_MAX - 1",
        what: "the highest item number",
        retail: RETAIL.item_numbers as u64,
        port: PORT.item_numbers as u64,
        capacity: Some("kItemNumbers - 1"),
    },
    Limit {
        name: "weapon_records",
        constant: "WEAPON_DATA_MAX (WEPNUM)",
        what: "weapon records",
        retail: RETAIL.weapon_records as u64,
        port: PORT.weapon_records as u64,
        capacity: Some("kWeaponRecords"),
    },
    Limit {
        name: "item_records",
        constant: "ITEM_DATA_MAX (ITEMINIT)",
        what: "usable item records",
        retail: RETAIL.item_records as u64,
        port: PORT.item_records as u64,
        capacity: Some("kItemRecords"),
    },
    Limit {
        name: "shop_goods",
        constant: "SHOP_ITEM_MAX",
        what: "goods one shop lists",
        retail: RETAIL.shop_goods as u64,
        port: PORT.shop_goods as u64,
        capacity: Some("kShopGoods"),
    },
    Limit {
        name: "statement_args",
        constant: "SPI_STACK_SIZE",
        what: "arguments one cfg statement holds",
        retail: RETAIL.statement_args as u64,
        port: PORT.statement_args as u64,
        capacity: None,
    },
    Limit {
        name: "layout_rooms",
        constant: "AUTOMAP_ROOM_MAX",
        what: "room layouts one floor's generator holds",
        retail: RETAIL.layout_rooms as u64,
        port: PORT.layout_rooms as u64,
        capacity: Some("kDungeonRooms"),
    },
    Limit {
        name: "layout_cells",
        constant: "CAutoMapParts",
        what: "cells of the generator's grid",
        retail: RETAIL.layout_cells as u64,
        port: PORT.layout_cells as u64,
        capacity: Some("kDungeonGrid * kDungeonGrid"),
    },
];

impl Limit {
    pub fn value(&self, profile: Profile) -> u64 {
        match profile {
            Profile::Retail => self.retail,
            Profile::Port => self.port,
        }
    }
}

/// The table as JSON: the profiles, then each limit with both values.
pub fn to_json() -> Value {
    let profiles: Vec<&str> = Profile::ALL.iter().map(|profile| profile.name()).collect();
    let limits: Vec<Value> = TABLE
        .iter()
        .map(|limit| {
            json!({
                "name": limit.name,
                "constant": limit.constant,
                "what": limit.what,
                "retail": limit.retail,
                "port": limit.port,
            })
        })
        .collect();
    json!({"profiles": profiles, "limits": limits})
}

/// The table as the text `dc2tk limits` prints: a line a limit, both values.
pub fn text() -> String {
    let mut out = String::new();
    let width = TABLE.iter().map(|limit| limit.name.len()).max().unwrap_or(0);
    out.push_str(&format!("{:<width$}  {:>6}  {:>6}  constant\n", "limit", "retail", "port"));
    for limit in &TABLE {
        out.push_str(&format!(
            "{:<width$}  {:>6}  {:>6}  {} ({})\n",
            limit.name, limit.retail, limit.port, limit.constant, limit.what
        ));
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    const ADDON_JSON: &str = include_str!("../../../../blender-plugin/dc2tk_maps/limits.json");
    const GUIDE: &str = include_str!("../../../../docs/guide/limits.md");

    #[test]
    fn profiles_read_from_their_names_and_an_unknown_one_is_an_error() {
        assert_eq!("retail".parse::<Profile>().unwrap(), Profile::Retail);
        assert_eq!("port".parse::<Profile>().unwrap(), Profile::Port);
        assert_eq!(Profile::default(), Profile::Retail);
        let error = "ps2".parse::<Profile>().unwrap_err();
        assert!(error.contains("ps2") && error.contains("retail and port"), "{error}");
        assert_eq!(Profile::Port.to_string(), "port");
        assert_eq!(Profile::Retail.limits(), &RETAIL);
        assert_eq!(Profile::Port.limits().profile, Profile::Port);
        assert!(RETAIL.describe().starts_with("retail (") && PORT.describe().starts_with("port ("));
    }

    #[test]
    fn the_retail_profile_holds_the_games_values() {
        assert_eq!((RETAIL.town_placements, RETAIL.dungeon_placements), (320, 400));
        assert_eq!(RETAIL.floor_monsters, 32);
        assert_eq!((RETAIL.chest_groups, RETAIL.chest_group_items, RETAIL.chest_floor_groups), (64, 96, 64));
        assert_eq!((RETAIL.georama_parts, RETAIL.georama_placed), (0x180, 0x100));
        assert_eq!(RETAIL.townspeople, 180);
        assert_eq!((RETAIL.common_items, RETAIL.item_numbers), (432, 0x1FF));
        assert_eq!((RETAIL.weapon_records, RETAIL.item_records), (116, 162));
        assert_eq!((RETAIL.shop_goods, RETAIL.statement_args, RETAIL.shop_goods_a_statement()), (64, 64, 63));
        assert_eq!((RETAIL.layout_rooms, RETAIL.layout_cells), (64, 900));
        assert_eq!((RETAIL.placements(false), RETAIL.placements(true)), (320, 400));
    }

    #[test]
    fn the_port_profile_holds_the_headers_values_and_retail_where_the_engine_keeps_it() {
        assert_eq!(PORT.floor_monsters, 128);
        assert_eq!(PORT.georama_parts, 1024);
        assert_eq!(PORT.georama_placed, 1024);
        assert_eq!(PORT.townspeople, 512);
        assert_eq!((PORT.common_items, PORT.item_numbers), (1024, 2047));
        assert_eq!((PORT.weapon_records, PORT.item_records), (512, 512));
        assert_eq!(PORT.shop_goods, 256);
        assert_eq!((PORT.layout_rooms, PORT.layout_cells), (160, 3600));
        assert_eq!((PORT.town_placements, PORT.dungeon_placements), (320, 400));
        assert_eq!((PORT.chest_groups, PORT.chest_group_items, PORT.chest_floor_groups), (64, 96, 64));
        assert_eq!(PORT.statement_args, 64);
        assert_eq!(PORT.shop_goods_a_statement(), 63);
        for limit in &TABLE {
            assert!(limit.port >= limit.retail, "{} is lower in port", limit.name);
            assert_eq!(limit.value(Profile::Retail), limit.retail);
            assert_eq!(limit.value(Profile::Port), limit.port);
            assert_eq!(
                limit.capacity.is_none(),
                limit.port == limit.retail,
                "{}: raised only by the header",
                limit.name
            );
        }
    }

    #[test]
    fn the_table_names_each_limit_once_and_covers_every_field() {
        let mut names: Vec<&str> = TABLE.iter().map(|limit| limit.name).collect();
        names.sort_unstable();
        names.dedup();
        assert_eq!(names.len(), TABLE.len());
        let debug = format!("{RETAIL:?}");
        let fields = debug.matches(": ").count() - 1;
        assert_eq!(fields, TABLE.len(), "every field of Limits is a row of TABLE");
        assert!(text().lines().count() == TABLE.len() + 1);
        assert!(text().contains("town_placements"), "{}", text());
    }

    #[test]
    fn the_add_ons_limits_json_is_the_table() {
        let checked_in: Value = serde_json::from_str(ADDON_JSON).unwrap();
        assert_eq!(
            checked_in,
            to_json(),
            "blender-plugin/dc2tk_maps/limits.json differs from limits::TABLE; write it again with dc2tk limits --json"
        );
        assert!(ADDON_JSON.ends_with('\n') && !ADDON_JSON.contains('\r'));
        assert_eq!(ADDON_JSON, format!("{}\n", serde_json::to_string_pretty(&to_json()).unwrap()));
    }

    #[test]
    fn the_guides_table_is_the_table() {
        for limit in &TABLE {
            let row = format!(
                "| `{}` | `{}` | {} | {} | {} |",
                limit.name, limit.constant, limit.what, limit.retail, limit.port
            );
            assert!(GUIDE.contains(&row), "docs/guide/limits.md lacks the row\n{row}");
        }
        let rows = GUIDE.lines().filter(|line| line.starts_with("| `") && line.matches('|').count() == 6).count();
        assert_eq!(rows, TABLE.len(), "docs/guide/limits.md lists a limit the table lacks");
    }

    /// The constant's value in capacity.hpp: `inline constexpr int kName = 160;`, or the product
    /// or difference the table names (`kDungeonGrid * kDungeonGrid`, `kItemNumbers - 1`).
    fn header_value(header: &str, expression: &str) -> u64 {
        let one = |name: &str| -> u64 {
            let needle = format!("constexpr int {name} = ");
            let start = header.find(&needle).unwrap_or_else(|| panic!("capacity.hpp has no {name}")) + needle.len();
            let text = header[start..].split(';').next().unwrap().trim();
            text.parse().unwrap_or_else(|_| panic!("{name} = {text} is not a plain number"))
        };
        if let Some((left, right)) = expression.split_once(" * ") {
            one(left.trim()) * one(right.trim())
        } else if let Some((left, right)) = expression.split_once(" - ") {
            one(left.trim()) - right.trim().parse::<u64>().unwrap()
        } else {
            one(expression)
        }
    }

    /// The port column is the engine's (`DC2_ENGINE`, a ChronicleTwo checkout, holds
    /// port/include/capacity.hpp and stubs/editmap.hpp); a limit the headers do not raise is
    /// retail here too.
    #[test]
    #[ignore = "needs DC2_ENGINE"]
    fn the_port_profile_is_capacity_hpp() {
        let engine = std::env::var("DC2_ENGINE").expect("DC2_ENGINE names a ChronicleTwo checkout");
        let include = std::path::Path::new(&engine).join("port/include");
        let read = |name: &str| {
            std::fs::read_to_string(include.join(name))
                .unwrap_or_else(|error| panic!("{}: {error}", include.join(name).display()))
        };
        let header = format!("{}\n{}", read("capacity.hpp"), read("stubs/editmap.hpp"));
        for limit in &TABLE {
            match limit.capacity {
                Some(expression) if expression.starts_with("<= ") => {
                    let ceiling = header_value(&header, &expression[3..]);
                    assert!(limit.port <= ceiling, "{}: {} is over {expression} ({ceiling})", limit.name, limit.port);
                    assert!(limit.port > limit.retail, "{}: a ceiling bounds a raised value", limit.name);
                }
                Some(expression) => {
                    assert_eq!(limit.port, header_value(&header, expression), "{}: {expression}", limit.name)
                }
                None => assert_eq!(limit.port, limit.retail, "{} is raised without a header constant", limit.name),
            }
        }
    }
}
