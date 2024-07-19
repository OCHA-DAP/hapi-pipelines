"""Populate the org table."""

import logging
from typing import Dict, NamedTuple

from hapi_schema.db_org import DBOrg
from hdx.scraper.utilities.reader import Read
from hdx.utilities.text import normalise
from sqlalchemy.orm import Session

from ..utilities.batch_populate import batch_populate
from .base_uploader import BaseUploader

logger = logging.getLogger(__name__)

_BATCH_SIZE = 1000


class OrgInfo(NamedTuple):
    canonical_name: str
    normalised_name: str
    acronym: str | None
    normalised_acronym: str | None
    type_code: str | None


class OrgData(NamedTuple):
    acronym: str
    name: str
    type_code: str


class Org(BaseUploader):
    def __init__(
        self,
        session: Session,
        datasetinfo: Dict[str, str],
    ):
        super().__init__(session)
        self._datasetinfo = datasetinfo
        self.data = {}
        self._org_map = {}

    def populate(self):
        logger.info("Populating org mapping")
        reader = Read.get_reader()
        headers, iterator = reader.get_tabular_rows(
            self._datasetinfo["url"],
            headers=2,
            dict_form=True,
            format="csv",
            file_prefix="org",
        )

        for row in iterator:
            canonical_name = row["#org+name"]
            if not canonical_name:
                continue
            normalised_name = normalise(canonical_name)
            country_code = row["#country+code"]
            acronym = row["#org+acronym"]
            if acronym:
                normalised_acronym = normalise(acronym)
            else:
                normalised_acronym = None
            org_name = row["#x_pattern"]
            type_code = row["#org+type+code"]
            org_info = OrgInfo(
                canonical_name,
                normalised_name,
                acronym,
                normalised_acronym,
                type_code,
            )
            self._org_map[(country_code, canonical_name)] = org_info
            self._org_map[(country_code, normalised_name)] = org_info
            self._org_map[(country_code, acronym)] = org_info
            self._org_map[(country_code, normalised_acronym)] = org_info
            self._org_map[(country_code, org_name)] = org_info
            self._org_map[(country_code, normalise(org_name))] = org_info

    def get_org_info(self, org_str: str, location: str) -> OrgInfo:
        key = (location, org_str)
        org_info = self._org_map.get(key)
        if org_info:
            return org_info
        normalised_str = normalise(org_str)
        org_info = self._org_map.get((location, normalised_str))
        if org_info:
            self._org_map[key] = org_info
            return org_info
        org_info = self._org_map.get((None, org_str))
        if org_info:
            self._org_map[key] = org_info
            return org_info
        org_info = self._org_map.get((None, normalised_str))
        if org_info:
            self._org_map[key] = org_info
            return org_info
        org_info = OrgInfo(org_str, normalised_str, None, None, None)
        self._org_map[key] = org_info
        return org_info

    def add_or_match_org(
        self,
        acronym: str,
        acronym_normalise: str,
        org_name: str,
        org_name_normalise: str,
        org_type_code: str,
    ) -> OrgData:
        key = (acronym_normalise, org_name_normalise)
        org_data = self.data.get(key)
        if org_data:
            if org_type_code and not org_data.type_code:
                org_data = OrgData(
                    org_data.acronym, org_data.name, org_type_code
                )
                self.data[key] = org_data
            # TODO: should we flag orgs if we find more than one org type?
        else:
            org_data = OrgData(acronym, org_name, org_type_code)
            self.data[key] = org_data
        return org_data

    def populate_multiple(self):
        org_rows = [
            dict(
                acronym=org_data.acronym,
                name=org_data.name,
                org_type_code=org_data.type_code,
            )
            for org_data in self.data.values()
        ]
        batch_populate(org_rows, self._session, DBOrg)
