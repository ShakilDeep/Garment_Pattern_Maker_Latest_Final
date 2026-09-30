from pathlib import Path
import json
import pdfplumber
from PIL import Image, ImageChops, ImageStat

root=Path(__file__).resolve().parents[1]
out=root/'artifacts/qa'
with pdfplumber.open(out/'demo.pdf') as pdf:
    print('PDF pages:',len(pdf.pages))
    for i,page in enumerate(pdf.pages):
        page.to_image(resolution=100).save(out/f'pdf-page-{i+1}.png')
        print('Page',i+1,'characters:',len(page.extract_text() or ''))
reference=Image.open(root/'references/ui/garment-pattern-maker-v5-ui-reference-1536x1024.png').convert('RGB')
actual=Image.open(out/'measurements-1536x1024.png').convert('RGB')
actual=actual.crop((0,0,1536,1024))
diff=ImageChops.difference(reference,actual)
diff.save(out/'reference-diff.png')
Image.blend(reference,actual,.5).save(out/'reference-overlay.png')
metrics={'viewport':[1536,1024],'mean_absolute_channel_difference':sum(ImageStat.Stat(diff).mean)/3,
         'interpretation':'Comparison evidence only. Source measurements and calibrated demo geometry differ from the illustration; pixel-identical acceptance is not claimed.'}
(out/'visual-comparison.json').write_text(json.dumps(metrics,indent=2))
print(metrics)
