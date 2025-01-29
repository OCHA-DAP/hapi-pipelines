"""Functions specific to the poverty rate theme."""

from logging import getLogger
from typing import Dict

from hapi_schema.db_poverty_rate import DBPovertyRate
from hdx.api.configuration import Configuration
from hdx.api.utilities.hdx_error_handler import HDXErrorHandler
from hdx.scraper.framework.utilities.reader import Read
from hdx.utilities.dateparse import parse_date
from hdx.utilities.dictandlist import dict_of_lists_add, invert_dictionary
from hdx.utilities.text import get_numeric_if_possible
from sqlalchemy.orm import Session

from ..utilities.provider_admin_names import get_provider_name
from . import admins
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
        error_handler: HDXErrorHandler,
    ):
        super().__init__(session)
        self._metadata = metadata
        self._admins = admins
        self._configuration = configuration
        self._error_handler = error_handler

    def populate(self) -> None:
        logger.info("Populating poverty rate table")
        reader = Read.get_reader("hdx")
        dataset = reader.read_dataset("global-mpi", self._configuration)
        self._metadata.add_dataset(dataset)
        dataset_id = dataset["id"]
        dataset_name = dataset["name"]
        null_values_by_iso3 = {}

        def get_value(row: Dict, in_col: str) -> float:
            countryiso3 = row["Country ISO3"]
            value = row[in_col]
            admin_name = row["Admin 1 Name"]
            if not admin_name:
                admin_name = countryiso3
            if value is None:
                dict_of_lists_add(null_values_by_iso3, countryiso3, admin_name)
                return 0.0
            return get_numeric_if_possible(value)

        output_rows = {}
        for resource in list(reversed(dataset.get_resources()))[-2:]:
            resource_id = resource["id"]
            self._metadata.add_resource(dataset_id, resource)
            url = resource["url"]
            header, rows = reader.get_tabular_rows(url, dict_form=True)
            hxltag_to_header = invert_dictionary(next(rows))
            for row in rows:
                admin_level = self._admins.get_admin_level_from_row(
                    hxltag_to_header, row, 1
                )
                admin1_ref = self._admins.get_admin1_ref_from_row(
                    hxltag_to_header,
                    row,
                    dataset_name,
                    "PovertyRate",
                    admin_level,
                )
                if not admin1_ref:
                    continue
                provider_admin1_name = get_provider_name(row, "Admin 1 Name")
                reference_period_start = parse_date(row["Start Date"])
                reference_period_end = parse_date(row["End Date"])
                key = (
                    admin1_ref,
                    provider_admin1_name,
                    reference_period_start,
                    reference_period_end,
                )
                existing_resource_name = output_rows.get(key)
                if existing_resource_name:
                    if existing_resource_name != resource["name"]:
                        continue
                    else:
                        raise ValueError(
                            f"Duplicate row in resource {existing_resource_name} with key {key}!"
                        )
                else:
                    output_rows[key] = resource["name"]
                row = DBPovertyRate(
                    resource_hdx_id=resource_id,
                    admin1_ref=admin1_ref,
                    provider_admin1_name=provider_admin1_name,
                    reference_period_start=reference_period_start,
                    reference_period_end=reference_period_end,
                    mpi=get_value(row, "MPI"),
                    headcount_ratio=get_value(row, "Headcount Ratio"),
                    intensity_of_deprivation=get_value(
                        row, "Intensity of Deprivation"
                    ),
                    vulnerable_to_poverty=get_value(
                        row, "Vulnerable to Poverty"
                    ),
                    in_severe_poverty=get_value(row, "In Severe Poverty"),
                )
                self._session.add(row)
        self._session.commit()

        for countryiso3, values in null_values_by_iso3.items():
            self._error_handler.add_multi_valued_message(
                "PovertyRate",
                dataset_name,
                f"null values set to 0.0 in {countryiso3}",
                values,
            )
