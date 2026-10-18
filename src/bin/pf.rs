//! pf — command line front-end for PatternForge.
//!   pf call                      read one JSON request from stdin, print the JSON response
//!   pf demo <outdir>             write sample patterns (JSON, SVG, DXF) and drape fixtures
//!   pf draft <garment> <outdir> [measurements.csv|json]
use patternforge::api;
use patternforge::json::Json;
use std::io::Read;

fn die(msg: &str) -> ! {
    eprintln!("error: {}", msg);
    std::process::exit(1);
}

fn write(path: &std::path::Path, s: &str) {
    std::fs::write(path, s).unwrap_or_else(|e| die(&format!("cannot write {}: {}", path.display(), e)));
}

fn field(j: &Json, k: &str) -> Json { j.get(k).cloned().unwrap_or(Json::Null) }

fn run(garment: &str, out: &std::path::Path, meas: Option<Json>) {
    std::fs::create_dir_all(out).unwrap_or_else(|e| die(&e.to_string()));
    let mut req = Json::obj().set("op", Json::str("draft")).set("garment", Json::str(garment));
    if let Some(m) = &meas { req = req.set("measurements", m.clone()); }
    let d = Json::parse(&api::call(&req.to_string())).unwrap();
    if d.get("ok").and_then(|v| v.as_bool()) != Some(true) { die(d.get("error").and_then(|v| v.as_str()).unwrap_or("draft failed")); }
    let pattern = field(&d, "pattern");
    write(&out.join(format!("{}.pattern.json", garment)), &d.to_string());
    let svg = Json::parse(&api::call(&Json::obj().set("op", Json::str("export_svg")).set("pattern", pattern.clone()).to_string())).unwrap();
    write(&out.join(format!("{}.svg", garment)), svg.get("svg").and_then(|v| v.as_str()).unwrap_or(""));
    let dxf = Json::parse(&api::call(&Json::obj().set("op", Json::str("export_dxf")).set("pattern", pattern.clone()).set("style", Json::str(&format!("{}-block", garment))).to_string())).unwrap();
    write(&out.join(format!("{}.dxf", garment)), dxf.get("dxf").and_then(|v| v.as_str()).unwrap_or(""));
    let mut dr = Json::obj().set("op", Json::str("drape")).set("pattern", pattern);
    if let Some(m) = meas { dr = dr.set("measurements", m); }
    write(&out.join(format!("{}.drape.json", garment)), &api::call(&dr.to_string()));
    println!("wrote {}/{}.{{pattern.json,svg,dxf,drape.json}}", out.display(), garment);
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    match args.get(1).map(|s| s.as_str()) {
        Some("call") => {
            let mut s = String::new();
            std::io::stdin().read_to_string(&mut s).unwrap_or_else(|e| die(&e.to_string()));
            println!("{}", api::call(&s));
        }
        Some("demo") => {
            let out = std::path::PathBuf::from(args.get(2).map(|s| s.as_str()).unwrap_or("demo-out"));
            for g in ["bodice", "skirt", "trousers"] { run(g, &out, None); }
        }
        Some("draft") => {
            let (Some(g), Some(o)) = (args.get(2), args.get(3)) else { die("usage: pf draft <bodice|skirt|trousers> <outdir> [measurements file]") };
            let meas = args.get(4).map(|f| {
                let t = std::fs::read_to_string(f).unwrap_or_else(|e| die(&format!("cannot read {}: {}", f, e)));
                match api::parse_measurements_text(&t, false, &patternforge::model::Measurements::default()) { Ok((m, w)) => { for x in w { eprintln!("warning: {}", x); } m.to_json() } Err(e) => die(&e) }
            });
            run(g, std::path::Path::new(o), meas);
        }
        _ => {
            eprintln!("usage: pf call | pf demo <outdir> | pf draft <garment> <outdir> [measurements]");
            std::process::exit(2);
        }
    }
}
