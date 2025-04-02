from abc import ABC
from logging import getLogger
from typing import Dict, List, Optional, Type

from hapi_schema.utils.base import Base
from hdx.api.configuration import Configuration
from hdx.api.utilities.hdx_error_handler import HDXErrorHandler
from hdx.database import Database
from hdx.scraper.framework.utilities.reader import Read
from hdx.utilities.dateparse import parse_date
from hdx.utilities.dictandlist import invert_dictionary

from . import admins, locations
from hapi.pipelines.database.base_uploader import BaseUploader
from hapi.pipelines.database.metadata import Metadata

logger = getLogger(__name__)


class HapiSubcategoryUploader(BaseUploader, ABC):
    def __init__(
        self,
        database: Database,
        metadata: Metadata,
        locations: locations.Locations,
        admins: admins.Admins,
        configuration: Configuration,
        error_handler: HDXErrorHandler,
    ):
        super().__init__(database)
        self._metadata = metadata
        self._locations = locations
        self._admins = admins
        self._configuration = configuration
        self._error_handler = error_handler

    def populate_row(self, output_row: Dict, row: Dict) -> None:
        return

    def hapi_populate(
        self,
        name_suffix: str,
        hapi_table: Type[Base],
        end_resource: Optional[int] = 1,
        max_admin_level: Optional[int] = 2,
        location_headers: Optional[List[str]] = None,
    ) -> None:
        log_name = name_suffix.replace("-", " ")
        pipeline = []
        for part in name_suffix.split("-"):
            pipeline.append(part.capitalize())
        pipeline = " ".join(pipeline)
        logger.info(f"Populating {log_name} table")
        reader = Read.get_reader("hdx")
        dataset = reader.read_dataset(
            f"hdx-hapi-{name_suffix}", self._configuration
        )
        resources_to_ignore = []
        output_rows = []
        for resource in dataset.get_resources()[0:end_resource]:
            url = resource["url"]
            headers, rows = reader.get_tabular_rows(url, dict_form=True)
            hxltag_to_header = invert_dictionary(next(rows))

            for row in rows:
                if row.get("error"):
                    continue
                resource_id = row["resource_hdx_id"]
                if resource_id in resources_to_ignore:
                    continue
                dataset_id = row["dataset_hdx_id"]
                dataset_name = self._metadata.get_dataset_name(dataset_id)
                if dataset_name:
                    output_str = dataset_name
                else:
                    output_str = dataset_id

                if location_headers is None:
                    location_headers = ["location_code"]
                countryiso3 = row.get(location_headers[0])
                resource_name = self._metadata.get_resource_name(resource_id)
                if not resource_name:
                    dataset = reader.read_dataset(
                        dataset_id, self._configuration
                    )
                    found = False
                    for resource in dataset.get_resources():
                        if resource["id"] == resource_id:
                            if not dataset_name:
                                self._metadata.add_dataset(dataset)
                            self._metadata.add_resource(dataset_id, resource)
                            found = True
                            break
                    if not found:
                        self._error_handler.add_message(
                            pipeline,
                            dataset["name"],
                            f"resource {resource_id} does not exist in dataset for {countryiso3}",
                        )
                        resources_to_ignore.append(resource_id)
                        continue

                output_row = {
                    "resource_hdx_id": resource_id,
                    "reference_period_start": parse_date(
                        row["reference_period_start"]
                    ),
                    "reference_period_end": parse_date(
                        row["reference_period_end"], max_time=True
                    ),
                }
                if max_admin_level is not None:
                    admin_level = self._admins.get_admin_level_from_row(
                        hxltag_to_header, row, max_admin_level
                    )
                    if max_admin_level == 2:
                        admin2_ref = self._admins.get_admin2_ref_from_row(
                            hxltag_to_header,
                            row,
                            output_str,
                            pipeline,
                            admin_level,
                        )
                        output_row["admin2_ref"] = admin2_ref
                        output_row["provider_admin1_name"] = (
                            row["provider_admin1_name"] or ""
                        )
                        output_row["provider_admin2_name"] = (
                            row["provider_admin2_name"] or ""
                        )
                    elif max_admin_level == 1:
                        admin1_ref = self._admins.get_admin1_ref_from_row(
                            hxltag_to_header,
                            row,
                            output_str,
                            pipeline,
                            admin_level,
                        )
                        output_row["admin1_ref"] = admin1_ref
                        output_row["provider_admin1_name"] = (
                            row["provider_admin1_name"] or ""
                        )
                    elif max_admin_level == 0:
                        for location_header in location_headers:
                            countryiso3 = row[location_header]
                            output_header = location_header.replace(
                                "_code", "_ref"
                            )
                            location_ref = self._locations.data[countryiso3]
                            output_row[output_header] = location_ref

                self.populate_row(output_row, row)
                output_rows.append(output_row)
        logger.info(f"Writing to {log_name} table")
        self._database.batch_populate(output_rows, hapi_table)
