from __future__ import annotations

from xml.etree import ElementTree

from europe_visa_jobs.connectors.base import BaseConnector, ConnectorError
from europe_visa_jobs.schemas import ATSProvider, NormalizedJob
from europe_visa_jobs.utils import classify_role, html_to_text, infer_country, normalize_whitespace


class PersonioConnector(BaseConnector):
    async def fetch_jobs(self) -> list[NormalizedJob]:
        domain = "com" if (self.source.region or "").casefold() == "com" else "de"
        url = self.endpoint(f"https://{self.source.slug}.jobs.personio.{domain}/xml")
        response = await self._get(url, params={"language": "en"})
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
