from __future__ import annotations

import httpx

from europe_visa_jobs.connectors.ashby import AshbyConnector
from europe_visa_jobs.connectors.base import BaseConnector
from europe_visa_jobs.connectors.greenhouse import GreenhouseConnector
from europe_visa_jobs.connectors.lever import LeverConnector
from europe_visa_jobs.connectors.personio import PersonioConnector
from europe_visa_jobs.connectors.recruitee import RecruiteeConnector
from europe_visa_jobs.connectors.smartrecruiters import SmartRecruitersConnector
from europe_visa_jobs.connectors.teamtailor import TeamtailorConnector
from europe_visa_jobs.connectors.workable import WorkableConnector
from europe_visa_jobs.connectors.workday import WorkdayConnector
from europe_visa_jobs.schemas import ATSProvider, SourceConfig

CONNECTORS: dict[ATSProvider, type[BaseConnector]] = {
    ATSProvider.GREENHOUSE: GreenhouseConnector,
    ATSProvider.LEVER: LeverConnector,
    ATSProvider.ASHBY: AshbyConnector,
    ATSProvider.WORKABLE: WorkableConnector,
    ATSProvider.PERSONIO: PersonioConnector,
    ATSProvider.TEAMTAILOR: TeamtailorConnector,
    ATSProvider.RECRUITEE: RecruiteeConnector,
    ATSProvider.SMARTRECRUITERS: SmartRecruitersConnector,
    ATSProvider.WORKDAY: WorkdayConnector,
}


def build_connector(client: httpx.AsyncClient, source: SourceConfig) -> BaseConnector:
    return CONNECTORS[source.provider](client, source)
