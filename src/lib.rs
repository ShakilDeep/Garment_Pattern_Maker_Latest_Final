//! PatternForge core: parametric garment pattern drafting, grading, editing,
//! DXF-AAMA/SVG export and a position-based cloth drape simulation.
//! Zero third-party dependencies so it builds anywhere (including wasm32).
pub mod api;
pub mod calib;
pub mod draft;
pub mod edit;
pub mod export;
pub mod geom;
pub mod grade;
pub mod json;
pub mod mesh;
pub mod pds_api;
pub mod pds_bin;
pub mod pds_import;
pub mod spec;
pub mod marker;
pub mod garments;
pub mod model;
pub mod sim;
pub mod fit;
pub mod pom;
pub mod validate;
pub mod wasm;
pub mod xlsx_read;
