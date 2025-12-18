import os
from pathlib import Path

import pytest_funcnodes  # noqa: F401


def test_render_launcher_windows_quotes_python_and_file():
    from funcnodes.runner.register import render_launcher_windows

    python_exe = r"C:\Program Files\Python\python.exe"
    content = render_launcher_windows(python_exe)

    assert f'set "PY={python_exe}"' in content
    assert 'set "ARGS=standalone"' in content
    assert 'set "FNW_FILE=%~1"' in content
    assert '"%PY%" -m funcnodes %ARGS% "%FNW_FILE%"' in content


def test_render_launcher_unix_embeds_python_and_calls_module():
    from funcnodes.runner.register import render_launcher_unix

    python_exe = "/opt/venv/bin/python3"
    content = render_launcher_unix(python_exe)

    assert content.startswith("#!")
    assert f'PY="{python_exe}"' in content
    assert 'ARGS="standalone"' in content
    assert 'FNW_FILE="$1"' in content
    assert '"$PY" -m funcnodes $ARGS "$FNW_FILE"' in content


def test_read_package_icon_bytes_has_expected_magic_headers():
    from funcnodes.runner.register import read_package_icon_bytes

    ico = read_package_icon_bytes("ico")
    assert ico[:4] == b"\x00\x00\x01\x00"

    png = read_package_icon_bytes("png")
    assert png[:8] == b"\x89PNG\r\n\x1a\n"

    icns = read_package_icon_bytes("icns")
    assert icns[:4] == b"icns"


def test_copy_package_icon_writes_bytes(tmp_path: Path):
    from funcnodes.runner.register import copy_package_icon, read_package_icon_bytes

    dest = tmp_path / "fnw_icon.png"
    copy_package_icon("png", dest)

    assert dest.exists()
    assert dest.read_bytes() == read_package_icon_bytes("png")


def test_write_launcher_script_creates_unix_executable(tmp_path: Path):
    from funcnodes.runner.register import write_launcher_script

    scripts_dir = tmp_path / "config" / "scripts"
    script = write_launcher_script(
        platform="linux",
        scripts_dir=scripts_dir,
        python_exe="/usr/bin/python3",
    )

    assert script.exists()
    assert script.name == "fnw_open.sh"
    assert script.read_text(encoding="utf-8").startswith("#!")
    # Windows does not support POSIX executable permission bits.
    if os.name != "nt":
        assert (script.stat().st_mode & 0o111) != 0


def test_build_linux_desktop_entry_contains_exec_mime_and_icon(tmp_path: Path):
    from funcnodes.runner.register import build_linux_desktop_entry

    launcher = tmp_path / "scripts" / "fnw_open.sh"
    icon = tmp_path / "scripts" / "fnw_icon.png"

    desktop = build_linux_desktop_entry(exec_path=launcher, icon_path=icon)
    assert 'Exec="' in desktop
    assert "MimeType=application/x-funcnodes-fnw;" in desktop
    assert f"Icon={icon}" in desktop


def test_build_linux_mime_xml_declares_fnw_glob():
    from funcnodes.runner.register import build_linux_mime_xml

    mime_xml = build_linux_mime_xml()
    assert 'type="application/x-funcnodes-fnw"' in mime_xml
    assert 'pattern="*.fnw"' in mime_xml


def test_build_windows_registry_entries_includes_defaulticon_and_open_command(
    tmp_path: Path,
):
    from funcnodes.runner.register import build_windows_registry_entries

    launcher = tmp_path / "fnw_open.cmd"
    icon = tmp_path / "fnw_icon.ico"

    entries = build_windows_registry_entries(launcher_path=launcher, icon_path=icon)
    assert entries["ext"] == ".fnw"
    assert entries["prog_id"] == "FuncNodes.WorkerFile"
    assert entries["default_icon"].endswith('",0')
    assert entries["open_command"].endswith('" "%1"')
