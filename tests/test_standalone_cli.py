import argparse
from pathlib import Path

import pytest
import pytest_funcnodes  # noqa: F401


def test_add_standalone_parser_parses_args(tmp_path: Path):
    from funcnodes.__main__ import add_standalone_parser, validate_standalone_args

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
    validate_standalone_args(parser, args)


def test_add_standalone_parser_accepts_port_alias(tmp_path: Path):
    from funcnodes.__main__ import add_standalone_parser, validate_standalone_args

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="task", required=True)
    add_standalone_parser(subparsers)

    fnw_path = tmp_path / "example.fnw"
    fnw_path.write_bytes(b"test")

    args = parser.parse_args(["standalone", str(fnw_path), "--port", "8501"])
    assert args.ui_port == 8501
    validate_standalone_args(parser, args)


def test_add_standalone_parser_parses_register_flag():
    from funcnodes.__main__ import add_standalone_parser, validate_standalone_args

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="task", required=True)
    add_standalone_parser(subparsers)

    args = parser.parse_args(["standalone", "--register"])
    assert args.task == "standalone"
    assert args.register is True
    assert args.fnw_file is None
    validate_standalone_args(parser, args)


def test_validate_standalone_args_requires_file_when_not_registering():
    from funcnodes.__main__ import add_standalone_parser, validate_standalone_args

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="task", required=True)
    add_standalone_parser(subparsers)

    args = parser.parse_args(["standalone"])
    with pytest.raises(SystemExit):
        validate_standalone_args(parser, args)


def test_validate_standalone_args_rejects_file_when_registering(tmp_path: Path):
    from funcnodes.__main__ import add_standalone_parser, validate_standalone_args

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="task", required=True)
    add_standalone_parser(subparsers)

    fnw_path = tmp_path / "example.fnw"
    fnw_path.write_bytes(b"test")

    args = parser.parse_args(["standalone", str(fnw_path), "--register"])
    with pytest.raises(SystemExit):
        validate_standalone_args(parser, args)
