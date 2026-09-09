from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "branch_state_archive.py"
_SPEC = importlib.util.spec_from_file_location("branch_state_archive", _SCRIPT)
assert _SPEC and _SPEC.loader
branch_state_archive = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(branch_state_archive)


def test_chunked_state_archive_round_trip(tmp_path: Path):
    source = tmp_path / "state.sqlite"
    payload = bytes(range(256)) * 64
    source.write_bytes(payload)

    manifest_path = branch_state_archive.pack_archive(
        source,
        tmp_path / "publication",
        chunk_size=128,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["format"] == branch_state_archive.FORMAT
    assert len(manifest["chunks"]) > 1
    assert all(chunk["size"] <= 128 for chunk in manifest["chunks"])
    assert branch_state_archive.chunk_names(manifest_path) == [
        chunk["name"] for chunk in manifest["chunks"]
    ]

    restored = tmp_path / "restored.sqlite"
    branch_state_archive.restore_archive(manifest_path, restored)
    assert restored.read_bytes() == payload


def test_chunked_state_archive_rejects_tampering(tmp_path: Path):
    source = tmp_path / "state.sqlite"
    source.write_bytes(bytes(range(128)) * 32)
    manifest_path = branch_state_archive.pack_archive(
        source,
        tmp_path / "publication",
        chunk_size=96,
    )
    first_chunk = manifest_path.parent / branch_state_archive.chunk_names(manifest_path)[0]
    tampered = bytearray(first_chunk.read_bytes())
    tampered[0] ^= 0xFF
    first_chunk.write_bytes(tampered)

    with pytest.raises(ValueError, match="checksum mismatch"):
        branch_state_archive.restore_archive(manifest_path, tmp_path / "restored.sqlite")


def test_chunked_state_archive_rejects_missing_chunk(tmp_path: Path):
    source = tmp_path / "state.sqlite"
    source.write_bytes(b"branch-backed-state" * 512)
    manifest_path = branch_state_archive.pack_archive(
        source,
        tmp_path / "publication",
        chunk_size=64,
    )
    missing = manifest_path.parent / branch_state_archive.chunk_names(manifest_path)[-1]
    missing.unlink()

    with pytest.raises(FileNotFoundError):
        branch_state_archive.restore_archive(manifest_path, tmp_path / "restored.sqlite")


def test_chunked_state_archive_rejects_unsafe_chunk_names(tmp_path: Path):
    manifest_path = tmp_path / "daily.sqlite.gz.manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "format": branch_state_archive.FORMAT,
                "compression": "gzip",
                "source_size": 1,
                "archive_size": 1,
                "archive_sha256": "0" * 64,
                "chunk_size": 1,
                "chunks": [{"name": "../escape", "size": 1, "sha256": "0" * 64}],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsafe"):
        branch_state_archive.chunk_names(manifest_path)
