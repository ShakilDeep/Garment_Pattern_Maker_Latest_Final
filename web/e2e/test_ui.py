import re, json, sys
from playwright.sync_api import sync_playwright, expect

results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1500, "height": 900}, accept_downloads=True)
    page = ctx.new_page()
    logs = []
    page.on("console", lambda m: logs.append(f"{m.type}: {m.text}") if m.type in ("error",) else None)
    page.on("pageerror", lambda e: logs.append(f"pageerror: {e}"))
    page.goto("http://localhost:5199/")
    page.wait_for_selector('[data-testid="start-panel"]', timeout=15000)
    check("start-up shows the empty state, no default pattern", page.locator('[data-testid="piece-Front Bodice"]').count() == 0)
    page.click('[data-testid="start-body"]')
    page.wait_for_selector('[data-testid="piece-Front Bodice"]', timeout=15000)
    check("engine falls back to native bridge", "native-bridge" in page.inner_text(".brand"))
    check("bodice shows 3 pieces", page.locator(".piece-list li").count() == 3)
    check("all fit checks pass for default", page.locator('[data-testid="check"].bad').count() == 0 and page.locator('[data-testid="check"]').count() >= 3,
          f"{page.locator('[data-testid=check]').count()} checks")
    check("canvas renders piece polygons", page.locator('svg[data-testid="canvas"] g[data-piece]').count() == 3)

    # --- measurements import via paste ---
    page.get_by_role("button", name="Paste").click()
    page.fill('[data-testid="measure-paste"]', "Measurement,Value\nbust,100\nwaist (cm), 82\nhip 106\nbogus,3")
    page.click('[data-testid="measure-apply"]')
    page.wait_for_function("document.querySelector('[data-testid=\"m-bust\"]').value === '100'")
    check("import applied bust/waist/hip", page.input_value('[data-testid="m-waist"]') == "82" and page.input_value('[data-testid="m-hip"]') == "106")
    check("unknown key reported", "bogus" in page.inner_text(".msgs"))
    check("untouched keys kept", page.input_value('[data-testid="m-neck"]') == "37")
    page.wait_for_timeout(900)
    w1 = page.locator('[data-testid="piece-Back Bodice"] em').inner_text()
    check("pattern regenerated from new measurements", w1 != "", w1)

    # inches toggle shows converted value
    page.get_by_role("button", name="in", exact=True).click()
    check("inch display conversion", abs(float(page.input_value('[data-testid="m-bust"]')) - 100/2.54) < 0.01)
    page.get_by_role("button", name="cm", exact=True).click()

    # --- editing: select node via inspector coordinates ---
    page.click('[data-testid="piece-Back Bodice"]')
    area_before = page.locator(".kv dd").first.inner_text()
    circles = page.locator('circle[data-node]')
    n_before = circles.count()
    check("nodes are shown for selected piece", n_before == 6, str(n_before))
    circles.nth(4).dispatch_event("pointerdown", {"pointerId": 1, "button": 0, "isPrimary": True})
    page.wait_for_selector('[data-testid="node-x"]')
    x0 = float(page.input_value('[data-testid="node-x"]'))
    page.fill('[data-testid="node-x"]', str(x0 + 3))
    page.wait_for_timeout(500)
    area_after = page.locator(".kv dd").first.inner_text()
    check("editing a node changes piece area", area_before != area_after, f"{area_before} -> {area_after}")
    # undo
    page.keyboard.press("Escape")
    page.get_by_role("button", name="Undo").click()
    page.wait_for_timeout(500)
    check("undo restores area", page.locator(".kv dd").first.inner_text() == area_before)
    page.get_by_role("button", name="Redo").click()
    page.wait_for_timeout(400)

    # drag a node with the mouse
    page.get_by_role("button", name="Undo").click(); page.wait_for_timeout(300)
    page.locator('circle[data-node="3"]').dispatch_event("pointerdown", {"pointerId": 1, "button": 0, "isPrimary": True})
    page.wait_for_selector('[data-testid="node-x"]')
    bx0, by0 = float(page.input_value('[data-testid="node-x"]')), float(page.input_value('[data-testid="node-y"]'))
    box = page.locator('circle[data-node="3"]').bounding_box()
    page.mouse.move(box["x"] + box["width"]/2, box["y"] + box["height"]/2)
    page.mouse.down(); page.mouse.move(box["x"] + 40, box["y"] + 25, steps=6); page.mouse.up()
    page.wait_for_timeout(600)
    bx1, by1 = float(page.input_value('[data-testid="node-x"]')), float(page.input_value('[data-testid="node-y"]'))
    check("dragging moved the node", abs(bx1 - bx0) > 0.5 and abs(by1 - by0) > 0.3, f"({bx0},{by0}) -> ({bx1},{by1})")

    # split edge by double click on an edge hit-area
    page.get_by_role("button", name="Fit").click()
    edge = page.locator('polyline[data-edge="4"]').first
    eb = edge.bounding_box()
    nn = page.locator('circle[data-node]').count()
    page.mouse.dblclick(eb["x"] + eb["width"]/2, eb["y"] + eb["height"]/2)
    page.wait_for_timeout(600)
    check("double-click edge adds a node", page.locator('circle[data-node]').count() == nn + 1, f"{nn} -> {page.locator('circle[data-node]').count()}")

    # dart width
    page.click('[data-testid="piece-Front Bodice"]')
    page.fill('[data-testid="dart-0"]', "3")
    page.wait_for_timeout(500)
    check("dart width editable", page.input_value('[data-testid="dart-0"]') == "3")
    # seam allowance
    page.fill('[data-testid="sa-input"]', "1.5")
    page.wait_for_timeout(500)
    check("seam allowance editable", page.input_value('[data-testid="sa-input"]') == "1.5")
    page.screenshot(path="/tmp/e2e/pattern.png")

    # --- export DXF ---
    page.click('[data-testid="export-menu"]')
    with page.expect_download() as dl:
        page.click('[data-testid="export-dxf"]')
    path = dl.value.path()
    dxf = open(path, encoding="utf-8", errors="replace").read()
    check("DXF download has pieces and EOF", "Piece Name: Front Bodice" in dxf and dxf.strip().endswith("EOF") and dxf.count("ENDBLK") == 3, f"{len(dxf)} bytes")
    check("DXF name", dl.value.suggested_filename.endswith(".dxf"), dl.value.suggested_filename)

    # PDS dialog
    page.click('[data-testid="export-menu"]')
    page.click('[data-testid="export-pds"]')
    page.wait_for_selector('[data-testid="pds-dialog"]')
    check("PDS dialog is honest", "proprietary" in page.inner_text('[data-testid="pds-dialog"]'))
    page.get_by_role("button", name="Close").click()

    # --- grading ---
    page.click('[data-testid="tab-grading"]')
    page.click('[data-testid="run-grade"]')
    page.wait_for_selector('[data-testid="grade-table"] tbody tr')
    check("grading table has 3 sizes", page.locator('[data-testid="grade-table"] tbody tr').count() == 3)
    check("graded overlay polygons drawn", page.locator('svg[data-testid="canvas"] polygon[fill="none"]').count() >= 3)
    page.screenshot(path="/tmp/e2e/grading.png")
    page.click('[data-testid="export-menu"]')
    with page.expect_download() as dl2:
        page.click('[data-testid="export-dxf-all"]')
    d2 = open(dl2.value.path(), encoding="utf-8", errors="replace").read()
    check("graded DXF has 3 sizes x 3 pieces", d2.count("ENDBLK") == 9 and "Size Name: S" in d2 and "Size Name: L" in d2, str(d2.count("ENDBLK")))

    # --- garments ---
    page.click('[data-testid="tab-pattern"]')
    page.once("dialog", lambda d: d.accept())
    page.select_option('[data-testid="garment"]', "trousers")
    page.wait_for_selector('[data-testid="piece-Front Trouser"]')
    check("trousers generated", page.locator(".piece-list li").count() == 2)
    page.wait_for_timeout(500)
    page.screenshot(path="/tmp/e2e/trousers.png")
    page.select_option('[data-testid="garment"]', "skirt")
    page.wait_for_selector('[data-testid="piece-Front Skirt"]')
    check("skirt generated", page.locator(".piece-list li").count() == 2)

    # --- 3D tab: simulation runs through the engine; viewer needs `three` (not installed here) ---
    page.click('[data-testid="tab-drape"]')
    page.wait_for_selector('[data-testid="view-error"], [data-testid="drape-canvas"]', timeout=20000)
    check("3D tab doesn't crash the app", page.locator('[data-testid="tab-pattern"]').count() == 1)

    # project save/open roundtrip
    with page.expect_download() as dl3:
        page.get_by_role("button", name="Save project").click()
    proj = json.load(open(dl3.value.path()))
    check("project file has pattern + measurements", proj["app"] == "patternforge" and len(proj["pattern"]["pieces"]) == 2 and proj["measurements"]["bust"] == 100)

    errs = [l for l in logs if "three" not in l and "Failed to fetch dynamically" not in l and "404" not in l]
    check("no unexpected console errors", not errs, "; ".join(errs[:3]))
    b.close()

bad = [r for r in results if not r[1]]
print(f"\n{len(results)-len(bad)}/{len(results)} passed")
sys.exit(1 if bad else 0)
