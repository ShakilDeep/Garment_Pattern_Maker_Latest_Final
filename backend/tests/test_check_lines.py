"""The line-budget checker flags only source files longer than the limit."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_lines.py"
spec = importlib.util.spec_from_file_location("check_lines", SCRIPT)
assert spec and spec.loader
check_lines = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_lines)


def _write(path: Path, lines: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x = 1\n" * lines, encoding="utf-8")
    return path


def test_small_files_pass(tmp_path):
    _write(tmp_path / "src" / "ok.py", 10)
    assert check_lines.oversized([tmp_path / "src"], 100) == []


def test_limit_is_inclusive_and_next_line_fails(tmp_path):
    _write(tmp_path / "src" / "edge.ts", 100)
    over = _write(tmp_path / "src" / "over.tsx", 101)
    assert check_lines.oversized([tmp_path / "src"], 100) == [(over, 101)]


def test_non_source_files_are_ignored(tmp_path):
    _write(tmp_path / "src" / "notes.md", 500)
    assert check_lines.oversized([tmp_path / "src"], 100) == []


@pytest.mark.parametrize("skipped", sorted(check_lines.SKIPPED_DIRS))
def test_vendor_dirs_inside_root_are_ignored(tmp_path, skipped):
    _write(tmp_path / "src" / skipped / "big.py", 500)
    assert check_lines.oversized([tmp_path / "src"], 100) == []


def test_skipped_names_above_root_do_not_hide_files(tmp_path):
    root = tmp_path / "dist" / "src"
    over = _write(root / "big.py", 101)
    assert check_lines.oversized([root], 100) == [(over, 101)]


def test_main_reports_offenders_and_fails(tmp_path, capsys):
    _write(tmp_path / "src" / "big.py", 150)
    assert check_lines.main([str(tmp_path / "src")]) == 1
    assert "big.py: 150" in capsys.readouterr().out


def test_main_succeeds_when_clean(tmp_path):
    _write(tmp_path / "src" / "small.py", 5)
    assert check_lines.main([str(tmp_path / "src")]) == 0
