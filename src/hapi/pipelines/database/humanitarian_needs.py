"""Functions specific to the humanitarian needs theme."""

import re
from datetime import datetime
from logging import getLogger

from hapi_schema.db_humanitarian_needs import DBHumanitarianNeeds
from hdx.api.configuration import Configuration
from hdx.scraper.framework.utilities.reader import Read
from hdx.utilities.dictandlist import dict_of_lists_add
from hdx.utilities.text import get_numeric_if_possible
from sqlalchemy.orm import Session

from ..utilities.logging_helpers import (
    add_missing_value_message,
    add_multi_valued_message,
)
from ..utilities.provider_admin_names import get_provider_name
from . import admins
from .admins import (
    get_admin1_to_location_connector_code,
    get_admin2_to_location_connector_code,
)
from .base_uploader import BaseUploader
from .metadata import Metadata
from .sector import Sector

logger = getLogger(__name__)


class HumanitarianNeeds(BaseUploader):
    admin_name_regex = re.compile(r"Admin (\d) Name")

    def __init__(
        self,
        session: Session,
        metadata: Metadata,
        admins: admins.Admins,
        sector: Sector,
        configuration: Configuration,
    ):
        super().__init__(session)
        self._metadata = metadata
        self._admins = admins
        self._sector = sector
        self._configuration = configuration

    def get_admin2_ref(self, row, dataset_name, errors):
        countryiso3 = row["Country ISO3"]
        if countryiso3 == "#country+code":  # ignore HXL row
            return None
        admin_level = "0"
        for header in row:
            match = self.admin_name_regex.match(header)
            if match and row[header]:
                admin_level = match.group(1)
        match admin_level:
            case "0":
                admin_level = "national"
                admin_code = countryiso3
            case "1":
                admin_level = "adminone"
                admin_code = row["Admin 1 PCode"]
            case "2":
                admin_level = "admintwo"
                admin_code = row["Admin 2 PCode"]
            case _:
                return None
        admin2_ref = self._admins.get_admin2_ref(
            admin_level, admin_code, dataset_name, errors
        )
        if admin2_ref is None:
            if admin_level == "adminone":
                admin_code = get_admin1_to_location_connector_code(countryiso3)
            elif admin_level == "admintwo":
                admin_code = get_admin2_to_location_connector_code(countryiso3)
            else:
                return None
            admin2_ref = self._admins.get_admin2_ref(
                admin_level, admin_code, dataset_name, errors
            )
        return admin2_ref

    def populate(self) -> None:
        logger.info("Populating humanitarian needs table")
        warnings = set()
        errors = set()
        reader = Read.get_reader("hdx")
        dataset = reader.read_dataset("global-hpc-hno", self._configuration)
        self._metadata.add_dataset(dataset)
        dataset_id = dataset["id"]
        dataset_name = dataset["name"]
        resource = dataset.get_resource(0)  # assumes first resource is latest!
        self._metadata.add_resource(dataset_id, resource)
        negative_values_by_iso3 = {}
        rounded_values_by_iso3 = {}
        resource_id = resource["id"]
        resource_name = resource["name"]
        year = int(resource_name[-4:])
        time_period_start = datetime(year, 1, 1)
        time_period_end = datetime(year, 12, 31, 23, 59, 59)
        url = resource["url"]
        headers, rows = reader.get_tabular_rows(url, dict_form=True)
        # Admin 1 PCode,Admin 2 PCode,Sector,Gender,Age Group,Disabled,Population Group,Population,In Need,Targeted,Affected,Reached
        for row in rows:
            countryiso3 = row["Country ISO3"]
            admin2_ref = self.get_admin2_ref(row, dataset_name, errors)
            if not admin2_ref:
                continue
            provider_admin1_name = get_provider_name(row, "Admin 1 Name")
            provider_admin2_name = get_provider_name(row, "Admin 2 Name")
            sector = row["Sector"]
            sector_code = self._sector.get_sector_code(sector)
            if not sector_code:
                add_missing_value_message(
                    errors, dataset_name, "sector", sector
                )
                continue
            category = row["Category"]
            if category is None:
                category = ""

            def create_row(in_col, population_status):
                value = row[in_col]
                if value is None:
                    return
                value = get_numeric_if_possible(value)
                if value < 0:
                    dict_of_lists_add(
                        negative_values_by_iso3, countryiso3, str(value)
                    )
                    return
                if isinstance(value, float):
                    dict_of_lists_add(
                        rounded_values_by_iso3, countryiso3, str(value)
                    )
                    value = round(value)
                humanitarian_needs_row = DBHumanitarianNeeds(
                    resource_hdx_id=resource_id,
                    admin2_ref=admin2_ref,
                    provider_admin1_name=provider_admin1_name,
                    provider_admin2_name=provider_admin2_name,
                    category=category,
                    sector_code=sector_code,
                    population_status=population_status,
                    population=value,
                    reference_period_start=time_period_start,
                    reference_period_end=time_period_end,
                )
                self._session.add(humanitarian_needs_row)

            create_row("Population", "all")
            create_row("Affected", "AFF")
            create_row("In Need", "INN")
            create_row("Targeted", "TGT")
            create_row("Reached", "REA")

        self._session.commit()
        for countryiso3, values in negative_values_by_iso3.items():
            add_multi_valued_message(
                errors,
                f"{dataset_name} - {countryiso3}",
                "negative values removed",
                values,
            )
        for countryiso3, values in rounded_values_by_iso3.items():
            add_multi_valued_message(
                warnings,
                f"{dataset_name} - {countryiso3}",
                "float values rounded",
                values,
            )

        for warning in sorted(warnings):
            logger.warning(warning)
        for error in sorted(errors):
            logger.error(error)
