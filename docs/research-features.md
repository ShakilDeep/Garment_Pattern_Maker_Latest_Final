# Optitex PDS 2D/3D - feature research

Caveat: help.optitex.com now 302-redirects to a login (my.optitex.com), so detailed docs were NOT readable.
Items marked [S] are backed by a fetched public page; [D] are standard pattern-CAD domain knowledge / Optitex
conventions I could not verify from public docs. Treat [D] as to-be-verified.

Sources:
- https://optitex.com/optitex-o26-release/  (O/26 release notes)
- https://minervapatterns.com/blog/optitex-for-beginners-a-digital-pattern-workflow  (third-party workflow)
- https://optitex.com (home)
- Gated (titles seen in search only): help.optitex.com/1382687/Content/Optitex_3D/3D_Workflow.htm,
  .../Optitex_2D/Update_Notches,_Darts_And_Pleats.htm, .../Optitex_2D/Viewing_Editing_properties.htm

## 1. 2D pattern design (PDS)
- Pieces: closed polylines/curves with points; piece properties dialog (name, fabric, quantity, flips) [S title/D].
- Point/curve editing: move/add/delete points, convert corner<->curve, spline editing, offset/trim/extend [D].
- Notches and drill holes, incl. DXF export of L-notches as true L-shapes (O/26) [S]. Darts and pleats have
  dedicated update tools (help page "Update Notches, Darts And Pleats") [S title]; rotate/transfer/fold dart [D].
- Seam allowance: explicit per-edge SA; distinct "sew line" vs "cut line", with a confirm prompt when
  switching between them (O/26) [S]. Corner styles on SA [D].
- Grainlines on every piece; nesting respects grainline constraints [S]. Internal lines/cutouts [D].
- Mirror/symmetry: mirror piece, symmetrical edit [D].
- Operations stitches: stitch-type annotations on edges, customizable via settings file (O/26) [S].
- Grading: grade rules applied to base-size pieces; grading table dialog synced with a Dynamic Measurement
  Chart that imports Excel measurements and auto-creates pattern/PDS files (O/26) [S]. Sketch & Fill artwork
  scales proportionally across sizes [S]. Nest of sizes reviewed for even stepping [S].
- Verification: seam-length compare / measurement tools [D]; import check of a known dimension after DXF import [S].
- Import/export: DXF AAMA/ASTM with unit setting [S]; PLT, PDF [S via Minerva]; Print & Cut batch PDF/DXF [S].
- Automation: Script Builder batch scripts across PDS and Marker [S].

## 2. 3D workflow (PDS 3D)
- Avatar/mannequin: digital avatar; Alvanon avatar library integrated with O/Cloud [S, apparelresources];
  scanner data flows to PDS 3D [S]. Adjustable avatar measurements/poses [D].
- Sewing: define sewing relationships between 2D piece edges (stitch definitions) [S].
- Arrange pieces around avatar, then simulate [S]. Fabric properties (stretch, bend, weight/density,
  friction, thickness) per fabric, material maps via Material Converter (TIFF, folder batch) [S partly/D].
- Draping simulation; fit maps (strain / looseness) guide pattern changes, re-simulate [S].
- 2D<->3D sync: edit 2D, 3D updates (loop above) [S/D]. Textures/prints via material maps and
  3D Design for Illustrator (3DDI plugin) [S].

## 3. Typical end-to-end workflow
1. Measurements (size chart; Excel -> Dynamic Measurement Chart) [S]
2. Block/sloper (import DXF or draft) [S]
3. Style changes: dart manipulation, pleats, seam lines, SA, notches, grainlines [S/D]
4. Grade: rules/table -> size set, check nest [S]
5. 3D: avatar, sewing, fabric, simulate, fit map, edit 2D, repeat [S]
6. Marker: nest all graded pieces to fabric width (auto Nest++ Pro + manual), batch commands [S]
7. Export: DXF AAMA/ASTM, PLT, PDF print-and-cut, production diagram [S]

## 4. MVP vs later
MVP (web clone):
- Piece model: polyline + bezier points, notches, grainline, internal lines, SA (sew vs cut), mirror
- Editing: point/curve edit, measure/length compare, seam-length verify
- Dart/pleat tools (basic rotate/close dart)
- Size table + point-delta grade rules (x/y per point per size), grade preview
- Import/export DXF (AAMA), PDF/PLT tile print at 1:1
- Simple auto/manual marker nest with grainline constraint
Later:
- 3D: avatar, stitch defs, cloth sim (mass-spring/PBD), fabric params, fit maps, 2D<->3D sync, textures
- Measurement chart auto-generation from Excel, Script Builder/batch, Sketch & Fill artwork scaling
- Advanced nesting (Nest++ style optimizer), bump lines/shading/bundles, production diagram
- Scanner/avatar-library integration, cloud collaboration
