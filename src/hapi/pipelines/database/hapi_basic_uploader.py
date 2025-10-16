from abc import ABC
from logging import getLogger
from typing import Dict, Optional, Type

from hapi_schema.utils.base import Base
from hdx.api.configuration import Configuration
from hdx.api.utilities.hdx_error_handler import HDXErrorHandler
from hdx.database import Database
from hdx.scraper.framework.utilities.reader import Read

from hapi.pipelines.database.base_uploader import BaseUploader

logger = getLogger(__name__)


class HapiBasicUploader(BaseUploader, ABC):
    def __init__(
        self,
        database: Database,
        configuration: Configuration,
        key: str,
        error_handler: HDXErrorHandler,
    ):
        super().__init__(database)
        self._configuration = configuration
        self._datasetinfo = self._configuration[key]
        self._name = self._datasetinfo.get("name", key)
        self._error_handler = error_handler
        dataset_suffix = self._datasetinfo["dataset_suffix"]
        self._dataset_name = f"hdx-hapi-{dataset_suffix}"

    def get_row(self, row: Dict) -> Optional[Dict]:
        return row

    def hapi_populate(
        self,
        hapi_table: Type[Base],
    ) -> None:
        logger.info(f"Populating {self._name} table")
        reader = Read.get_reader("hdx")
        dataset = reader.read_dataset(self._dataset_name, self._configuration)
        resource = None
        resource_name = self._datasetinfo["resource"]
        for resource in dataset.get_resources():
            if resource["name"] == resource_name:
                break
        if not resource:
            self._error_handler.add_message(
                self._name, self._dataset_name, f"{resource_name} not found"
            )
            return

        url = resource["url"]
        headers, rows = reader.get_tabular_rows(url, dict_form=True)
        output_rows = []
        for row in rows:
            output_row = self.get_row(row)
            if output_row:
                output_rows.append(output_row)
        logger.info(f"Writing to {self._name} table")
        self._database.batch_populate(output_rows, hapi_table)
