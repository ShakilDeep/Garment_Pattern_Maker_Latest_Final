from PIL import Image
from pathlib import Path
root = Path("/mnt/f/Garment-PatternMaker-Codex")
ref = Image.open(root / "references/ui/garment-pattern-maker-v5-ui-reference-1536x1024.png")
act = Image.open(root / "artifacts/qa/canonical-actual.png")
out = root / "artifacts/qa/crops"
ref.crop((1280, 160, 1520, 420)).save(out / "ref-info2.png")
act.crop((1280, 160, 1520, 420)).save(out / "act-info2.png")
ref.crop((1280, 420, 1520, 700)).save(out / "ref-act2.png")
act.crop((1280, 420, 1520, 700)).save(out / "act-act2.png")
ref.crop((200, 0, 400, 75)).save(out / "ref-brand-edge.png")
act.crop((200, 0, 400, 75)).save(out / "act-brand-edge.png")
ref.crop((1100, 780, 1520, 1010)).save(out / "ref-next2.png")
act.crop((1100, 780, 1520, 1010)).save(out / "act-next2.png")
print("ok")
