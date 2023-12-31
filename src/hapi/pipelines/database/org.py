import logging
from typing import Dict

from hapi_schema.db_org import DBOrg
from hdx.location.names import clean_name
from hdx.scraper.utilities.reader import Read
from hdx.utilities.dictandlist import dict_of_sets_add
from sqlalchemy import select
from sqlalchemy.orm import Session

from .base_uploader import BaseUploader

logger = logging.getLogger(__name__)


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
            self._org_map[org_name] = row

    def populate_single(
        self,
        acronym,
        org_name,
        org_type,
        reference_period_start,
        reference_period_end,
    ):
        logger.info(f"Adding org {org_name}")
        org_row = DBOrg(
            acronym=acronym,
            name=org_name,
            org_type_code=org_type,
            reference_period_start=reference_period_start,
            reference_period_end=reference_period_end,
        )
        self._session.add(org_row)
        self._session.commit()
        results = self._session.execute(
            select(DBOrg.id, DBOrg.acronym, DBOrg.name, DBOrg.org_type_code)
        )
        for result in results:
            self.data[
                (result[1].upper(), clean_name(result[2]), result[3])
            ] = result[0]

    def get_org_info(self, org_name: str, location: str) -> Dict[str, str]:
        org_name_map = {
            on: self._org_map[on]
            for on in self._org_map
            if self._org_map[on]["#country+code"] in [location, None]
        }
        org_map_info = org_name_map.get(org_name)
        if not org_map_info:
            org_name_map_clean = {
                clean_name(on): org_name_map[on] for on in org_name_map
            }
            org_name_clean = clean_name(org_name)
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
