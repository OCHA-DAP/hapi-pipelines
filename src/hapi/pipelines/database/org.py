"""Populate the org table."""

import logging
from dataclasses import dataclass
from os.path import join
from typing import Dict, NamedTuple

from hapi_schema.db_org import DBOrg
from hdx.scraper.utilities.reader import Read
from hdx.utilities.dictandlist import write_list_to_csv
from hdx.utilities.text import normalise
from sqlalchemy.orm import Session

from ..utilities.batch_populate import batch_populate
from .base_uploader import BaseUploader

logger = logging.getLogger(__name__)

_BATCH_SIZE = 1000


@dataclass
class OrgInfo:
    canonical_name: str
    normalised_name: str
    acronym: str | None
    normalised_acronym: str | None
    type_code: str | None
    used: bool = False
    complete: bool = False


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

        for i, row in enumerate(iterator):
            canonical_name = row["#org+name"]
            if not canonical_name:
                logger.error(f"Canonical name is empty in row {i}!")
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
        org_info = OrgInfo(
            canonical_name=org_str,
            normalised_name=normalised_str,
            acronym=None,
            normalised_acronym=None,
            type_code=None,
        )
        self._org_map[key] = org_info
        return org_info

    def add_or_match_org(self, org_info: OrgInfo) -> OrgData:
        key = (org_info.normalised_acronym, org_info.normalised_name)
        org_data = self.data.get(key)
        if org_data:
            if not org_data.type_code and org_info.type_code:
                org_data = OrgData(
                    org_data.acronym, org_data.name, org_info.type_code
                )
                self.data[key] = org_data
                # TODO: should we flag orgs if we find more than one org type?
            else:
                org_info.type_code = org_data.type_code
            # Since we're looking up by normalised acronym and normalised name,
            # these don't need copying here
            org_info.acronym = org_data.acronym
            org_info.canonical_name = org_data.name

        else:
            org_data = OrgData(
                org_info.acronym, org_info.canonical_name, org_info.type_code
            )
            self.data[key] = org_data
        if org_info.acronym and org_info.type_code:
            org_info.complete = True
        org_info.used = True
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

    def output_org_map(self, folder: str) -> None:
        rows = [
            (
                "Country Code",
                "Lookup",
                "Canonical Name",
                "Normalised Name",
                "Acronym",
                "Normalised Acronym",
                "Type Code",
                "Used",
                "Complete",
            )
        ]
        for key, org_info in self._org_map.items():
            country_code, lookup = key
            rows.append(
                (
                    country_code,
                    lookup,
                    org_info.canonical_name,
                    org_info.normalised_name,
                    org_info.acronym,
                    org_info.normalised_acronym,
                    org_info.type_code,
                    "Y" if org_info.used else "N",
                    "Y" if org_info.complete else "N",
                )
            )
        write_list_to_csv(join(folder, "org_map.csv"), rows)
