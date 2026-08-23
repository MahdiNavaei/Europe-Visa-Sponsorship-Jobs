"""Convert Freehire's MIT-licensed ATS board catalog into discovery candidates.

The generated JSON is deliberately only an input to the normal discovery
pipeline.  It does not mark boards verified or package any third-party job
data: every candidate must still pass this project's live provider validation.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml

SUPPORTED_PROVIDERS = {"greenhouse", "lever", "ashby", "workable"}
CATALOG_ORIGIN = "https://github.com/strelov1/freehire"
CATALOG_LICENSE = "MIT"
REFERENCE_ORIGIN = "https://github.com/trylynceus/jobs"
REFERENCE_LICENSE = "CC BY 4.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True, help="Freehire sources directory")
    parser.add_argument("--output", type=Path, required=True, help="Discovery candidate JSON output")
    parser.add_argument(
        "--provider",
        action="append",
        choices=sorted(SUPPORTED_PROVIDERS),
        help="One or more supported provider catalogs (defaults to all)",
    )
    parser.add_argument(
        "--location-board",
        action="append",
        type=Path,
        help="Optional Lynceus city-board Markdown file; keep only matching employer names",
    )
    parser.add_argument("--limit", type=int, help="Optional deterministic cap after candidate sorting")
    parser.add_argument("--offset", type=int, default=0, help="Deterministic number of sorted candidates to skip")
    return parser.parse_args()


def _company_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def location_board_companies(paths: list[Path]) -> set[str]:
    companies: set[str] = set()
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            columns = [value.strip() for value in line.strip().split("|")]
            if len(columns) < 4 or columns[1].casefold() in {"role", "---"}:
                continue
            company = columns[2]
            if company:
                companies.add(_company_key(company))
    return companies


def build_candidates(
    source_dir: Path,
    providers: set[str],
    *,
    reference_companies: set[str] | None = None,
) -> list[dict[str, object]]:
    candidates: dict[tuple[str, str], dict[str, object]] = {}
    for provider in sorted(providers):
        path = source_dir / f"{provider}.yml"
        if not path.is_file():
            raise FileNotFoundError(f"Freehire catalog is missing {path}")
        entries = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(entries, list):
            raise ValueError(f"Freehire catalog {path} is not a YAML list")
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            company = entry.get("company")
            board = entry.get("board")
            if not isinstance(company, str) or not isinstance(board, str) or not board.strip():
                continue
            if reference_companies is not None and _company_key(company) not in reference_companies:
                continue
            slug = board.strip()
            metadata: dict[str, str] = {
                "candidate_catalog": CATALOG_ORIGIN,
                "candidate_catalog_license": CATALOG_LICENSE,
            }
            if reference_companies is not None:
                metadata.update(
                    {
                        "geographic_candidate_reference": REFERENCE_ORIGIN,
                        "geographic_candidate_reference_license": REFERENCE_LICENSE,
                    }
                )
            candidates.setdefault(
                (provider, slug.casefold()),
                {
                    "provider": provider,
                    "company_name": company.strip() or slug,
                    "slug": slug,
                    "discovery_method": "licensed_catalog_freehire",
                    "metadata": metadata,
                    # ``load_sources`` accepts enabled entries only. Discovery
                    # deliberately persists these with enabled=False until
                    # live validation succeeds, so this flag cannot make a
                    # catalog candidate eligible for ingestion by itself.
                    "enabled": True,
                },
            )
    return [candidates[key] for key in sorted(candidates)]


def main() -> None:
    args = parse_args()
    providers = set(args.provider or SUPPORTED_PROVIDERS)
    references = location_board_companies(args.location_board) if args.location_board else None
    candidates = build_candidates(args.source_dir, providers, reference_companies=references)
    if args.offset < 0:
        raise ValueError("--offset cannot be negative")
    candidates = candidates[args.offset :]
    if args.limit is not None:
        if args.limit < 1:
            raise ValueError("--limit must be positive")
        candidates = candidates[: args.limit]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(candidates, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(candidates)} unverified candidate boards to {args.output}")


if __name__ == "__main__":
    main()
