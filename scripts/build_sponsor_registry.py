"""Build and validate sponsor evidence from official UK and Dutch registers."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import re
import sys
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser
from io import BytesIO, StringIO
from itertools import chain
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

UK_PUBLICATION_URL = "https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers"
NL_REGISTER_URL = "https://ind.nl/en/public-register-recognised-sponsors/public-register-work"
UK_REGISTRY_NAME = "UKVI Register of Licensed Sponsors (Workers)"
NL_REGISTRY_NAME = "IND Public Register Recognised Sponsors - Labour"
USER_AGENT = "CareerRadar/1.1 (+https://github.com/MahdiNavaei/Europe-Visa-Sponsorship-Jobs)"
FIELDS = ("company_name", "country", "registry_name", "source_url")
EXPECTED = {
    "United Kingdom": (UK_REGISTRY_NAME, UK_PUBLICATION_URL),
    "Netherlands": (NL_REGISTRY_NAME, NL_REGISTER_URL),
}


def _download(url: str) -> bytes:
    request = Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/csv,*/*;q=0.1"},
    )
    with urlopen(request, timeout=60) as response:
        return response.read()


def _uk_csv_url(publication_html: str) -> str:
    links = re.findall(r'href=["\']([^"\']+\.csv(?:\?[^"\']*)?)["\']', publication_html, re.I)
    candidates = [urljoin(UK_PUBLICATION_URL, link.replace("&amp;", "&")) for link in links]
    preferred = [url for url in candidates if "worker" in url.casefold() or "sponsor" in url.casefold()]
    if not preferred:
        raise RuntimeError("could not locate the current UKVI worker sponsor CSV on the official page")
    return preferred[0]


class _INDWorkRegisterParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._in_row = False
        self._in_cell = False
        self._row: list[str] = []
        self._cell: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        if tag == "tr":
            self._in_row = True
            self._row = []
        elif self._in_row and tag in {"td", "th"}:
            self._in_cell = True
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._in_cell:
            self._row.append(" ".join("".join(self._cell).split()))
            self._in_cell = False
        elif tag == "tr" and self._in_row:
            if self._row:
                self.rows.append(self._row)
            self._in_row = False


def uk_records(csv_bytes: bytes) -> Iterable[tuple[str, str, str, str]]:
    reader = csv.DictReader(StringIO(csv_bytes.decode("utf-8-sig", "replace")))
    if not reader.fieldnames or "Organisation Name" not in reader.fieldnames:
        raise RuntimeError("official UKVI CSV does not have an Organisation Name column")
    for row in reader:
        name = (row.get("Organisation Name") or "").strip()
        licence_type = (row.get("Type & Rating") or "").casefold()
        if name and "worker" in licence_type and not licence_type.startswith("temporary worker"):
            yield name, "United Kingdom", UK_REGISTRY_NAME, UK_PUBLICATION_URL


def netherlands_records(html_bytes: bytes) -> Iterable[tuple[str, str, str, str]]:
    parser = _INDWorkRegisterParser()
    parser.feed(html_bytes.decode("utf-8", "replace"))
    if not parser.rows:
        raise RuntimeError("official IND work register contains no HTML table rows")
    for row in parser.rows:
        if not row or row[0].casefold() in {"organisation", "organization", "organisatie"}:
            continue
        name = row[0].strip()
        if name:
            yield name, "Netherlands", NL_REGISTRY_NAME, NL_REGISTER_URL


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _dataset_bytes(records: Iterable[tuple[str, str, str, str]], *, compressed: bool) -> bytes:
    raw = StringIO(newline="")
    writer = csv.writer(raw, lineterminator="\n")
    writer.writerow(FIELDS)
    writer.writerows(records)
    data = raw.getvalue().encode("utf-8")
    if not compressed:
        return data
    output = BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", filename="", mtime=0) as zipped:
        zipped.write(data)
    return output.getvalue()


def _read_rows(path: Path) -> list[dict[str, str]]:
    opener = gzip.open if path.suffix.casefold() == ".gz" else Path.open
    with opener(path, "rt", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise RuntimeError(f"unexpected sponsor registry schema: {reader.fieldnames}")
        return [dict(row) for row in reader]


def validate_registry(
    dataset: Path,
    manifest_path: Path,
    *,
    max_age_days: int,
    minimum_uk: int,
    minimum_nl: int,
    require_input_hashes: bool = False,
) -> dict[str, object]:
    if not dataset.is_file() or not manifest_path.is_file():
        raise RuntimeError("sponsor dataset and provenance manifest must both exist")
    rows = _read_rows(dataset)
    identities: set[tuple[str, str, str]] = set()
    counts: Counter[str] = Counter()
    for row in rows:
        if not all(row.get(field, "").strip() for field in FIELDS):
            raise RuntimeError("sponsor registry contains a blank required field")
        country = row["country"]
        if country not in EXPECTED:
            raise RuntimeError(f"unsupported sponsor registry country: {country}")
        registry, source_url = EXPECTED[country]
        if row["registry_name"] != registry or row["source_url"] != source_url:
            raise RuntimeError(f"untrusted provenance for {country} sponsor record")
        identity = (row["company_name"], country, registry)
        if identity in identities:
            raise RuntimeError("sponsor registry contains duplicate normalized rows")
        identities.add(identity)
        counts[country] += 1
    if counts["United Kingdom"] < minimum_uk or counts["Netherlands"] < minimum_nl:
        raise RuntimeError(f"sponsor registry is suspiciously small: {dict(counts)}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "career-radar-sponsor-registry/v1":
        raise RuntimeError("unsupported sponsor registry manifest format")
    if manifest.get("dataset_sha256") != _sha256(dataset.read_bytes()):
        raise RuntimeError("sponsor dataset SHA-256 does not match its manifest")
    if manifest.get("record_count") != len(rows) or manifest.get("country_counts") != dict(counts):
        raise RuntimeError("sponsor manifest counts do not match the dataset")
    generated_at = datetime.fromisoformat(str(manifest["generated_at"]).replace("Z", "+00:00"))
    if generated_at.tzinfo is None:
        raise RuntimeError("sponsor manifest generated_at must include a timezone")
    if generated_at > datetime.now(UTC) + timedelta(minutes=5):
        raise RuntimeError("sponsor manifest is dated in the future")
    if datetime.now(UTC) - generated_at > timedelta(days=max_age_days):
        raise RuntimeError(f"sponsor registry is older than {max_age_days} days")
    sources = manifest.get("sources")
    if not isinstance(sources, list) or {item.get("url") for item in sources} != {
        UK_PUBLICATION_URL,
        NL_REGISTER_URL,
    }:
        raise RuntimeError("sponsor manifest does not identify both official sources")
    if require_input_hashes and any(not item.get("input_sha256") for item in sources):
        raise RuntimeError("sponsor manifest is missing official input hashes")
    return manifest


def _manifest_path(output: Path, requested: str | None) -> Path:
    return Path(requested) if requested else output.with_name("sponsors.manifest.json")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="data/sponsors.csv.gz")
    parser.add_argument("--manifest")
    parser.add_argument("--uk-csv", help="Current official UKVI CSV for an offline build")
    parser.add_argument("--ind-html", help="Current official IND work-register HTML for an offline build")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--max-age-days", type=int, default=45)
    parser.add_argument("--minimum-uk", type=int, default=50_000)
    parser.add_argument("--minimum-nl", type=int, default=1_000)
    parser.add_argument("--require-input-hashes", action="store_true")
    args = parser.parse_args()
    output = Path(args.output)
    manifest_path = _manifest_path(output, args.manifest)
    if args.validate:
        manifest = validate_registry(
            output,
            manifest_path,
            max_age_days=args.max_age_days,
            minimum_uk=args.minimum_uk,
            minimum_nl=args.minimum_nl,
            require_input_hashes=args.require_input_hashes,
        )
        print(f"validated {manifest['record_count']} official sponsor records")
        return

    publication_bytes: bytes | None = None
    resolved_uk_url: str | None = None
    if args.uk_csv:
        uk_bytes = Path(args.uk_csv).read_bytes()
    else:
        publication_bytes = _download(UK_PUBLICATION_URL)
        resolved_uk_url = _uk_csv_url(publication_bytes.decode("utf-8", "replace"))
        uk_bytes = _download(resolved_uk_url)
    ind_bytes = Path(args.ind_html).read_bytes() if args.ind_html else _download(NL_REGISTER_URL)
    normalized_records: dict[tuple[str, str, str], tuple[str, str, str, str]] = {}
    for record in chain(uk_records(uk_bytes), netherlands_records(ind_bytes)):
        normalized_records[(record[0].casefold(), record[1], record[2])] = record
    records = sorted(normalized_records.values(), key=lambda row: (row[1], row[0].casefold()))
    counts = Counter(record[1] for record in records)
    if counts["United Kingdom"] < args.minimum_uk or counts["Netherlands"] < args.minimum_nl:
        raise RuntimeError(f"official sponsor registry generation is suspiciously small: {dict(counts)}")
    dataset = _dataset_bytes(records, compressed=output.suffix.casefold() == ".gz")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(dataset)
    generated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    manifest = {
        "format": "career-radar-sponsor-registry/v1",
        "generated_at": generated_at,
        "dataset_sha256": _sha256(dataset),
        "record_count": len(records),
        "country_counts": dict(counts),
        "sources": [
            {
                "url": UK_PUBLICATION_URL,
                "resolved_url": resolved_uk_url,
                "input_sha256": _sha256(uk_bytes),
                "publication_page_sha256": _sha256(publication_bytes) if publication_bytes else None,
            },
            {"url": NL_REGISTER_URL, "resolved_url": NL_REGISTER_URL, "input_sha256": _sha256(ind_bytes)},
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    validate_registry(
        output,
        manifest_path,
        max_age_days=1,
        minimum_uk=args.minimum_uk,
        minimum_nl=args.minimum_nl,
        require_input_hashes=True,
    )
    print(f"wrote {len(records)} official sponsor-evidence records to {output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"sponsor registry generation failed: {exc}", file=sys.stderr)
        raise
