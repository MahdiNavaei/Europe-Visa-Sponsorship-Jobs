from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

FORMAT = "career-radar-branch-state-v1"
DEFAULT_CHUNK_SIZE = 48 * 1024 * 1024
_COPY_BUFFER = 1024 * 1024


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(_COPY_BUFFER):
            digest.update(block)
    return digest.hexdigest()


def _safe_chunk_name(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("state archive manifest contains an invalid chunk name")
    candidate = Path(value)
    if candidate.name != value or value in {".", ".."}:
        raise ValueError(f"unsafe state archive chunk name: {value!r}")
    return value


def pack_archive(
    source: Path,
    output_dir: Path,
    *,
    prefix: str = "daily.sqlite.gz",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> Path:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if not source.is_file():
        raise FileNotFoundError(source)

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / f"{prefix}.manifest.json"
    temp_archive = output_dir / f".{prefix}.packing"

    for stale in output_dir.glob(f"{prefix}.part-*"):
        stale.unlink()
    manifest_path.unlink(missing_ok=True)
    temp_archive.unlink(missing_ok=True)

    try:
        with (
            source.open("rb") as source_handle,
            temp_archive.open("wb") as raw_handle,
            gzip.GzipFile(
                filename="",
                mode="wb",
                compresslevel=9,
                fileobj=raw_handle,
                mtime=0,
            ) as compressed,
        ):
            shutil.copyfileobj(source_handle, compressed, length=_COPY_BUFFER)

        chunks: list[dict[str, Any]] = []
        with temp_archive.open("rb") as archive_handle:
            index = 0
            while block := archive_handle.read(chunk_size):
                name = f"{prefix}.part-{index:03d}"
                chunk_path = output_dir / name
                chunk_path.write_bytes(block)
                chunks.append(
                    {
                        "name": name,
                        "size": len(block),
                        "sha256": hashlib.sha256(block).hexdigest(),
                    }
                )
                index += 1

        if not chunks:
            raise ValueError("compressed state archive unexpectedly produced no chunks")

        manifest = {
            "format": FORMAT,
            "compression": "gzip",
            "source_size": source.stat().st_size,
            "archive_size": temp_archive.stat().st_size,
            "archive_sha256": _sha256(temp_archive),
            "chunk_size": chunk_size,
            "chunks": chunks,
        }
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return manifest_path
    finally:
        temp_archive.unlink(missing_ok=True)


def _load_manifest(manifest_path: Path) -> dict[str, Any]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("state archive manifest must be a JSON object")
    if payload.get("format") != FORMAT:
        raise ValueError(f"unsupported state archive format: {payload.get('format')!r}")
    if payload.get("compression") != "gzip":
        raise ValueError("state archive manifest must use gzip compression")
    chunks = payload.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        raise ValueError("state archive manifest must contain at least one chunk")
    return payload


def chunk_names(manifest_path: Path) -> list[str]:
    manifest = _load_manifest(manifest_path)
    names: list[str] = []
    for item in manifest["chunks"]:
        if not isinstance(item, dict):
            raise ValueError("state archive manifest contains an invalid chunk entry")
        names.append(_safe_chunk_name(item.get("name")))
    return names


def restore_archive(manifest_path: Path, output: Path) -> None:
    manifest = _load_manifest(manifest_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_archive = output.with_name(f".{output.name}.archive.tmp")
    temp_output = output.with_name(f".{output.name}.restore.tmp")
    temp_archive.unlink(missing_ok=True)
    temp_output.unlink(missing_ok=True)

    try:
        with temp_archive.open("wb") as archive_handle:
            for item in manifest["chunks"]:
                if not isinstance(item, dict):
                    raise ValueError("state archive manifest contains an invalid chunk entry")
                name = _safe_chunk_name(item.get("name"))
                chunk_path = manifest_path.parent / name
                if not chunk_path.is_file():
                    raise FileNotFoundError(chunk_path)
                expected_size = int(item.get("size", -1))
                if chunk_path.stat().st_size != expected_size:
                    raise ValueError(f"state archive chunk size mismatch: {name}")
                expected_sha = item.get("sha256")
                if not isinstance(expected_sha, str) or _sha256(chunk_path) != expected_sha:
                    raise ValueError(f"state archive chunk checksum mismatch: {name}")
                with chunk_path.open("rb") as chunk_handle:
                    shutil.copyfileobj(chunk_handle, archive_handle, length=_COPY_BUFFER)

        expected_archive_size = int(manifest.get("archive_size", -1))
        if temp_archive.stat().st_size != expected_archive_size:
            raise ValueError("state archive size does not match its manifest")
        expected_archive_sha = manifest.get("archive_sha256")
        if not isinstance(expected_archive_sha, str) or _sha256(temp_archive) != expected_archive_sha:
            raise ValueError("state archive checksum does not match its manifest")

        with gzip.open(temp_archive, "rb") as compressed, temp_output.open("wb") as restored:
            shutil.copyfileobj(compressed, restored, length=_COPY_BUFFER)

        expected_source_size = int(manifest.get("source_size", -1))
        if temp_output.stat().st_size != expected_source_size:
            raise ValueError("restored state size does not match its manifest")
        temp_output.replace(output)
    finally:
        temp_archive.unlink(missing_ok=True)
        temp_output.unlink(missing_ok=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pack and restore chunked branch-backed state")
    subparsers = parser.add_subparsers(dest="command", required=True)

    pack = subparsers.add_parser("pack")
    pack.add_argument("--input", type=Path, required=True)
    pack.add_argument("--output-dir", type=Path, required=True)
    pack.add_argument("--prefix", default="daily.sqlite.gz")
    pack.add_argument("--chunk-size-mib", type=int, default=48)

    restore = subparsers.add_parser("restore")
    restore.add_argument("--manifest", type=Path, required=True)
    restore.add_argument("--output", type=Path, required=True)

    list_chunks = subparsers.add_parser("list-chunks")
    list_chunks.add_argument("--manifest", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "pack":
        manifest = pack_archive(
            args.input,
            args.output_dir,
            prefix=args.prefix,
            chunk_size=args.chunk_size_mib * 1024 * 1024,
        )
        print(manifest)
    elif args.command == "restore":
        restore_archive(args.manifest, args.output)
    else:
        for name in chunk_names(args.manifest):
            print(name)


if __name__ == "__main__":
    main()
