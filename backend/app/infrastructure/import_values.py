"""Import validator: every number in an imported payload is finite and plausible, and nesting stays shallow."""
from app.application.errors import ImportInvalid

# Far beyond any garment dimension, quantity or seed; rejects NaN, infinities and overflow-sized integers.
MAX_IMPORT_MAGNITUDE = 1e12
# Exported projects nest about six levels deep; deeper payloads would exhaust recursion when persisted.
MAX_IMPORT_DEPTH = 32


def _invalid(message):
    return ImportInvalid("IMPORT_VALUE_INVALID", message)


def check_numbers(body):
    pending = [(body.pattern, 1), (body.grades, 1), (body.marker, 1)]
    while pending:
        value, depth = pending.pop()
        if isinstance(value, (dict, list)) and depth > MAX_IMPORT_DEPTH:
            raise _invalid("Imported data is nested too deeply")
        if isinstance(value, dict):
            pending.extend((child, depth + 1) for child in value.values())
        elif isinstance(value, list):
            pending.extend((child, depth + 1) for child in value)
        elif isinstance(value, (int, float)) and not abs(value) <= MAX_IMPORT_MAGNITUDE:
            raise _invalid("Imported numbers must be finite and within range")
