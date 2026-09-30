"""Estimate irreducible vs chrome-fixable REF-004 pixel mass."""
from pathlib import Path
import numpy as np
from PIL import Image

root = Path("/mnt/f/Garment-PatternMaker-Codex")
ref = np.array(Image.open(root / "references/ui/garment-pattern-maker-v5-ui-reference-1536x1024.png").convert("RGB"))
act = np.array(Image.open(root / "artifacts/qa/canonical-actual.png").convert("RGB"))
diff = (np.abs(ref.astype(float) - act.astype(float)) / 255.0).max(axis=2) > 0.2
print("total", int(diff.sum()))

# Mask likely irreducible: measurement value cells + canvas CAD
mask = np.zeros_like(diff, dtype=bool)
# measurement inputs approx x=480-600, y=300-720
mask[300:720, 470:610] = True
# canvas
mask[180:690, 650:1280] = True
# summary measurement values
mask[800:960, 250:450] = True
chrome = diff & ~mask
print("after masking values+canvas", int(chrome.sum()), "masked-away", int((diff & mask).sum()))

# Top residual chrome hotspots (20x20 tiles)
h, w = chrome.shape
scores = []
for y in range(0, h - 20, 20):
    for x in range(0, w - 20, 20):
        c = int(chrome[y : y + 20, x : x + 20].sum())
        if c > 40:
            scores.append((c, x, y))
scores.sort(reverse=True)
print("top chrome tiles (count,x,y):")
for row in scores[:15]:
    print(row)
