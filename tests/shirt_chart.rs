//! Regression: the shirt measurement chart (long-sleeve MAN SHIRT, base L) must parse and fit exactly at every size.
use patternforge::api;
use patternforge::json::Json;

const CHART: &str = include_str!("fixtures/shirt_chart.tsv");

fn q(s: &str) -> String {
    let mut o = String::from("\"");
    for c in s.chars() {
        match c { '"' => o.push_str("\\\""), '\\' => o.push_str("\\\\"), '\n' => o.push_str("\\n"), '\t' => o.push_str("\\t"), '\r' => {}, c => o.push(c) }
    }
    o.push('"');
    o
}

#[test]
fn shirt_chart_parses_and_fits_every_size() {
    let parsed = Json::parse(&api::call(&format!("{{\"op\":\"parse_spec\",\"text\":{}}}", q(CHART)))).unwrap();
    let spec = parsed.get("spec").expect("spec");
    assert_eq!(spec.get("base_size").and_then(|v| v.as_str()), Some("L"));
    let spec_s = spec.to_string();
    for size in ["S", "M", "L", "XL", "XXL", "3XL"] {
        let req = format!("{{\"op\":\"fit_spec\",\"garment\":\"shirt\",\"spec\":{},\"size\":{}}}", spec_s, q(size));
        let r = Json::parse(&api::call(&req)).unwrap();
        assert_eq!(r.get("ok").and_then(|v| v.as_bool()), Some(true), "size {size}: {:?}", r.get("error"));
        let err = r.get("max_abs_error").and_then(|v| v.as_f64()).unwrap();
        assert!(err < 0.05, "size {size}: max error {err}");
        assert_eq!(r.get("converged").and_then(|v| v.as_bool()), Some(true), "size {size}");
    }
}
