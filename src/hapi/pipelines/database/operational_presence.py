"""Functions specific to the operational presence theme."""

from logging import getLogger
from os.path import join
from typing import Dict

from hapi_schema.db_operational_presence import DBOperationalPresence
from hdx.location.adminlevel import AdminLevel
from hdx.location.names import clean_name
from hdx.utilities.dateparse import parse_date
from hdx.utilities.dictandlist import write_list_to_csv
from sqlalchemy.orm import Session

from . import admins
from .base_uploader import BaseUploader
from .metadata import Metadata
from .org import Org
from .org_type import OrgType
from .sector import Sector

logger = getLogger(__name__)


class OperationalPresence(BaseUploader):
    def __init__(
        self,
        session: Session,
        metadata: Metadata,
        admins: admins.Admins,
        adminone: AdminLevel,
        admintwo: AdminLevel,
        org: Org,
        org_type: OrgType,
        sector: Sector,
        results: Dict,
    ):
        super().__init__(session)
        self._metadata = metadata
        self._admins = admins
        self._adminone = adminone
        self._admintwo = admintwo
        self._org = org
        self._org_type = org_type
        self._sector = sector
        self._results = results

    def populate(self, debug=False):
        logger.info("Populating operational presence table")
        rows = []
        if debug:
            debug_rows = []
        number_duplicates = 0
        for dataset in self._results.values():
            time_period_start = dataset["time_period"]["end"]
            for admin_level, admin_results in dataset["results"].items():
                resource_id = admin_results["hapi_resource_metadata"]["hdx_id"]
                hxl_tags = admin_results["headers"][1]
                values = admin_results["values"]

                org_name_index = hxl_tags.index("#org+name")
                try:
                    org_acronym_index = hxl_tags.index("#org+acronym")
                except ValueError:
                    org_acronym_index = hxl_tags.index("#org+name")
                try:
                    org_type_name_index = hxl_tags.index("#org+type+name")
                except ValueError:
                    org_type_name_index = None
                try:
                    sector_index = hxl_tags.index("#sector")
                except ValueError:
                    logger.error("Sector missing from dataset")
                    continue

                for admin_code, org_names in values[org_name_index].items():
                    for i, org_name_orig in enumerate(org_names):
                        admin2_code = admins.get_admin2_code_based_on_level(
                            admin_code=admin_code, admin_level=admin_level
                        )
                        org_acronym_orig = values[org_acronym_index][
                            admin_code
                        ][i]
                        if not org_name_orig:
                            org_name_orig = org_acronym_orig
                        sector_orig = values[sector_index][admin_code][i]
                        if not sector_orig:
                            continue
                        org_type_orig = None
                        if org_type_name_index:
                            org_type_orig = values[org_type_name_index][
                                admin_code
                            ][i]
                        country_code = None
                        if admin_level == "admintwo":
                            country_code = self._admintwo.pcode_to_iso3.get(
                                admin_code
                            )
                        if admin_level == "adminone":
                            country_code = self._admintwo.pcode_to_iso3.get(
                                admin_code
                            )
                        org_info = self._org.get_org_info(
                            org_name_orig, location=country_code
                        )
                        self._org.add_org_to_lookup(
                            org_name_orig, org_info.get("#org+name")
                        )
                        org_name = org_info.get("#org+name")
                        org_acronym = org_info.get(
                            "#org+acronym",
                            values[org_acronym_index][admin_code][i],
                        )
                        if org_acronym is not None and len(org_acronym) > 32:
                            org_acronym = org_acronym[:32]
                        org_type_code = org_info.get("#org+type+code")
                        org_type_name = None
                        if not org_type_code:
                            if org_type_name_index:
                                org_type_name = values[org_type_name_index][
                                    admin_code
                                ][i]
                                if org_type_name:
                                    org_type_code = (
                                        self._org_type.get_org_type_code(
                                            org_type_name
                                        )
                                    )
                        if org_type_name and not org_type_code:
                            logger.error(
                                f"Org type {org_type_name} not in table"
                            )
                        # TODO: find out how unique orgs are. Currently checking that
                        #  combo of acronym/name/type is unique. (More clarity will come
                        #  from HAPI-166).
                        if (
                            org_acronym is not None
                            and org_name is not None
                            and (
                                clean_name(org_acronym).upper(),
                                clean_name(org_name),
                                org_type_code,
                            )
                            not in self._org.data
                        ):
                            # Date is release date of HAPI v1
                            self._org.populate_single(
                                acronym=org_acronym,
                                org_name=org_name,
                                org_type=org_type_code,
                                time_period_start=parse_date("2023-11-21"),
                            )
                        sector_code = self._sector.get_sector_code(sector_orig)
                        if debug:
                            debug_row = {
                                "org_name_orig": org_name_orig,
                                "org_acronym_orig": org_acronym_orig,
                                "org_type_orig": org_type_orig,
                                "sector_orig": sector_orig,
                                "org_name": org_name,
                                "org_acronym": org_acronym,
                                "org_type": org_type_code,
                                "sector": sector_code,
                            }
                            debug_rows.append(debug_row)
                            continue

                        if not sector_code:
                            logger.error(f"Sector {sector_orig} not in table")
                            continue

                        org_ref = self._org.data[
                            (
                                clean_name(org_acronym).upper(),
                                clean_name(org_name),
                                org_type_code,
                            )
                        ]
                        admin2_ref = self._admins.admin2_data[admin2_code]
                        row = (resource_id, org_ref, sector_code, admin2_ref)
                        if row in rows:
                            number_duplicates += 1
                            continue
                        rows.append(row)
                        operational_presence_row = DBOperationalPresence(
                            resource_hdx_id=resource_id,
                            admin2_ref=admin2_ref,
                            org_ref=org_ref,
                            sector_code=sector_code,
                            reference_period_start=time_period_start,
                            # TODO: Add to scraper (HAPI-199)
                            source_data="not yet implemented",
                        )
                        self._session.add(operational_presence_row)

        if debug:
            write_list_to_csv(
                join("saved_data", "debug_operational_presence.csv"),
                debug_rows,
            )
            return
        self._session.commit()
        logger.info(
            f"There were {number_duplicates} duplicate operational presence rows!"
        )
