"""SQL helpers for projection upserts; table and column names are code constants, values are bound."""
import json

from sqlalchemy import text


def encoded(value):
    return json.dumps(value, sort_keys=True, allow_nan=False)


def put(c, table, values, immutable=False):
    columns = list(values)
    placeholders = ','.join(':' + k for k in columns)
    action = 'DO NOTHING' if immutable else 'DO UPDATE SET ' + ','.join(
        f'{k}=excluded.{k}' for k in columns if k != 'id')
    c.execute(text(f'INSERT INTO {table} ({",".join(columns)}) VALUES ({placeholders}) '
                   f'ON CONFLICT(id) {action}'), values)
