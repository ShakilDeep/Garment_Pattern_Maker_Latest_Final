from pathlib import Path
import json
import openpyxl
import pdfplumber

root = Path(__file__).resolve().parents[1]
out = root / 'tmp' / 'references'
out.mkdir(parents=True, exist_ok=True)
for path in (root / 'references').glob('*.pdf'):
    with pdfplumber.open(path) as pdf:
        texts = []
        for i, page in enumerate(pdf.pages):
            texts.append(f'PAGE {i+1}\n{page.extract_text() or "[No text layer]"}')
            page.to_image(resolution=65).save(out / f'{path.stem}-{i+1}.png')
        text = '\n'.join(texts)
        (out / f'{path.stem}.txt').write_text(text, encoding='utf-8')
        print(path.name, text)
for path in (root / 'references').glob('*.xlsx'):
    wb = openpyxl.load_workbook(path, data_only=False)
    rows = {s.title: [[c.value for c in row] for row in s] for s in wb}
    (out / 'workbook.json').write_text(json.dumps(rows, ensure_ascii=False, default=str), encoding='utf-8')
    print(json.dumps(rows, ensure_ascii=False, default=str))
