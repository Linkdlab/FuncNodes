import argparse
from pathlib import Path

import pytest_funcnodes  # noqa: F401


def test_add_standalone_parser_parses_args(tmp_path: Path):
    from funcnodes.__main__ import add_standalone_parser

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="task", required=True)
    add_standalone_parser(subparsers)

    fnw_path = tmp_path / "example.fnw"
    fnw_path.write_bytes(b"test")

    args = parser.parse_args(
        [
            "standalone",
            str(fnw_path),
            "--host",
            "127.0.0.1",
            "--worker-port",
            "9500",
            "--ui-port",
            "8500",
            "--no-browser",
        ]
    )

    assert args.task == "standalone"
    assert args.fnw_file == str(fnw_path)
    assert args.host == "127.0.0.1"
    assert args.worker_port == 9500
    assert args.ui_port == 8500
    assert args.open_browser is False


def test_add_standalone_parser_accepts_port_alias(tmp_path: Path):
    from funcnodes.__main__ import add_standalone_parser

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="task", required=True)
    add_standalone_parser(subparsers)

    fnw_path = tmp_path / "example.fnw"
    fnw_path.write_bytes(b"test")

    args = parser.parse_args(["standalone", str(fnw_path), "--port", "8501"])
    assert args.ui_port == 8501
