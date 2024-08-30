"""Functions specific to the humanitarian needs theme."""

from datetime import datetime
from logging import getLogger

from hapi_schema.db_humanitarian_needs import DBHumanitarianNeeds
from hdx.api.configuration import Configuration
from hdx.scraper.utilities.reader import Read
from hdx.utilities.dictandlist import dict_of_lists_add
from hdx.utilities.text import get_numeric_if_possible
from sqlalchemy.orm import Session

from ..utilities.logging_helpers import (
    add_missing_value_message,
    add_multi_valued_message,
)
from . import admins
from .base_uploader import BaseUploader
from .metadata import Metadata
from .sector import Sector

logger = getLogger(__name__)


class HumanitarianNeeds(BaseUploader):
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
        admin_code = row["Admin 2 PCode"]
        if admin_code == "#adm2+code":  # ignore HXL row
            return None
        if admin_code:
            admin_level = "admintwo"
        else:
            admin_code = row["Admin 1 PCode"]
            if admin_code:
                admin_level = "adminone"
            else:
                admin_code = row["Country ISO3"]
                admin_level = "national"
        return self._admins.get_admin2_ref(
            admin_level, admin_code, dataset_name, errors
        )

    def populate(self) -> None:
        logger.info("Populating humanitarian needs table")
        warnings = set()
        errors = set()
        reader = Read.get_reader("hdx")
        dataset = reader.read_dataset("global-hpc-hno", self._configuration)
        self._metadata.add_dataset(dataset)
        dataset_id = dataset["id"]
        dataset_name = dataset["name"]
        resource = dataset.get_resource()  # assumes first resource is latest!
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
            admin2_ref = self.get_admin2_ref(row, dataset_name, errors)
            if not admin2_ref:
                continue
            countryiso3 = row["Country ISO3"]
            population_group = row["Population Group"]
            if population_group == "ALL":
                population_group = "all"
            sector = row["Sector"]
            sector_code = self._sector.get_sector_code(sector)
            if not sector_code:
                add_missing_value_message(
                    errors, dataset_name, "sector", sector
                )
                continue
            gender = row["Gender"]
            if gender == "a":
                gender = "all"
            age_range = row["Age Range"]
            min_age = row["Min Age"]
            max_age = row["Max Age"]
            disabled_marker = row["Disabled"]
            if disabled_marker == "a":
                disabled_marker = "all"

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
                    gender=gender,
                    age_range=age_range,
                    min_age=min_age,
                    max_age=max_age,
                    sector_code=sector_code,
                    population_group=population_group,
                    population_status=population_status,
                    disabled_marker=disabled_marker,
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
