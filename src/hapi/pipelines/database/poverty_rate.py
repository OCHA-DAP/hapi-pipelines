"""Functions specific to the poverty rate theme."""

from logging import getLogger
from typing import Dict

from hapi_schema.db_poverty_rate import DBPovertyRate
from hdx.api.configuration import Configuration
from hdx.scraper.framework.utilities.reader import Read
from hdx.utilities.dateparse import parse_date
from hdx.utilities.dictandlist import dict_of_lists_add
from hdx.utilities.text import get_numeric_if_possible
from sqlalchemy.orm import Session

from ..utilities.error_handling import ErrorManager
from ..utilities.provider_admin_names import get_provider_name
from . import admins
from .admins import get_admin1_to_location_connector_code
from .base_uploader import BaseUploader
from .metadata import Metadata

logger = getLogger(__name__)


class PovertyRate(BaseUploader):
    def __init__(
        self,
        session: Session,
        metadata: Metadata,
        admins: admins.Admins,
        configuration: Configuration,
        error_manager: ErrorManager,
    ):
        super().__init__(session)
        self._metadata = metadata
        self._admins = admins
        self._configuration = configuration
        self._error_manager = error_manager

    def get_admin1_ref(self, row, dataset_name):
        countryiso3 = row["country_code"]
        if countryiso3 == "#country+code":  # ignore HXL row
            return None
        admin_code = row["admin1_code"]
        if admin_code:
            admin_level = "adminone"
        else:
            admin1_name = row["admin1_name"]
            if admin1_name:
                admin_level = "adminone"
                admin_code = get_admin1_to_location_connector_code(countryiso3)
            else:
                admin_level = "national"
                admin_code = countryiso3
        return self._admins.get_admin1_ref(
            admin_level,
            admin_code,
            dataset_name,
            "PovertyRate",
            self._error_manager,
        )

    def populate(self) -> None:
        logger.info("Populating poverty rate table")
        reader = Read.get_reader("hdx")
        dataset = reader.read_dataset("global-mpi", self._configuration)
        self._metadata.add_dataset(dataset)
        dataset_id = dataset["id"]
        dataset_name = dataset["name"]
        resource = dataset.get_resource(0)
        resource_id = resource["id"]
        self._metadata.add_resource(dataset_id, resource)
        null_values_by_iso3 = {}
        url = resource["url"]
        headers, rows = reader.get_tabular_rows(url, dict_form=True)

        def get_value(row: Dict, in_col: str) -> float:
            countryiso3 = row["country_code"]
            value = row[in_col]
            admin_name = row["admin1_name"]
            if not admin_name:
                admin_name = countryiso3
            if value is None:
                dict_of_lists_add(null_values_by_iso3, countryiso3, admin_name)
                return 0.0
            return get_numeric_if_possible(value)

        # country_code,admin1_code,admin1_name,mpi,headcount_ratio,intensity_of_deprivation,vulnerable_to_poverty,in_severe_poverty,reference_period_start,reference_period_end
        for row in rows:
            admin1_ref = self.get_admin1_ref(row, dataset_name)
            if not admin1_ref:
                continue
            provider_admin1_name = get_provider_name(row, "admin1_name")
            reference_period_start = parse_date(row["reference_period_start"])
            reference_period_end = parse_date(row["reference_period_end"])
            row = DBPovertyRate(
                resource_hdx_id=resource_id,
                admin1_ref=admin1_ref,
                provider_admin1_name=provider_admin1_name,
                reference_period_start=reference_period_start,
                reference_period_end=reference_period_end,
                mpi=get_value(row, "mpi"),
                headcount_ratio=get_value(row, "headcount_ratio"),
                intensity_of_deprivation=get_value(
                    row, "intensity_of_deprivation"
                ),
                vulnerable_to_poverty=get_value(row, "vulnerable_to_poverty"),
                in_severe_poverty=get_value(row, "in_severe_poverty"),
            )
            self._session.add(row)
        self._session.commit()

        for countryiso3, values in null_values_by_iso3.items():
            self._error_manager.add_multi_valued_message(
                "PovertyRate",
                dataset_name,
                f"null values set to 0.0 in {countryiso3}",
                values,
            )
