from pathlib import Path

from app.infrastructure.parsers import parse_pdf, parse_xlsx

ROOT = Path(__file__).resolve().parents[2]


def test_technical_fields_keep_page_and_original_evidence():
    p = parse_pdf((ROOT / 'references/1078983(5).pdf').read_bytes(), 'tech.pdf')
    fields = p['attributes']
    assert next(a for a in fields if a['key'] == 'garment_weight')['value'] == '228 GR'
    assert any(a['category'] == 'bom' and a['page'] == 5 for a in fields)
    assert any(a['category'] == 'construction' and 'CL28' in a['raw'] for a in fields)
    assert all(a['raw'] and a['page'] >= 1 and a['parser_version'] for a in fields)
    assert all(0 <= a['confidence'] <= 1 for a in fields)


def test_workbook_provenance():
    rows = parse_xlsx((ROOT / 'references/Book2(4).xlsx').read_bytes(), 'book.xlsx')
    chest = next(r for r in rows if r['key'] == 'half_chest')
    assert chest['original_label'].startswith('*')
    assert chest['parser_version']
    assert chest['values']['L']['evaluation'] == 'direct'
    assert 0 <= chest['confidence'] <= 1
