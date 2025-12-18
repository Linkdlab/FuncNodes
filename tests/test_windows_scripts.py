from pathlib import Path


def _repo_root() -> Path:
    # backend/FuncNodes/tests/<this file>
    return Path(__file__).resolve().parents[1]


def test_windows_scripts_exist():
    root = _repo_root()
    assert (root / "scripts" / "fnw_open.cmd").exists()
    assert (root / "scripts" / "register_fnw_windows.ps1").exists()


def test_fnw_open_cmd_mentions_standalone():
    root = _repo_root()
    content = (root / "scripts" / "fnw_open.cmd").read_text(encoding="utf-8").lower()
    assert "funcnodes" in content
    assert "standalone" in content
    assert '\\"' not in content


def test_register_script_references_cmd():
    root = _repo_root()
    content = (root / "scripts" / "register_fnw_windows.ps1").read_text(
        encoding="utf-8"
    )
    assert "fnw_open.cmd" in content
