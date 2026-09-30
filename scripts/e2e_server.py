"""Run browser acceptance tests against an isolated, disposable database."""
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

if __name__ == '__main__':
    with TemporaryDirectory(prefix='garment-e2e-') as directory:
        os.environ['DATABASE_URL'] = f'sqlite:///{Path(directory) / "test.db"}'
        uvicorn.run('app.api.main:app', host='127.0.0.1', port=8765)
