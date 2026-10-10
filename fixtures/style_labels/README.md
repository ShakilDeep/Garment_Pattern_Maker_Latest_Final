# Labelled style images (T132 gate)

Doc 124 asks for correct garment type and options on **at least 30 labelled images per family** (shirt,
pant). This folder holds that set. It is empty today: the gate is **open** until images are supplied.

## Format
Put the images (PNG, JPEG, WebP, or a PDF whose page 1 shows the garment) next to `labels.json`:

```json
[
  {"file": "shirt_001.jpg", "garment": "shirt", "options": {"sleeve": "short", "collar": "shirt_collar"}},
  {"file": "pant_001.png", "garment": "pant", "options": {"leg": "wide", "waistband": "elastic"}}
]
```

- `garment` is `shirt` or `pant`; option ids and values come from
  `backend/app/domain/style_detect/schema.py` (`GET /api/v1/style/options`).
- Only the options a label states are scored; leave out what the image does not show.
- Record where each image comes from and that it may be sent to Gemini.

## Run
`python scripts/eval_style_detect.py` (needs `GEMINI_API_KEY`). A family is `open` below 30 images, `pass`
when every image is correct and `fail` otherwise (`application/style_eval.py`).
