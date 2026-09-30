"""Optional cloud AttributeExtractor. Values must already appear in source text."""


class CloudAttributeExtractor:
    def __init__(self, client, api_key, url):
        if not api_key or not url:
            raise ValueError("Cloud extraction is not configured")
        self._client = client
        self._key = api_key
        self._url = url

    def extract(self, pages, filename):
        payload = self._client.post(
            self._url,
            json={"pages": pages, "filename": filename},
            headers={"Authorization": f"Bearer {self._key}"},
        )
        body = payload if isinstance(payload, dict) else payload.json()
        text = "\n".join(str(page.get("text") or "") for page in pages)
        attributes, issues = [], []
        for item in body.get("attributes") or []:
            key, value = item.get("key"), str(item.get("value") or "")
            if key and value and value in text:
                attributes.append({
                    "category": "garment", "key": key, "value": value, "raw": value,
                    "page": 1, "source": filename, "parser_version": "cloud_extract_v1",
                    "confidence": 0.5, "status": "NEEDS_REVIEW",
                })
            else:
                issues.append({
                    "key": key or "unknown", "severity": "WARNING", "page": None,
                    "source": filename, "parser_version": "cloud_extract_v1",
                    "why": f"Cloud candidate {key} was not present in source text; ignored.",
                })
        return attributes, issues
