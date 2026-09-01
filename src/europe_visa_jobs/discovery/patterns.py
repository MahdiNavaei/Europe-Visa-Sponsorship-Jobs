from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import unquote, urlsplit, urlunsplit

from europe_visa_jobs.schemas import ATSProvider, SourceCandidate, SourceConfig

_SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,59}$")
_JUNK = {
    "_next", "api", "assets", "b", "css", "embed", "favicon.ico", "images", "img",
    "jobs", "job_app", "js", "meeting", "robots.txt", "sitemap.xml", "static", "v1",
}


@dataclass(frozen=True)
class ProviderPattern:
    provider: ATSProvider
    hosts: tuple[str, ...]
    path_pattern: re.Pattern[str]
    identifier_group: str = "board"
    canonical_template: str = ""
    api_template: str = ""


@dataclass
class IdentifiedSource:
    provider: ATSProvider
    board_identifier: str
    canonical_url: str
    api_url: str | None
    metadata: dict[str, str] = field(default_factory=dict)

    def candidate(self, *, discovery_method: str, company_name: str | None = None) -> SourceCandidate:
        return SourceCandidate(
            provider=self.provider,
            board_identifier=self.board_identifier,
            canonical_url=self.canonical_url,
            api_url=self.api_url,
            company_name=company_name,
            discovery_method=discovery_method,
            metadata=self.metadata,
        )


def normalize_identifier(value: str) -> str | None:
    value = unquote(value).strip().strip("/")
    if not value or value.casefold() in _JUNK or not _SLUG.fullmatch(value):
        return None
    return value.casefold()


def plausible_identifier(provider: ATSProvider, value: str) -> bool:
    """Reject archive noise before it becomes a network validation attempt.

    The reference implementation found that archive paths contain JS/assets,
    tracking fragments, UUIDs, and Ashby's internal ``root.*`` embed paths.  The
    shape filter is intentionally conservative: a missed board can be recovered
    by a seed or a later index, while probing obvious noise wastes provider quota.
    """
    normalized = normalize_identifier(value)
    if normalized is None or normalized in _JUNK:
        return False
    if provider is ATSProvider.ASHBY and normalized.startswith("root."):
        return False
    return not re.fullmatch(r"[0-9a-f-]{30,}", normalized)


def _host_matches(host: str, pattern: str) -> bool:
    return host == pattern or host.endswith(f".{pattern}")


def _clean_url(parts, path: str) -> str:
    return urlunsplit((parts.scheme or "https", parts.netloc, path.rstrip("/"), "", ""))


def identify_source_url(url: str) -> IdentifiedSource | None:
    """Extract one canonical board from an arbitrary archived/live URL."""
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return None
    host = parts.hostname.casefold() if parts.hostname else ""
    path = unquote(parts.path)

    if host in {"boards.greenhouse.io", "job-boards.greenhouse.io", "boards-api.greenhouse.io"}:
        match = re.search(r"/v1/boards/([^/]+)|/(?!embed/)([^/]+)", path, re.I)
        identifier = normalize_identifier((match.group(1) or match.group(2)) if match else "")
        if identifier:
            return IdentifiedSource(ATSProvider.GREENHOUSE, identifier, f"https://boards.greenhouse.io/{identifier}", f"https://boards-api.greenhouse.io/v1/boards/{identifier}/jobs")

    if host in {"jobs.lever.co", "jobs.eu.lever.co", "api.lever.co", "api.eu.lever.co"}:
        match = re.match(r"/([^/]+)", path)
        identifier = normalize_identifier(match.group(1) if match else "")
        if identifier:
            region = "eu" if host == "jobs.eu.lever.co" else ""
            api_host = "api.eu.lever.co" if region else "api.lever.co"
            return IdentifiedSource(ATSProvider.LEVER, identifier, f"https://{host}/{identifier}", f"https://{api_host}/v0/postings/{identifier}", {"region": region})

    if host in {"jobs.ashbyhq.com", "api.ashbyhq.com"}:
        match = re.search(r"/job-board/([^/]+)|/(?!job-board/)([^/]+)", path, re.I)
        identifier = normalize_identifier((match.group(1) or match.group(2)) if match else "")
        if identifier:
            return IdentifiedSource(ATSProvider.ASHBY, identifier, f"https://jobs.ashbyhq.com/{identifier}", f"https://api.ashbyhq.com/posting-api/job-board/{identifier}")

    if host in {"apply.workable.com", "www.workable.com"}:
        match = re.match(r"/(?!j/|api/)([^/]+)", path, re.I)
        identifier = normalize_identifier(match.group(1) if match else "")
        if identifier:
            return IdentifiedSource(ATSProvider.WORKABLE, identifier, f"https://apply.workable.com/{identifier}", f"https://apply.workable.com/api/v1/widget/accounts/{identifier}")

    for domain in ("com", "de"):
        suffix = f".jobs.personio.{domain}"
        if host.endswith(suffix):
            prefix = host[: -len(suffix)]
            # Valid hosted Personio boards have exactly one tenant label before
            # jobs.personio.*. Archive noise such as www.tenant.jobs.personio.de
            # used to be misclassified as a tenant named "www".
            if not prefix or "." in prefix:
                return None
            identifier = normalize_identifier(prefix)
            if identifier:
                return IdentifiedSource(
                    ATSProvider.PERSONIO,
                    identifier,
                    f"https://{identifier}.jobs.personio.{domain}/",
                    f"https://{identifier}.jobs.personio.{domain}/xml",
                    {"region": domain},
                )

    if host.endswith(".teamtailor.com"):
        identifier = normalize_identifier(host.split(".")[0])
        if identifier:
            return IdentifiedSource(ATSProvider.TEAMTAILOR, identifier, f"https://{host}/", f"https://{host}/jobs")

    if host.endswith(".recruitee.com"):
        identifier = normalize_identifier(host.split(".")[0])
        if identifier:
            return IdentifiedSource(ATSProvider.RECRUITEE, identifier, f"https://{host}/", f"https://{host}/api/offers/")

    if host == "jobs.smartrecruiters.com":
        match = re.match(r"/([^/]+)", path)
        identifier = normalize_identifier(match.group(1) if match else "")
        if identifier:
            return IdentifiedSource(ATSProvider.SMARTRECRUITERS, identifier, f"https://jobs.smartrecruiters.com/{identifier}", f"https://api.smartrecruiters.com/v1/companies/{identifier}/postings")

    if ".myworkdayjobs.com" in host:
        parts_path = [segment for segment in path.split("/") if segment]
        site = parts_path[1] if len(parts_path) >= 2 and parts_path[0].casefold() in {"en-us", "en-gb", "de-de", "fr-fr"} else (parts_path[0] if parts_path else "")
        company = host.split(".wd", 1)[0]
        if company and site:
            return IdentifiedSource(
                ATSProvider.WORKDAY,
                f"{company}:{site}".casefold(),
                f"https://{host}/{parts_path[0]}/{site}" if parts_path else f"https://{host}",
                f"https://{host}/wday/cxs/{company}/{site}/jobs",
                {"workday_company": company, "workday_site": site},
            )
    return None


def identify_provider(url: str) -> ATSProvider | None:
    identified = identify_source_url(url)
    return identified.provider if identified else None


def identify_config(config: SourceConfig) -> IdentifiedSource:
    """Build a canonical endpoint for a seed even when its careers URL is vendor-neutral."""
    if config.board_url:
        identified = identify_source_url(config.board_url)
        if identified:
            return identified
    identifier = normalize_identifier(config.slug) or config.slug.casefold()
    if config.provider is ATSProvider.GREENHOUSE:
        return IdentifiedSource(config.provider, identifier, f"https://boards.greenhouse.io/{identifier}", config.api_url or f"https://boards-api.greenhouse.io/v1/boards/{identifier}/jobs")
    if config.provider is ATSProvider.LEVER:
        return IdentifiedSource(config.provider, identifier, f"https://jobs.lever.co/{identifier}", config.api_url or f"https://api.lever.co/v0/postings/{identifier}")
    if config.provider is ATSProvider.ASHBY:
        return IdentifiedSource(config.provider, identifier, f"https://jobs.ashbyhq.com/{identifier}", config.api_url or f"https://api.ashbyhq.com/posting-api/job-board/{identifier}")
    if config.provider is ATSProvider.WORKABLE:
        return IdentifiedSource(config.provider, identifier, f"https://apply.workable.com/{identifier}", config.api_url or f"https://apply.workable.com/api/v1/widget/accounts/{identifier}")
    if config.provider is ATSProvider.PERSONIO:
        domain: str | None = None
        for value in (config.board_url, config.careers_url, config.api_url):
            if not value:
                continue
            host = (urlsplit(value).hostname or "").casefold().rstrip(".")
            if host.endswith(".jobs.personio.de"):
                domain = "de"
                break
            if host.endswith(".jobs.personio.com"):
                domain = "com"
                break
        if domain is None:
            region = config.region
            if not region and isinstance(config.metadata, dict):
                metadata_region = config.metadata.get("region")
                region = metadata_region if isinstance(metadata_region, str) else None
            domain = "com" if (region or "").casefold() == "com" else "de"
        return IdentifiedSource(
            config.provider,
            identifier,
            f"https://{identifier}.jobs.personio.{domain}/",
            f"https://{identifier}.jobs.personio.{domain}/xml",
            {"region": domain},
        )
    if config.provider is ATSProvider.TEAMTAILOR:
        return IdentifiedSource(config.provider, identifier, config.board_url or f"https://{identifier}.teamtailor.com/", config.api_url or f"https://{identifier}.teamtailor.com/jobs")
    if config.provider is ATSProvider.RECRUITEE:
        return IdentifiedSource(config.provider, identifier, config.board_url or f"https://{identifier}.recruitee.com/", config.api_url or f"https://{identifier}.recruitee.com/api/offers/")
    if config.provider is ATSProvider.SMARTRECRUITERS:
        return IdentifiedSource(config.provider, identifier, config.board_url or f"https://jobs.smartrecruiters.com/{identifier}", config.api_url or f"https://api.smartrecruiters.com/v1/companies/{identifier}/postings")
    if config.provider is ATSProvider.WORKDAY:
        return IdentifiedSource(config.provider, identifier, config.board_url or config.careers_url or "", config.api_url, dict(config.metadata))
    return IdentifiedSource(config.provider, identifier, config.careers_url or "", config.api_url)
