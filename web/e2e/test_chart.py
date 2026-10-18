import sys
from playwright.sync_api import sync_playwright
S = "/home/claude/samples/"
res = []
def check(n, c, d=""):
    res.append(bool(c)); print(("PASS " if c else "FAIL ") + n + (f"  [{d}]" if d and not c else ""))
with sync_playwright() as p:
    b = p.chromium.launch(); page = b.new_page(viewport={"width": 1500, "height": 900})
    errs = []; page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto("http://localhost:5199/"); page.wait_for_selector('[data-testid="tab-import"]', timeout=15000)
    page.click('[data-testid="tab-import"]')
    page.set_input_files('[data-testid="spec-file"]', S + "garment_measurement_chart.xlsx")
    page.wait_for_selector('[data-testid="source-panel"]', timeout=25000)
    page.wait_for_timeout(1500)
    check("chart is drawn as a SHIRT (not pant)", page.locator('[data-testid="panel-kind"]').input_value() == "shirt", page.locator('[data-testid="panel-kind"]').input_value())
    n = page.locator(".piece-list li").count(); check("pieces drawn", n >= 3, str(n))
    check("fit banner shows spec matched", "matches the spec" in page.inner_text('[data-testid="fit-banner"]'), page.inner_text('[data-testid="fit-banner"]')[:150])
    check("no unmapped banner", page.locator('[data-testid="unmapped-banner"]').count() == 0)
    check("base size L selected", page.locator('[data-testid="spec-size"]').input_value() == "L")
    def sig(): return page.inner_text(".piece-list")
    page.select_option('[data-testid="spec-size"]', "S"); page.wait_for_timeout(1200)
    check("size S still fits", "matches the spec" in page.inner_text('[data-testid="fit-banner"]'))
    page.select_option('[data-testid="spec-size"]', "3XL"); page.wait_for_timeout(1200)
    check("size 3XL still fits", "matches the spec" in page.inner_text('[data-testid="fit-banner"]'))
    check("no page errors", not errs, str(errs[:2]))
    b.close()
sys.exit(0 if all(res) else 1)
