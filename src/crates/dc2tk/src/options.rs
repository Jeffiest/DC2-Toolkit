//! The options commands share: the native tables (NativesArg), the definition sets, SDK headers
//! and native tables most script commands take (Common), the mods folder (ModsDir) and the
//! capacity limits content is checked against (LimitsArg); and what compiling needs, loaded once
//! from Common (Tools).

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use anyhow::Result;
use clap::Args;
use indexmap::IndexMap;

use dc2tk_assets::limits::{Limits, Profile};
use dc2tk_script::compile::Toolchain;
use dc2tk_script::definitions::{self, Definitions};
use dc2tk_script::natives::{self, Table};
use dc2tk_script::{mods, sdk};

use crate::files;

/// Where the native tables are.
#[derive(Args, Clone, Default)]
pub struct NativesArg {
    /// Directory of native table JSON files; definitions/natives when omitted.
    #[arg(long, value_name = "DIR")]
    pub natives: Option<PathBuf>,
}

impl NativesArg {
    pub fn dir(&self) -> PathBuf {
        self.natives.clone().unwrap_or_else(files::natives_dir)
    }

    pub fn tables(&self) -> Result<BTreeMap<String, Table>> {
        Ok(natives::load(&self.dir())?)
    }
}

/// The options most script commands share.
#[derive(Args, Clone, Default)]
pub struct Common {
    #[command(flatten)]
    pub natives: NativesArg,
    /// Directory of SDK headers; sdk/ when omitted.
    #[arg(long, value_name = "DIR")]
    pub sdk: Option<PathBuf>,
    /// Definition set to apply; repeat to layer sets (later ones win); the shipped PAL set when
    /// omitted.
    #[arg(long, value_name = "DIR")]
    pub defs: Vec<PathBuf>,
    /// Apply no definition set, not even the shipped one.
    #[arg(long, conflicts_with = "defs")]
    pub no_defs: bool,
}

impl Common {
    pub fn tables(&self) -> Result<BTreeMap<String, Table>> {
        self.natives.tables()
    }

    /// The definition sets to apply, in order: none with --no-defs, the shipped PAL set when none
    /// are given.
    pub fn def_sets(&self) -> Vec<PathBuf> {
        if self.no_defs {
            Vec::new()
        } else if self.defs.is_empty() {
            vec![files::default_defs()]
        } else {
            self.defs.clone()
        }
    }

    pub fn table_rules(&self) -> Result<Vec<(String, String)>> {
        Ok(definitions::table_rules(&self.def_sets())?)
    }

    pub fn sdk_dir(&self) -> PathBuf {
        self.sdk.clone().unwrap_or_else(|| files::root().join("sdk"))
    }

    pub fn definitions(&self) -> Result<Definitions> {
        let sets = self.def_sets();
        if sets.is_empty() {
            return Ok(Definitions::empty());
        }
        Ok(definitions::load(&sets)?)
    }

    /// The definitions, their headers with the SDK's and the native tables, loaded once.
    pub fn tools(&self) -> Result<Tools> {
        let defs = self.definitions()?;
        let sdk_dir = self.sdk_dir();
        let headers = sdk::header_texts(&defs, &sdk_dir)?;
        Ok(Tools { defs, headers, tables: self.tables()?, sdk_dir })
    }
}

/// What compiling needs, loaded from Common: the definitions, the headers (the SDK's and the
/// definition sets'), the native tables and the SDK folder. toolchain() lends them to the
/// compiler.
pub struct Tools {
    pub defs: Definitions,
    pub headers: IndexMap<String, String>,
    pub tables: BTreeMap<String, Table>,
    pub sdk_dir: PathBuf,
}

impl Tools {
    pub fn toolchain(&self) -> Toolchain<'_> {
        Toolchain { headers: &self.headers, rules: &self.defs.tables, tables: &self.tables, sdk_dir: &self.sdk_dir }
    }
}

/// The capacity limits content is checked against (docs/guide/limits.md).
#[derive(Args, Clone, Debug, Default)]
pub struct LimitsArg {
    /// The limits the content is checked against: retail (the PS2 game's) or port (the raised
    /// engine's; content that needs them runs only on that engine). dc2tk limits lists both.
    #[arg(long, value_name = "PROFILE", default_value = "retail")]
    pub limits: Profile,
}

impl LimitsArg {
    pub fn of(profile: Profile) -> LimitsArg {
        LimitsArg { limits: profile }
    }

    pub fn limits(&self) -> &'static Limits {
        self.limits.limits()
    }
}

/// The folder that holds the mods.
#[derive(Args, Clone)]
pub struct ModsDir {
    /// The folder that holds the mods.
    #[arg(long, value_name = "DIR", default_value = "mods")]
    pub mods: PathBuf,
}

impl ModsDir {
    /// The folder of the mod of that name.
    pub fn folder(&self, name: &str) -> Result<PathBuf> {
        Ok(mods::folder(&self.mods, name)?)
    }

    pub fn path(&self) -> &Path {
        &self.mods
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use clap::Parser;

    #[derive(Parser, Debug)]
    struct Line {
        #[command(flatten)]
        limits: LimitsArg,
    }

    #[test]
    fn the_limits_option_defaults_to_retail_and_names_the_profiles_when_wrong() {
        assert_eq!(Line::try_parse_from(["x"]).unwrap().limits.limits, Profile::Retail);
        assert_eq!(
            Line::try_parse_from(["x", "--limits", "port"]).unwrap().limits.limits(),
            &dc2tk_assets::limits::PORT
        );
        assert_eq!(
            Line::try_parse_from(["x", "--limits", "retail"]).unwrap().limits.limits(),
            &dc2tk_assets::limits::RETAIL
        );
        let error = Line::try_parse_from(["x", "--limits", "ps2"]).unwrap_err().to_string();
        assert!(error.contains("ps2") && error.contains("retail and port"), "{error}");
        assert_eq!(LimitsArg::of(Profile::Port).limits.name(), "port");
        assert_eq!(LimitsArg::default().limits, Profile::Retail);
    }
}
