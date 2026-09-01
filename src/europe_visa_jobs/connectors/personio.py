from __future__ import annotations

from urllib.parse import urlsplit
from xml.etree import ElementTree

from europe_visa_jobs.connectors.base import BaseConnector, ConnectorError
from europe_visa_jobs.schemas import ATSProvider, NormalizedJob, SourceConfig
from europe_visa_jobs.utils import classify_role, html_to_text, infer_country, normalize_whitespace


def _personio_domains(source: SourceConfig) -> tuple[str, ...]:
    """Return likely Personio TLDs while keeping requests on provider-owned hosts."""
    domains: list[str] = []

    def add(value: str | None) -> None:
        normalized = (value or "").casefold()
        if normalized in {"de", "germany"}:
            domain = "de"
        elif normalized == "com":
            domain = "com"
        else:
            return
        if domain not in domains:
            domains.append(domain)

    add(source.region)
    metadata_region = source.metadata.get("region") if isinstance(source.metadata, dict) else None
    add(metadata_region if isinstance(metadata_region, str) else None)

    for value in (source.board_url, source.careers_url, source.api_url):
        if not value:
            continue
        host = (urlsplit(value).hostname or "").casefold().rstrip(".")
        if host.endswith(".jobs.personio.de"):
            add("de")
        elif host.endswith(".jobs.personio.com"):
            add("com")

    # Historical discovery rows do not always carry a region. Try both public
    # Personio domains rather than trusting a stale/custom api_url from an old
    # archive observation.
    add("de")
    add("com")
    return tuple(domains)


class PersonioConnector(BaseConnector):
    async def fetch_jobs(self) -> list[NormalizedJob]:
        response = None
        domain = "de"
        first_error: ConnectorError | None = None
        recoverable_categories = {"not_found", "unsafe_url", "network", "timeout"}

        for candidate_domain in _personio_domains(self.source):
            # Personio sources are deliberately reconstructed from the verified
            # board identifier. Do not feed a historical vanity/custom api_url
            # back into the SSRF allowlist boundary during retries.
            url = f"https://{self.source.slug}.jobs.personio.{candidate_domain}/xml"
            try:
                response = await self._get(url, params={"language": "en"})
            except ConnectorError as exc:
                if first_error is None:
                    first_error = exc
                if exc.category not in recoverable_categories:
                    raise
                continue
            domain = candidate_domain
            break

        if response is None:
            if first_error is not None:
                raise first_error
            raise ConnectorError("personio: no provider domain could be resolved", category="network")

        try:
            root = ElementTree.fromstring(response.text)
        except ElementTree.ParseError as exc:
            raise ConnectorError("personio: invalid XML payload") from exc

        jobs: list[NormalizedJob] = []
        for position in root.findall(".//position"):
            external_id = _text(position, "id")
            title = _text(position, "name") or "Untitled role"
            office = _text(position, "office")
            department = _text(position, "department")
            descriptions: list[str] = []
            for node in position.findall("./jobDescriptions/jobDescription"):
                section_name = _text(node, "name")
                section_value = html_to_text(_text(node, "value"))
                descriptions.append(normalize_whitespace(f"{section_name} {section_value}"))
            description = normalize_whitespace(" ".join(descriptions))
            job_url = f"https://{self.source.slug}.jobs.personio.{domain}/job/{external_id}"
            jobs.append(
                NormalizedJob(
                    external_id=external_id,
                    provider=ATSProvider.PERSONIO,
                    source_slug=self.source.slug,
                    company_name=self.source.company_name,
                    title=title,
                    description=description,
                    location=office,
                    country=infer_country(office, self.source.default_country),
                    department=department or None,
                    employment_type=_text(position, "employmentType") or None,
                    apply_url=job_url,
                    job_url=job_url,
                    job_family=classify_role(title),
                    raw={},
                )
            )
        return jobs


def _text(node: ElementTree.Element, path: str) -> str:
    child = node.find(path)
    return (child.text or "").strip() if child is not None else ""
