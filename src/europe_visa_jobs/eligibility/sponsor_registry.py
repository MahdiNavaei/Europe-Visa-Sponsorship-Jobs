from __future__ import annotations

from collections.abc import Iterable

from europe_visa_jobs.schemas import CompanySponsorEvidence
from europe_visa_jobs.utils import normalize_company_name


class SponsorRegistryStore:
    """In-memory exact normalized-name matcher over verified sponsor records."""

    def __init__(self, records: Iterable[CompanySponsorEvidence] = ()) -> None:
        self._records: dict[tuple[str, str], CompanySponsorEvidence] = {}
        for record in records:
            self.add(record)

    def add(self, record: CompanySponsorEvidence) -> None:
        key = (record.country.casefold(), normalize_company_name(record.company_name))
        self._records[key] = record

    def find(self, company_name: str, country: str | None) -> CompanySponsorEvidence | None:
        if not country:
            return None
        return self._records.get((country.casefold(), normalize_company_name(company_name)))
