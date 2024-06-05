"""Functions specific to the humanitarian needs theme."""

from logging import getLogger

from hapi_schema.db_humanitarian_needs import DBHumanitarianNeeds
from hdx.api.configuration import Configuration
from hdx.scraper.utilities.reader import Read
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

    def get_admin2_ref(self, countryiso3, row, dataset_name, errors):
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
                admin_code = countryiso3
                admin_level = "national"
        admin2_code = admins.get_admin2_code_based_on_level(
            admin_code=admin_code, admin_level=admin_level
        )
        ref = self._admins.admin2_data.get(admin2_code)
        if ref is None:
            add_missing_value_message(
                errors, dataset_name, "admin 2 code", admin2_code
            )
        return ref

    def populate(self):
        logger.info("Populating humanitarian needs table")
        reader = Read.get_reader("hdx")
        datasets = reader.search_datasets(
            filename="hno_dataset",
            fq="name:hno-data-for-*",
            configuration=self._configuration,
        )
        warnings = set()
        errors = set()
        for dataset in datasets:
            negative_values = []
            rounded_values = []
            dataset_name = dataset["name"]
            self._metadata.add_dataset(dataset)
            countryiso3 = dataset.get_location_iso3s()[0]
            time_period = dataset.get_time_period()
            time_period_start = time_period["startdate_str"]
            time_period_end = time_period["enddate_str"]
            resource = dataset.get_resource()
            resource_id = resource["id"]
            url = resource["url"]
            headers, rows = reader.get_tabular_rows(url, dict_form=True)
            # Admin 1 PCode,Admin 2 PCode,Sector,Gender,Age Group,Disabled,Population Group,Population,In Need,Targeted,Affected,Reached
            for row in rows:
                admin2_ref = self.get_admin2_ref(
                    countryiso3, row, dataset_name, errors
                )
                if not admin2_ref:
                    continue
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
                        negative_values.append(str(value))
                        return
                    if isinstance(value, float):
                        rounded_values.append(str(value))
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

                create_row("Population", "POP")
                create_row("Affected", "AFF")
                create_row("In Need", "INN")
                create_row("Targeted", "TGT")
                create_row("Reached", "REA")

            self._session.commit()
            add_multi_valued_message(
                errors,
                dataset_name,
                "negative values removed",
                negative_values,
            )
            add_multi_valued_message(
                warnings,
                dataset_name,
                "float values rounded",
                rounded_values,
            )

        for warning in sorted(warnings):
            logger.warning(warning)
        for error in sorted(errors):
            logger.error(error)
