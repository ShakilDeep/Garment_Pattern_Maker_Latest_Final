from app.infrastructure.chart_parser import parse_chart
from app.infrastructure.pdf_parser import parse_pdf

__all__ = ["parse_pdf", "parse_xlsx"]


def parse_xlsx(data: bytes, filename: str) -> list[dict]:
    """Legacy measurement rows of a spec workbook (see ``parse_chart`` for the full chart)."""
    return parse_chart(data, filename).measurements
