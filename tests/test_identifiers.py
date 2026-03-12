"""Tests for data_utils.identifiers."""

from data_utils.identifiers import fragment_id


def test_format():
    fid = fragment_id(1, "hello")
    assert fid.startswith("1:")
    assert len(fid.split(":")[1]) == 8


def test_deterministic():
    assert fragment_id(5, "content") == fragment_id(5, "content")


def test_different_content():
    assert fragment_id(1, "a") != fragment_id(1, "b")


def test_different_line():
    assert fragment_id(1, "same") != fragment_id(2, "same")
