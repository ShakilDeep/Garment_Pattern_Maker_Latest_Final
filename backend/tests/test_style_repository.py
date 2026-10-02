"""P1-07: styles and their command history persist in SQLite (schema v4) with optimistic concurrency."""

import pytest
from sqlalchemy import text
from test_cad_style_bus import BUS, _move, _style

from app.application.cad.history import History
from app.application.errors import StyleConflict
from app.infrastructure.repository import Repository
from app.infrastructure.style_repository import StyleRepository


@pytest.fixture
def store(tmp_path):
    return StyleRepository(Repository(f"sqlite:///{tmp_path}/styles.db").engine)


def test_schema_v4_adds_the_styles_table(store):
    with store.engine.connect() as connection:
        assert connection.execute(text("SELECT max(version) FROM schema_versions")).scalar() == 4
        assert connection.execute(text("SELECT count(*) FROM styles")).scalar() == 0


def test_a_style_and_its_history_round_trip(store):
    store.add(_style(), project_id=None)
    record = store.get("shirt")
    assert (record.style, record.history, record.version) == (_style(), History(), 1)
    edited, history = BUS.dispatch(record.style, record.history, "move_point", _move(1))
    assert store.save(edited, history, expected_version=1) == 2
    saved = store.get("shirt")
    assert saved.style == edited and saved.history == history.collected() and saved.version == 2


def test_a_stale_save_is_refused_and_changes_nothing(store):
    store.add(_style(), project_id=None)
    edited, history = BUS.dispatch(_style(), History(), "move_point", _move(1))
    store.save(edited, history, expected_version=1)
    with pytest.raises(StyleConflict, match="changed since it was loaded"):
        store.save(_style(), History(), expected_version=1)
    assert store.get("shirt").style == edited


def test_unknown_and_duplicate_styles(store):
    with pytest.raises(KeyError):
        store.get("nope")
    store.add(_style(), project_id=None)
    with pytest.raises(StyleConflict, match="already exists"):
        store.add(_style(), project_id=None)


def test_a_v3_database_upgrades_once_and_a_newer_one_is_refused(tmp_path):
    url = f"sqlite:///{tmp_path}/v3.db"
    with Repository(url).engine.begin() as connection:
        connection.execute(text("DROP TABLE styles"))
        connection.execute(text("DELETE FROM schema_versions WHERE version = 4"))
    for _ in range(2):
        with Repository(url).engine.connect() as connection:
            assert connection.execute(text("SELECT max(version) FROM schema_versions")).scalar() == 4
            assert connection.execute(text("SELECT count(*) FROM styles")).scalar() == 0
    with Repository(url).engine.begin() as connection:
        connection.execute(text("INSERT INTO schema_versions VALUES (5)"))
    with pytest.raises(RuntimeError, match="newer than this application"):
        Repository(url)


def test_missing_rows_are_not_found_and_corrupt_rows_are_server_errors(store):
    with pytest.raises(KeyError, match="Unknown project"):
        store.add(_style(), project_id="no-such-project")
    with pytest.raises(KeyError, match="Unknown style"):
        store.save(_style(), History(), expected_version=1)
    store.add(_style(), project_id=None)
    with store.engine.begin() as connection:
        connection.execute(text("UPDATE styles SET style_json = '{}' WHERE id = 'shirt'"))
    with pytest.raises(RuntimeError, match="Stored style shirt is corrupt"):
        store.get("shirt")
