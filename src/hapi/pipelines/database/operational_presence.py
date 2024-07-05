"""Functions specific to the operational presence theme."""

from logging import getLogger
from os.path import join
from typing import Dict

from hapi_schema.db_operational_presence import DBOperationalPresence
from hdx.location.adminlevel import AdminLevel
from hdx.utilities.dictandlist import write_list_to_csv
from hdx.utilities.text import normalise
from sqlalchemy.orm import Session

from ..utilities.batch_populate import batch_populate
from ..utilities.logging_helpers import add_message, add_missing_value_message
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
        config: Dict,
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
        self._config = config

    def populate(self, debug=False):
        logger.info("Populating operational presence table")
        operational_presence_rows = []
        if debug:
            debug_rows = []
        errors = set()
        for dataset in self._results.values():
            dataset_name = dataset["hdx_stub"]
            time_period_start = dataset["time_period"]["start"]
            time_period_end = dataset["time_period"]["end"]
            number_duplicates = 0
            for admin_level, admin_results in dataset["results"].items():
                resource_id = admin_results["hapi_resource_metadata"]["hdx_id"]
                hxl_tags = admin_results["headers"][1]
                values = admin_results["values"]
                # Add this check to see if there is no data, otherwise get a confusing
                # sqlalchemy error
                if not values[0]:
                    raise RuntimeError(
                        f"Admin level {admin_level} in dataset"
                        f" {dataset_name} has no data, "
                        f"please check configuration"
                    )
                # Config must contain an org name
                org_name_index = hxl_tags.index("#org+name")
                # If config is missing org acronym, use the org name
                try:
                    org_acronym_index = hxl_tags.index("#org+acronym")
                except ValueError:
                    org_acronym_index = hxl_tags.index("#org+name")
                # If config is missing org type, set to None
                try:
                    org_type_name_index = hxl_tags.index("#org+type+name")
                except ValueError:
                    org_type_name_index = None
                # If config is missing sector, add to error messages
                try:
                    sector_index = hxl_tags.index("#sector")
                except ValueError:
                    add_message(
                        errors,
                        dataset_name,
                        "missing sector in config, dataset skipped",
                    )
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
                        # Skip rows that are missing a sector
                        if not sector_orig:
                            add_message(
                                errors,
                                dataset_name,
                                f"org {org_name_orig} missing sector",
                            )
                            continue
                        org_type_orig = None
                        if org_type_name_index:
                            org_type_orig = values[org_type_name_index][
                                admin_code
                            ][i]
                        country_code = admin_code
                        if admin_level == "admintwo":
                            country_code = self._admintwo.pcode_to_iso3.get(
                                admin_code
                            )
                        if admin_level == "adminone":
                            country_code = self._adminone.pcode_to_iso3.get(
                                admin_code
                            )
                        org_info = self._org.get_org_info(
                            org_name_orig, location=country_code
                        )
                        org_name = org_info.get("#org+name")
                        self._org.add_org_to_lookup(org_name_orig, org_name)
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
                            add_missing_value_message(
                                errors, dataset_name, "org type", org_type_name
                            )
                        self._org.add_or_match_org(
                            acronym=org_acronym,
                            org_name=org_name,
                            org_type=org_type_code,
                        )
                        org_acronym, org_name, org_type = self._org.data[
                            (
                                normalise(org_acronym),
                                normalise(org_name),
                            )
                        ]
                        sector_code = self._sector.get_sector_code(sector_orig)
                        if debug:
                            debug_row = {
                                "location": country_code,
                                "org_name_orig": org_name_orig,
                                "org_acronym_orig": org_acronym_orig,
                                "org_type_orig": org_type_orig,
                                "sector_orig": sector_orig,
                                "org_name": org_name,
                                "org_acronym": org_acronym,
                                "org_type": org_type_code,
                                "sector": sector_code,
                            }
                            if debug_row in debug_rows:
                                continue
                            debug_rows.append(debug_row)
                            continue

                        if not sector_code:
                            add_missing_value_message(
                                errors, dataset_name, "sector", sector_orig
                            )
                            continue

                        admin2_ref = self._admins.admin2_data[admin2_code]
                        operational_presence_row = dict(
                            resource_hdx_id=resource_id,
                            admin2_ref=admin2_ref,
                            org_acronym=org_acronym,
                            org_name=org_name,
                            sector_code=sector_code,
                            reference_period_start=time_period_start,
                            reference_period_end=time_period_end,
                        )
                        if (
                            operational_presence_row
                            in operational_presence_rows
                        ):
                            number_duplicates += 1
                            continue
                        operational_presence_rows.append(
                            operational_presence_row
                        )
            if number_duplicates:
                add_message(
                    errors,
                    dataset_name,
                    f"{number_duplicates} duplicate rows found",
                )
        if debug:
            write_list_to_csv(
                join("saved_data", "debug_operational_presence.csv"),
                debug_rows,
            )
            return

        logger.info("Writing to org table")
        self._org.populate_multiple()
        logger.info("Writing to operational presence table")
        batch_populate(
            operational_presence_rows, self._session, DBOperationalPresence
        )

        for dataset, msg in self._config.get(
            "operational_presence_error_messages", dict()
        ).items():
            add_message(errors, dataset, msg)
        for error in sorted(errors):
            logger.error(error)
