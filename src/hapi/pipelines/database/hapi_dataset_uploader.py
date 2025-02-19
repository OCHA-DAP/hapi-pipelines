from abc import ABC
from logging import getLogger
from typing import Dict, Optional, Type

from hapi_schema.utils.base import Base
from hdx.api.configuration import Configuration
from hdx.api.utilities.hdx_error_handler import HDXErrorHandler
from hdx.scraper.framework.utilities.reader import Read
from hdx.utilities.dateparse import parse_date
from hdx.utilities.dictandlist import invert_dictionary
from sqlalchemy.orm import Session

from ..utilities.batch_populate import batch_populate
from . import admins
from hapi.pipelines.database.base_uploader import BaseUploader
from hapi.pipelines.database.metadata import Metadata

logger = getLogger(__name__)


class HapiDatasetUploader(BaseUploader, ABC):
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

    def populate_row(self, output_row: Dict, row: Dict) -> None:
        return

    def hapi_populate(
        self,
        name_suffix: str,
        hapi_table: Type[Base],
        end_resource: Optional[int] = 1,
    ):
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
                if row["error"]:
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
                admin_level = self._admins.get_admin_level_from_row(
                    hxltag_to_header, row, 2
                )
                admin2_ref = self._admins.get_admin2_ref_from_row(
                    hxltag_to_header,
                    row,
                    output_str,
                    pipeline,
                    admin_level,
                )

                countryiso3 = row["location_code"]
                provider_admin1_name = row["provider_admin1_name"] or ""
                provider_admin2_name = row["provider_admin2_name"] or ""

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
                    "admin2_ref": admin2_ref,
                    "provider_admin1_name": provider_admin1_name,
                    "provider_admin2_name": provider_admin2_name,
                    "reference_period_start": parse_date(
                        row["reference_period_start"]
                    ),
                    "reference_period_end": parse_date(
                        row["reference_period_end"], max_time=True
                    ),
                }
                self.populate_row(output_row, row)
                output_rows.append(output_row)
        logger.info(f"Writing to {log_name} table")
        batch_populate(output_rows, self._session, hapi_table)
