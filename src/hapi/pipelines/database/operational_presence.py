"""Functions specific to the operational presence theme."""

from logging import getLogger
from typing import Dict, Optional

from hapi_schema.db_operational_presence import DBOperationalPresence
from hdx.location.adminlevel import AdminLevel
from hdx.utilities.text import normalise
from sqlalchemy.orm import Session

from ..utilities.batch_populate import batch_populate
from ..utilities.error_handling import ErrorManager
from ..utilities.provider_admin_names import get_provider_name
from . import admins
from .base_uploader import BaseUploader
from .metadata import Metadata
from .org import Org, OrgInfo
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
        error_manager: ErrorManager,
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
        self._error_manager = error_manager

    def complete_org_info(
        self,
        org_info: OrgInfo,
        org_acronym: Optional[str],
        org_type_name: Optional[str],
        dataset_name: str,
    ):
        if org_info.acronym is None and org_acronym is not None:
            if len(org_acronym) > 32:
                org_acronym = org_acronym[:32]
            org_info.acronym = org_acronym
            org_info.normalised_acronym = normalise(org_acronym)

        # * Org type processing
        if org_info.type_code is None and org_type_name is not None:
            org_type_code = self._org_type.get_org_type_code(org_type_name)
            if org_type_code:
                org_info.type_code = org_type_code
            else:
                self._error_manager.add_missing_value_message(
                    "OperationalPresence",
                    dataset_name,
                    "org type",
                    org_type_name,
                )

        # * Org matching
        self._org.add_or_match_org(org_info)

    def populate(self) -> None:
        logger.info("Populating operational presence table")
        operational_presence_rows = []
        for dataset in self._results.values():
            dataset_name = dataset["hdx_stub"]
            time_period_start = dataset["time_period"]["start"]
            time_period_end = dataset["time_period"]["end"]
            number_duplicates = 0
            for admin_level, admin_results in dataset["results"].items():
                values = admin_results["values"]
                # Add this check to see if there is no data, otherwise get a confusing
                # sqlalchemy error
                if not values[0]:
                    raise RuntimeError(
                        f"Admin level {admin_level} in dataset"
                        f" {dataset_name} has no data, "
                        f"please check configuration"
                    )
                hxl_tags = admin_results["headers"][1]
                # If config is missing sector, add to error messages
                try:
                    sector_index = hxl_tags.index("#sector")
                except ValueError:
                    self._error_manager.add_message(
                        "OperationalPresence",
                        dataset_name,
                        "missing sector in config, dataset skipped",
                    )
                    continue
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
                resource_id = admin_results["hapi_resource_metadata"]["hdx_id"]
                for admin_code, org_names in values[org_name_index].items():
                    for i, org_str in enumerate(org_names):
                        # * Sector processing
                        sector_orig = values[sector_index][admin_code][i]
                        # Skip rows that are missing a sector
                        if not sector_orig:
                            self._error_manager.add_message(
                                "OperationalPresence",
                                dataset_name,
                                f"org {org_str} missing sector",
                            )
                            continue
                        sector_code = self._sector.get_sector_code(sector_orig)
                        if not sector_code:
                            self._error_manager.add_missing_value_message(
                                "OperationalPresence",
                                dataset_name,
                                "sector",
                                sector_orig,
                            )
                            continue

                        # * Admin processing
                        if admin_level == "admintwo":
                            country_code = self._admintwo.pcode_to_iso3.get(
                                admin_code
                            )
                        elif admin_level == "adminone":
                            country_code = self._adminone.pcode_to_iso3.get(
                                admin_code
                            )
                        else:
                            country_code = admin_code
                        admin2_code = admins.get_admin2_code_based_on_level(
                            admin_code=admin_code, admin_level=admin_level
                        )
                        admin2_ref = self._admins.admin2_data[admin2_code]

                        # * Admin name processing
                        provider_admin1_name = get_provider_name(
                            values, "#adm1+name", hxl_tags, admin_code, i
                        )
                        provider_admin2_name = get_provider_name(
                            values, "#adm2+name", hxl_tags, admin_code, i
                        )

                        # * Org processing
                        if not org_str:
                            org_str = values[org_acronym_index][admin_code][i]
                        org_info = self._org.get_org_info(
                            org_str, location=country_code
                        )
                        if not org_info.complete:
                            if org_type_name_index:
                                org_type_name = values[org_type_name_index][
                                    admin_code
                                ][i]
                            else:
                                org_type_name = None
                            self.complete_org_info(
                                org_info,
                                values[org_acronym_index][admin_code][i],
                                org_type_name,
                                dataset_name,
                            )

                        operational_presence_row = dict(
                            resource_hdx_id=resource_id,
                            admin2_ref=admin2_ref,
                            provider_admin1_name=provider_admin1_name,
                            provider_admin2_name=provider_admin2_name,
                            org_acronym=org_info.acronym,
                            org_name=org_info.canonical_name,
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
                self._error_manager.add_message(
                    "OperationalPresence",
                    dataset_name,
                    f"{number_duplicates} duplicate rows found",
                )

        logger.info("Writing to org table")
        self._org.populate_multiple()
        logger.info("Writing to operational presence table")
        batch_populate(
            operational_presence_rows, self._session, DBOperationalPresence
        )

        for dataset, msg in self._config.get(
            "operational_presence_error_messages", {}
        ).items():
            self._error_manager.add_message(
                "OperationalPresence", dataset, msg
            )
