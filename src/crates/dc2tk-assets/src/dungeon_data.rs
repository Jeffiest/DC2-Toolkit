//! Dungeon floors (docs/game/data.md, "Floor medals" and "Monsters"): the medal conditions of
//! `menu/dngmap/dflr<dungeon>.cfg` (`data:medals`) and the monsters of
//! `dungeon/cfg_file/mos_place<dungeon>.cfg` (`data:floors`), as [`data_table`] tables named by
//! dungeon and floor.
//!
//! CDngFloorManager::LoadDataTable (dngfloor.cpp) reads `RF_INFO floor, geostone, fast_time,
//! fishing, fishing_record, seal, spheda, [item, count] × 3;` (_ROOM_FLOOR_INFO, into
//! DNGMAP_ROOM_INFO: s8, s32, s8, s16, s8, s8, then s16 items and s8 counts) and `RF_INFO2 floor,
//! practice_type, practice_param;` (_ROOM_FLOOR_INFO2: s8, s32). LoadMonsterFile (dng_event.cpp)
//! runs `mos_place` over `FLS floor, count;` (the count is read and dropped), `FL monster, param,
//! ...;` (pairs appended to CMonsterLocateInfo's 32 slots, unchecked) and `FLE;`, for the floor
//! being entered; a later block for one floor starts it again. The param becomes the placed
//! monster's `locate_param`, the talk number (-1: it cannot be talked to; CheckMonsterTolk), shown
//! as `talk`.

use serde_json::Value;

use crate::cfg_text::Arg;
use crate::data_table::{self, Place, Record, Table, S16, S32, S8};
use crate::limits::Limits;
use crate::Result;

pub const DUNGEONS: usize = 7;

pub fn medal_paths() -> Vec<String> {
    (0..DUNGEONS).map(|dungeon| format!("menu/dngmap/dflr{dungeon}.cfg")).collect()
}

pub fn floor_paths() -> Vec<String> {
    (0..DUNGEONS).map(|dungeon| format!("dungeon/cfg_file/mos_place{dungeon}.cfg")).collect()
}

fn keys(dungeon: usize, floor: i32) -> Record {
    Record::new(&[("dungeon", Value::from(dungeon)), ("floor", Value::from(floor))])
}

/// The floor medals: one record per RF_INFO, with its RF_INFO2.
pub fn medals(files: &[Vec<u8>]) -> Result<Table> {
    let scripts = data_table::parse_all(&medal_paths(), files)?;
    let mut records = Vec::new();
    for (dungeon, script) in scripts.iter().enumerate() {
        let practice = data_table::by_first(script, "RF_INFO2");
        for (floor, places) in data_table::by_first(script, "RF_INFO") {
            let at = [(dungeon, *places.last().unwrap())];
            if script.statements[at[0].1].args().len() < 13 {
                continue;
            }
            let mut record = keys(dungeon, floor);
            record
                .arg("geostone", S8, &at, 1)
                .arg("fast_time", S32, &at, 2)
                .arg("fishing", S8, &at, 3)
                .arg("fishing_record", S16, &at, 4)
                .arg("seal", S8, &at, 5)
                .arg("spheda", S8, &at, 6);
            record.field(
                "spheda_prizes",
                Place::List {
                    at: at.to_vec(),
                    arg: 7,
                    tail: 0,
                    entry: vec![("item", S16), ("count", S8)],
                    count: (3, 3),
                },
            );
            if let Some(places) = practice.get(&floor) {
                let at = [(dungeon, *places.last().unwrap())];
                if script.statements[at[0].1].args().len() >= 3 {
                    record.arg("practice_type", S8, &at, 1).arg("practice_param", S32, &at, 2);
                }
            }
            records.push(record);
        }
    }
    let mut table = Table::new("a medal table", scripts, Vec::new());
    table.section("floors", &["dungeon", "floor"], records);
    Ok(table)
}

/// The monsters of each floor: the FL statements of its last FLS .. FLE block, at most the
/// profile's `floor_monsters` (MONSTER_LOCATE_MAX). The engine reads every FL statement's pairs,
/// and a statement holds `statement_args` arguments (SPI_STACK_SIZE), so where the profile's
/// list outgrows one statement the list is written as many statements of as many pairs as one
/// holds, added after the last; retail's 32 pairs fit one statement, and its lists keep their
/// lines as they were.
pub fn floors(files: &[Vec<u8>], limits: &Limits) -> Result<Table> {
    let pairs_a_statement = limits.statement_args / 2;
    let spread = limits.floor_monsters > pairs_a_statement;
    let scripts = data_table::parse_all(&floor_paths(), files)?;
    let mut blocks: std::collections::BTreeMap<(usize, i32), Vec<(usize, usize)>> = Default::default();
    for (dungeon, script) in scripts.iter().enumerate() {
        let mut current: Option<i32> = None;
        for (at, statement) in script.statements.iter().enumerate() {
            match statement.tag.as_str() {
                "FLS" => {
                    let floor = statement.values().first().map_or(0, Arg::int);
                    blocks.insert((dungeon, floor), Vec::new());
                    current = Some(floor);
                }
                "FL" => {
                    if let Some(floor) = current {
                        blocks.entry((dungeon, floor)).or_default().push((dungeon, at));
                    }
                }
                "FLE" => current = None,
                _ => {}
            }
        }
    }
    let mut records = Vec::new();
    for ((dungeon, floor), at) in blocks {
        let mut record = keys(dungeon, floor);
        record.field(
            "monsters",
            Place::Lines {
                copies: vec![at],
                entry: vec![("monster", S16), ("talk", S16)],
                count: (0, limits.floor_monsters),
                per_line: if spread { pairs_a_statement } else { 0 },
                grow: spread,
            },
        );
        records.push(record);
    }
    let mut table = Table::new_with("a floor table", scripts, Vec::new(), limits);
    table.section("floors", &["dungeon", "floor"], records);
    Ok(table)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn corpus(paths: &[String]) -> Vec<Vec<u8>> {
        let corpus = dc2tk_disc::samples::corpus();
        paths.iter().map(|path| std::fs::read(corpus.join(path)).unwrap()).collect()
    }

    #[test]
    fn floor_lists_fill_their_lines() {
        let files: Vec<Vec<u8>> = (0..DUNGEONS)
            .map(|dungeon| {
                let text = if dungeon == 0 { "FLS 1,3;\r\nFL 0,0,0,1;\r\nFL 8,800;\r\nFLE;\r\n" } else { "" };
                text.as_bytes().to_vec()
            })
            .collect();
        let table = floors(&files, &crate::limits::RETAIL).unwrap();
        assert_eq!(table.to_json()["floors"][0]["monsters"][2], json!({"monster": 8, "talk": 800}));
        let edit = json!({"floors": [{"dungeon": 0, "floor": 1, "monsters": [{"monster": 4, "talk": 400}]}]});
        let written = table.apply(&table.changes(&edit, "m").unwrap().0).unwrap();
        assert_eq!(written[0], b"FLS 1,3;\r\nFL 4,400;\r\nFL;\r\nFLE;\r\n");
    }

    /// The medal and floor files of an extracted disc (DC2TK_CORPUS) read, write back unchanged,
    /// and their JSON changes nothing.
    #[test]
    #[ignore = "needs DC2TK_CORPUS"]
    fn corpus_floors_and_medals_round_trip() {
        let (medal_files, floor_files) = (corpus(&medal_paths()), corpus(&floor_paths()));
        let medals = medals(&medal_files).unwrap();
        assert_eq!(medals.write(), medal_files);
        assert_eq!(medals.check(), Vec::<String>::new());
        let floors = floors(&floor_files, &crate::limits::RETAIL).unwrap();
        assert_eq!(floors.write(), floor_files);
        assert_eq!(floors.check(), Vec::<String>::new());
        eprintln!(
            "{} floor medals and {} floors' monsters round-trip",
            medals.sections[0].records.len(),
            floors.sections[0].records.len()
        );
    }

    #[test]
    fn a_floors_monsters_are_bounded_by_the_profile() {
        let files: Vec<Vec<u8>> = (0..DUNGEONS)
            .map(|dungeon| if dungeon == 0 { b"FLS 1,3;\r\nFL 0,0;\r\nFLE;\r\n".to_vec() } else { Vec::new() })
            .collect();
        for profile in crate::limits::Profile::ALL {
            let limits = profile.limits();
            let table = floors(&files, limits).unwrap();
            let monsters = |count: usize| {
                let list: Vec<_> = (0..count).map(|i| json!({"monster": i as i64 % 100, "talk": 0})).collect();
                json!({"floors": [{"dungeon": 0, "floor": 1, "monsters": list}]})
            };
            let written = |edit| table.changes(&edit, "m").and_then(|changed| table.apply(&changed.0));
            written(monsters(limits.floor_monsters)).unwrap_or_else(|error| panic!("{profile}: {error}"));
            let error = written(monsters(limits.floor_monsters + 1)).unwrap_err().to_string();
            assert!(error.contains(&format!("0 to {}", limits.floor_monsters)), "{profile}: {error}");
        }
    }
}
