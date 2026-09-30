from pathlib import Path
import numpy as np
from PIL import Image

root = Path("/mnt/f/Garment-PatternMaker-Codex")
ref = np.array(Image.open(root / "references/ui/garment-pattern-maker-v5-ui-reference-1536x1024.png").convert("RGB"))
act = np.array(Image.open(root / "artifacts/qa/canonical-actual.png").convert("RGB"))

def find_blue_button_top(img, x0=1200, x1=1510):
    for y in range(820, 1000):
        row = img[y, x0:x1]
        mask = (row[:, 2] > 180) & (row[:, 0] < 120) & (row[:, 1] > 80)
        if mask.mean() > 0.15:
            return y
    return -1

print("next btn top ref", find_blue_button_top(ref), "act", find_blue_button_top(act))

# regenerate button in actions
def find_actions_btn(img):
    for y in range(480, 650):
        row = img[y, 1310:1500]
        mask = (row[:, 2] > 180) & (row[:, 0] < 120) & (row[:, 1] > 80)
        if mask.mean() > 0.2:
            return y, row[mask].mean(axis=0)
    return -1, None

print("actions btn ref", find_actions_btn(ref))
print("actions btn act", find_actions_btn(act))

# canvas left border
def canvas_left(img, y=300):
    for x in range(600, 750):
        if img[y, x, 0] > 250 and img[y, x - 1, 0] < 230:
            return x
    return -1

print("canvas left ref", canvas_left(ref), "act", canvas_left(act))

# meas panel right
def meas_right(img, y=400):
    for x in range(620, 500, -1):
        if img[y, x, 0] > 250 and img[y, x + 1, 0] < 245:
            return x
    return -1

print("approx white span")
# mean abs in info rail excluding text by looking at structure
print("info mean abs", np.abs(ref[:,1298:1510].astype(int)-act[:,1298:1510].astype(int)).mean())
print("actions band mean abs", np.abs(ref[520:650,1298:1510].astype(int)-act[520:650,1298:1510].astype(int)).mean())
print("next band mean abs", np.abs(ref[820:1000,1180:1520].astype(int)-act[820:1000,1180:1520].astype(int)).mean())
print("brand mean abs", np.abs(ref[0:75,0:576].astype(int)-act[0:75,0:576].astype(int)).mean())
print("demo mean abs", np.abs(ref[700:1024,0:223].astype(int)-act[700:1024,0:223].astype(int)).mean())
print("stepper mean abs", np.abs(ref[75:157,223:1536].astype(int)-act[75:157,223:1536].astype(int)).mean())
