import sys
import pytest
from unittest.mock import patch
from src.civit.cli import parse_args


def test_parse_args_minimal(monkeypatch):
    test_args = ["prog", "http://civitai.com/sample"]
    monkeypatch.setattr(sys, "argv", test_args)
    with patch("sys.argv", test_args):
        args = parse_args()
    assert args.urls == ["http://civitai.com/sample"]
    assert args.output_folder.rstrip("/") == "."


def test_parse_args_with_options(monkeypatch):
    test_args = [
        "prog",
        "http://civitai.com/sample",
        "http://civitai.com/sample2",
        "-o",
        "downloads",
        "-k",
        "test_key",
        "-v",
    ]
    monkeypatch.setattr(sys, "argv", test_args)
    with patch("sys.argv", test_args):
        args = parse_args()
    assert args.urls == ["http://civitai.com/sample", "http://civitai.com/sample2"]
    assert args.output_folder.rstrip("/") == "downloads"
    assert args.api_key == "test_key"
    assert args.verbose is True


def test_mutually_exclusive(monkeypatch):
    test_args = ["prog", "http://civitai.com/sample", "-v", "-q"]
    monkeypatch.setattr(sys, "argv", test_args)
    with pytest.raises(SystemExit):
        parse_args()


def test_debug_flag_parsing():
    """Test that the debug flag is correctly parsed"""
    with patch("sys.argv", ["civit", "-d", "https://example.com"]):
        args = parse_args()
        assert args.debug is True
        assert args.verbose is False

    with patch("sys.argv", ["civit", "--debug", "https://example.com"]):
        args = parse_args()
        assert args.debug is True
        assert args.verbose is False

    with patch("sys.argv", ["civit", "https://example.com"]):
        args = parse_args()
        assert getattr(args, "debug", False) is False

    with patch("sys.argv", ["civit", "-v", "https://example.com"]):
        args = parse_args()
        assert args.verbose is True
        assert getattr(args, "debug", False) is False


def test_custom_naming_flags():
    """Test that the custom naming flags are correctly parsed"""
    with patch("sys.argv", ["civit", "https://example.com"]):
        args = parse_args()
        assert args.custom_naming is True

    with patch("sys.argv", ["civit", "--custom-naming", "https://example.com"]):
        args = parse_args()
        assert args.custom_naming is True

    with patch("sys.argv", ["civit", "--no-custom-naming", "https://example.com"]):
        args = parse_args()
        assert args.custom_naming is False


def test_url_parsing():
    """Test that URLs are correctly parsed"""
    with patch("sys.argv", ["civit", "https://example.com"]):
        args = parse_args()
        assert len(args.urls) == 1
        assert args.urls[0] == "https://example.com"

    with patch("sys.argv", ["civit", "https://example1.com", "https://example2.com"]):
        args = parse_args()
        assert len(args.urls) == 2
        assert args.urls[0] == "https://example1.com"
        assert args.urls[1] == "https://example2.com"


def test_output_folder():
    """Test that output folder is correctly parsed"""
    import os

    with patch("sys.argv", ["civit", "https://example.com"]):
        args = parse_args()
        assert args.output_folder == os.getcwd()

    with patch("sys.argv", ["civit", "-o", "/tmp/output", "https://example.com"]):
        args = parse_args()
        assert args.output_folder == "/tmp/output"

    with patch(
        "sys.argv", ["civit", "--output-folder", "/tmp/output2", "https://example.com"]
    ):
        args = parse_args()
        assert args.output_folder == "/tmp/output2"
