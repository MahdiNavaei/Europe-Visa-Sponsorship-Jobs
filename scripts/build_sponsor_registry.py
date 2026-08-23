"""Generate production sponsor evidence from official UK and Dutch registers.

The resulting CSV is a narrow evidence cache: company name, country, registry
name, and the official public source URL.  It does not assert that any
particular vacancy is sponsored; the eligibility engine still requires
job-level evidence and applies hard negatives first.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections.abc import Iterable
from html.parser import HTMLParser
from io import StringIO
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

UK_PUBLICATION_URL = "https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers"
NL_REGISTER_URL = "https://ind.nl/en/public-register-recognised-sponsors/public-register-work"
UK_REGISTRY_NAME = "UKVI Register of Licensed Sponsors (Workers)"
NL_REGISTRY_NAME = "IND Public Register Recognised Sponsors - Labour"
USER_AGENT = "CareerRadar/1.1 (+https://github.com/MahdiNavaei/Europe-Visa-Sponsorship-Jobs)"


def _download(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/csv,*/*;q=0.1"})
    with urlopen(request, timeout=60) as response:
        return response.read()


def _uk_csv_url(publication_html: str) -> str:
    match = re.search(r'href="([^"]*Worker_and_Temporary_Worker[^"?#]*\.csv)"', publication_html, re.I)
    if not match:
        raise RuntimeError("could not locate the current UKVI worker sponsor CSV on the official publication page")
    return urljoin(UK_PUBLICATION_URL, match.group(1).replace("&amp;", "&"))


class _INDWorkRegisterParser(HTMLParser):
    """Extract first-column organization names from the official IND work tables."""

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


def uk_records(csv_bytes: bytes | None = None) -> Iterable[tuple[str, str, str, str]]:
    if csv_bytes is None:
        publication = _download(UK_PUBLICATION_URL).decode("utf-8", "replace")
        csv_bytes = _download(_uk_csv_url(publication))
    text = csv_bytes.decode("utf-8-sig", "replace")
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames or "Organisation Name" not in reader.fieldnames:
        raise RuntimeError("official UKVI CSV does not have an Organisation Name column")
    for row in reader:
        name = (row.get("Organisation Name") or "").strip()
        # Keep only organisations with a Worker route. Temporary-only licences
        # are not evidence for the product's professional-work visa use case.
        if name and "worker" in (row.get("Type & Rating") or "").casefold():
            yield name, "United Kingdom", UK_REGISTRY_NAME, UK_PUBLICATION_URL


def netherlands_records(html_bytes: bytes | None = None) -> Iterable[tuple[str, str, str, str]]:
    parser = _INDWorkRegisterParser()
    parser.feed((html_bytes or _download(NL_REGISTER_URL)).decode("utf-8", "replace"))
    if not parser.rows:
        raise RuntimeError("official IND work register contains no HTML table rows")
    for row in parser.rows:
        if not row or row[0].casefold() in {"organisation", "organization"}:
            continue
        name = row[0].strip()
        if name:
            yield name, "Netherlands", NL_REGISTRY_NAME, NL_REGISTER_URL


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="data/sponsors.csv")
    parser.add_argument("--uk-csv", help="Previously downloaded current official UKVI CSV (for offline/reproducible generation)")
    parser.add_argument("--ind-html", help="Previously downloaded current official IND work-register HTML")
    args = parser.parse_args()
    uk_bytes = Path(args.uk_csv).read_bytes() if args.uk_csv else None
    ind_bytes = Path(args.ind_html).read_bytes() if args.ind_html else None
    records = sorted(
        set(uk_records(uk_bytes)) | set(netherlands_records(ind_bytes)),
        key=lambda row: (row[1], row[0].casefold()),
    )
    if not records:
        raise RuntimeError("official sponsor registry generation produced no records")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["company_name", "country", "registry_name", "source_url"])
        writer.writerows(records)
    print(f"wrote {len(records)} official sponsor-evidence records to {output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"sponsor registry generation failed: {exc}", file=sys.stderr)
        raise
