"""Populate the org table."""

import logging
from typing import Dict, Tuple

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
            value = (
                canonical_name,
                normalised_name,
                acronym,
                normalised_acronym,
                type_code,
            )
            self._org_map[(country_code, normalised_name)] = value
            self._org_map[(country_code, normalised_acronym)] = value
            self._org_map[(country_code, normalise(org_name))] = value

    def add_or_match_org(
        self,
        acronym,
        acronym_normalise,
        org_name,
        org_name_normalise,
        org_type,
    ):
        key = (acronym_normalise, org_name_normalise)
        if key in self.data:
            org_type_old = self.data[key][2]
            if org_type and not org_type_old:
                self.data[key][2] = org_type
            # TODO: should we flag orgs if we find more than one org type?
        else:
            self.data[key] = (acronym, org_name, org_type)
        return self.data[key]

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

    def get_org_info(
        self, org_name: str, location: str
    ) -> Tuple[str, str, str | None, str | None, str | None]:
        key = (location, org_name)
        value = self._org_map.get(key)
        if value:
            return value
        value = self._org_map.get((None, org_name))
        if value:
            self._org_map[key] = value
            return value
        return org_name, org_name, None, None, None

    def add_org_to_lookup(self, org_name_orig, org_name_official):
        dict_of_sets_add(self._org_lookup, org_name_official, org_name_orig)
