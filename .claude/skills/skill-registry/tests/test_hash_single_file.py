"""Tests for hash_single_file."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import hash_single_file


def test_strip_first_line():
    assert hash_single_file.strip_first_line(b"line1\nrest") == b"rest"
    assert hash_single_file.strip_first_line(b"a\nb\nc") == b"b\nc"
    assert hash_single_file.strip_first_line(b"no newline") == b""
    assert hash_single_file.strip_first_line(b"") == b""


def test_hash_strips_metadata_line(tmp_path):
    body = b"# doc\n\nbody bytes\n"
    expected = hashlib.sha256(body).hexdigest()
    p = tmp_path / "x.md"
    p.write_bytes(b'{"some":"metadata"}\n' + body)
    assert hash_single_file.hash_single_file(p) == expected


def test_metadata_changes_dont_alter_hash(tmp_path):
    body = b"# x\n"
    p1 = tmp_path / "v1.md"
    p2 = tmp_path / "v2.md"
    p1.write_bytes(b'{"version":"0.1.0"}\n' + body)
    p2.write_bytes(b'{"version":"2.0.0","extra":"stuff"}\n' + body)
    assert hash_single_file.hash_single_file(p1) == \
           hash_single_file.hash_single_file(p2)


def test_round_trip_via_is_unmodified(tmp_path):
    body = b"# spec\n\ncontent\n"
    raw_hash = hashlib.sha256(body).hexdigest()
    meta = {
        "name": "x",
        "origin": "github.com/lago-morph/ai-skills",
        "content_hash": raw_hash,
        "version": "0.1.0",
        "state": "live",
        "implemented_as": None,
        "merged_into": None,
    }
    first = json.dumps(meta, separators=(",", ":"))
    p = tmp_path / "x.md"
    p.write_bytes(first.encode("utf-8") + b"\n" + body)
    assert hash_single_file.is_unmodified(p) is True


def test_modification_detected(tmp_path):
    body = b"original\n"
    meta = {
        "name": "x",
        "origin": "github.com/lago-morph/ai-skills",
        "content_hash": hashlib.sha256(body).hexdigest(),
        "version": "0.1.0",
        "state": "live",
        "implemented_as": None,
        "merged_into": None,
    }
    first = json.dumps(meta, separators=(",", ":"))
    p = tmp_path / "x.md"
    # Body modified, metadata UNTOUCHED.
    p.write_bytes(first.encode("utf-8") + b"\nmodified\n")
    assert hash_single_file.is_unmodified(p) is False
