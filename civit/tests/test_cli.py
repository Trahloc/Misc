import sys
import pytest
from cli import parse_args


def test_parse_args_minimal(monkeypatch):
    test_args = ["prog", "http://civitai.com/sample"]
    monkeypatch.setattr(sys, "argv", test_args)
    args = parse_args()
    assert args.urls == ["http://civitai.com/sample"]
    assert args.output_dir == "."


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
    args = parse_args()
    assert args.urls == ["http://civitai.com/sample", "http://civitai.com/sample2"]
    assert args.output_dir == "downloads"
    assert args.api_key == "test_key"
    assert args.verbose is True
    assert args.quiet is False
    assert args.very_verbose is False


def test_mutually_exclusive(monkeypatch):
    test_args = ["prog", "http://civitai.com/sample", "-v", "-q"]
    monkeypatch.setattr(sys, "argv", test_args)
    with pytest.raises(SystemExit):
        parse_args()
