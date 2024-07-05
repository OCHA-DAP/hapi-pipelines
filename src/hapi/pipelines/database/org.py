"""Populate the org table."""

import logging
from typing import Dict

from hapi_schema.db_org import DBOrg
from hdx.scraper.utilities.reader import Read
from hdx.utilities.dictandlist import dict_of_sets_add
from hdx.utilities.text import normalise
from sqlalchemy.orm import Session

from ..utilities.batch_populate import batch_populate
from .base_uploader import BaseUploader

logger = logging.getLogger(__name__)

_BATCH_SIZE = 1000


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
        self._org_lookup = {}

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
            org_name = row.get("#x_pattern")
            canonical_org_name = row.get("#org+name")
            if not canonical_org_name:
                continue
            self._org_map[org_name] = row
            self._org_map[canonical_org_name] = row
            org_acronym = row.get("#org+acronym")
            if org_acronym:
                self._org_map[org_acronym] = row

    def add_or_match_org(
        self,
        acronym,
        org_name,
        org_type,
    ):
        key = (
            normalise(acronym),
            normalise(org_name),
        )
        if key in self.data:
            org_type_old = self.data[key][2]
            if org_type and not org_type_old:
                self.data[key][2] = org_type
            # TODO: should we flag orgs if we find more than one org type?
            return
        self.data[
            (
                normalise(acronym),
                normalise(org_name),
            )
        ] = [acronym, org_name, org_type]

    def populate_multiple(self):
        org_rows = [
            dict(
                acronym=values[0],
                name=values[1],
                org_type_code=values[2],
            )
            for values in self.data.values()
        ]
        batch_populate(org_rows, self._session, DBOrg)

    def get_org_info(self, org_name: str, location: str) -> Dict[str, str]:
        org_name_map = {
            on: self._org_map[on]
            for on in self._org_map
            if self._org_map[on]["#country+code"] in [location, None]
        }
        org_map_info = org_name_map.get(org_name)
        if not org_map_info:
            org_name_map_clean = {
                normalise(on): org_name_map[on] for on in org_name_map
            }
            org_name_clean = normalise(org_name)
            org_map_info = org_name_map_clean.get(org_name_clean)
        if not org_map_info:
            return {"#org+name": org_name}
        org_info = {"#org+name": org_map_info["#org+name"]}
        if not org_info["#org+name"]:
            org_info["#org+name"] = org_map_info["#x_pattern"]
        if org_map_info["#org+acronym"]:
            org_info["#org+acronym"] = org_map_info["#org+acronym"]
        if org_map_info["#org+type+code"]:
            org_info["#org+type+code"] = org_map_info["#org+type+code"]
        return org_info

    def add_org_to_lookup(self, org_name_orig, org_name_official):
        dict_of_sets_add(self._org_lookup, org_name_official, org_name_orig)
