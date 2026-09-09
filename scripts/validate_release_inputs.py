"""Fail fast when a Windows release would package inconsistent or demo inputs."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from europe_visa_jobs.discovery.snapshot import validate_snapshot  # noqa: E402
from scripts.build_sponsor_registry import validate_registry  # noqa: E402


def _version_from_init() -> str:
    match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', (ROOT / "src/europe_visa_jobs/__init__.py").read_text(encoding="utf-8"), re.M)
    if not match:
        raise RuntimeError("could not read backend version")
    return match.group(1)


def _installer_version() -> str:
    match = re.search(r'#define AppVersion "([^"]+)"', (ROOT / "packaging/windows/installer.iss").read_text(encoding="utf-8"))
    if not match:
        raise RuntimeError("could not read default installer version")
    return match.group(1)


def _validate_web_lock_contract(package: dict, lock: dict) -> None:
    lock_root = lock.get("packages", {}).get("")
    if not isinstance(lock_root, dict):
        raise RuntimeError("web lockfile is missing its root package entry")
    if lock_root.get("name") != package.get("name"):
        raise RuntimeError("web lockfile root package name does not match package.json")

    # npm's root package version is descriptive metadata and does not participate
    # in dependency resolution. Keep the stronger invariant instead: every root
    # dependency declaration must exactly match package.json. `npm ci` then proves
    # the complete resolved graph is reproducible without forcing lockfile churn
    # for a release-only application version bump.
    for section in ("dependencies", "devDependencies", "optionalDependencies"):
        expected = package.get(section, {})
        actual = lock_root.get(section, {})
        if actual != expected:
            raise RuntimeError(f"web lockfile {section} do not match package.json")


def validate(*, require_snapshot: bool, require_input_hashes: bool = False) -> str:
    backend = _version_from_init()
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    package = json.loads((ROOT / "apps/web/package.json").read_text(encoding="utf-8"))
    web = package["version"]
    lock = json.loads((ROOT / "apps/web/package-lock.json").read_text(encoding="utf-8"))
    _validate_web_lock_contract(package, lock)
    versions = {"backend": backend, "pyproject": pyproject, "web": web, "installer": _installer_version()}
    if len(set(versions.values())) != 1:
        detail = ", ".join(f"{key}={value}" for key, value in versions.items())
        raise RuntimeError(f"release version mismatch: {detail}")
    if require_snapshot:
        snapshot_path = ROOT / "config/source-registry.snapshot.json"
        if not snapshot_path.is_file():
            raise RuntimeError("release registry snapshot is missing")
        validate_snapshot(json.loads(snapshot_path.read_text(encoding="utf-8")), minimum_verified=500, maximum_age=None)
    if require_input_hashes:
        validate_registry(
            ROOT / "data/sponsors.csv.gz",
            ROOT / "data/sponsors.manifest.json",
            max_age_days=45,
            minimum_uk=50_000,
            minimum_nl=1_000,
            require_input_hashes=True,
        )
    return backend


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-snapshot", action="store_true")
    parser.add_argument("--require-input-hashes", action="store_true")
    args = parser.parse_args()
    print(
        "release inputs valid: "
        f"v{validate(require_snapshot=args.require_snapshot, require_input_hashes=args.require_input_hashes)}"
    )


if __name__ == "__main__":
    main()
