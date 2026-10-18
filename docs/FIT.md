# Closed-loop fit (src/fit.rs)

## api.rs wiring snippet

Add to `src/lib.rs`:
```rust
pub mod pom;
pub mod fit;
```
Add to the op dispatch in `src/api.rs` (next to `"draft_spec"`, line ~165):
```rust
"fit_spec" => {
    let kind = j.get("garment").and_then(|v| v.as_str()).ok_or("missing garment")?;
    let sheet = j.get("spec").ok_or("missing spec")?;
    let size = j.get("size").and_then(|v| v.as_str());
    crate::fit::fit_json(kind, sheet, size, j.get("factors"))
}
```
Request: `{op:"fit_spec", garment:"pant", spec:<SpecSheet json>, size?:"M", factors?:{shrink_x,shrink_y,stretch_x,stretch_y}}`.
Response: same shape as `draft_spec` (`pattern,size,base_size,sizes[{label,step,measurements,pattern,table}],warnings`)
plus `fit[]`, `max_abs_error`, `converged`, `grading`.

## What it does

`fit_pant(spec, opts, factors)` / `fit_shirt(...)` draft, measure (`pom::measure_*`), and
adjust the drafter's input fields until each non-input POM is within 0.01 cm (hard gate
0.02 cm). The solver is a damped Newton iteration on the full Jacobian (finite differences,
refreshed by Broyden rank-1 updates, halving line search), so the couplings (rise vs inseam, seat vs thigh,
thigh vs knee, pocket length vs bag depth) are solved together. Cap 60 iterations, no randomness.

Driven pant fields: half_seat, thigh, front_rise, back_rise, knee, leg_opening, `opts.pant_hem`,
inseam, waistband_width, pocket_opening_waist/length, pocket_bag_depth. Not driven (input_only
rows, spec value passed through): 20125, 20245, 20305-A/B, 30845 and shirt `armhole`.

Bounds follow `validate()`. An infeasible spec returns `Err` naming the field
(e.g. `infeasible pant spec: pant spec 'leg_opening' = 5 outside the supported range 12..60 cm`).
If the solver cannot reach 0.02 cm it returns `converged=false` with per-POM residual warnings.

Tolerance: `fit_pant_sheet`/`fit_json` read the sheet's +/- column per row. `tol = 0` is honoured exactly
(`ok` requires |error| <= 0.001 cm solver noise floor, not a widened band).

## Grading checks (G36/G37)

`grading_report(sheet)` flags per POM: non-monotonic grading (increments change sign) and any
single-step jump over 20 % of the value. No false positives on `spec_graded.tsv` (tested).
`extrapolate_size(sheet,label,from,steps)` wraps `SpecSheet::extrapolate`; callers must label the result
as extrapolated (linear using the first/last real increment).

## Fabric factors (#11 scaffolding)

`FabricFactors{shrink_x,shrink_y,stretch_x,stretch_y}` default 1.0. Convention: finished = cut x shrink x stretch.
`apply_factors(spec, axis, f) = spec / (shrink*stretch)` so the pattern is cut larger when fabric shrinks.
Width POMs use X, length/curved POMs use Y. Applied to targets inside `fit_*`; the report's `target`
is the compensated (cut) value. Rows are not yet split into "finished spec" vs "cut target".

## Honesty: guaranteed vs not

- Guaranteed (tested, all 6 sizes of the real sheet): every driven POM equals the spec within 0.01 cm
  **by the definitions in POM-DEFINITIONS.md**, and `check_pattern` still passes.
- Not guaranteed: that Optitex measures the same. Open definitions (horizontal vs perpendicular width,
  knee reference, seat line, the 22145 calibration) are listed under CONFIRM IN OPTITEX.
- The drafter has structural limits: seat/thigh/knee are coupled through the drafter's grading
  coefficients, and the fit moves the drafter inputs away from the spec values to hit the measured
  ones (e.g. S: half_seat input 50.98 for a 52.0 result). The pattern shape is a parametric
  re-creation, not the factory's curves.
- Fabric shrink/stretch factors are scaffolding; nothing here measures real fabric.
