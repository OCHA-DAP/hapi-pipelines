import logging
from datetime import datetime
from typing import Dict, Optional

from hapi_schema.db_dataset import DBDataset
from hapi_schema.db_resource import DBResource
from hdx.data.dataset import Dataset
from hdx.data.resource import Resource
from hdx.database import Database
from hdx.scraper.framework.runner import Runner
from hdx.scraper.framework.utilities.reader import Read

from .base_uploader import BaseUploader

logger = logging.getLogger(__name__)


class Metadata(BaseUploader):
    def __init__(self, runner: Runner, database: Database, today: datetime) -> None:
        super().__init__(database)
        self._runner = runner
        self._today = today
        self._dataset_id_to_name = {}
        self._resource_id_to_name = {}

    def populate(self) -> None:
        logger.info("Populating metadata")
        datasets = self._runner.get_hapi_metadata()
        for dataset_id, dataset in datasets.items():
            # First add dataset

            # Make sure dataset hasn't already been added - hapi_metadata
            # contains duplicate datasets since it contains
            # dataset-resource pairs
            if dataset_id in self._dataset_id_to_name:
                continue
            dataset_name = dataset["hdx_stub"]
            dataset_row = DBDataset(
                hdx_id=dataset_id,
                hdx_stub=dataset_name,
                title=dataset["title"],
                hdx_provider_stub=dataset["hdx_provider_stub"],
                hdx_provider_name=dataset["hdx_provider_name"],
            )
            self._session.add(dataset_row)
            self._session.commit()
            self._dataset_id_to_name[dataset_id] = dataset_name

            resources = dataset["resources"]
            for resource_id, resource in resources.items():
                resource_name = resource["name"]
                # Then add the resources
                resource_row = DBResource(
                    hdx_id=resource_id,
                    dataset_hdx_id=dataset_row.hdx_id,
                    name=resource_name,
                    format=resource["format"],
                    update_date=resource["update_date"],
                    is_hxl=resource["is_hxl"],
                    download_url=resource["download_url"],
                    hapi_updated_date=self._today,
                )
                self._session.add(resource_row)
                self._session.commit()
                self._resource_id_to_name[resource_id] = resource_name

    def add_hapi_dataset_metadata(self, hapi_dataset_metadata: Dict) -> str:
        dataset_id = hapi_dataset_metadata["hdx_id"]
        dataset_name = hapi_dataset_metadata["hdx_stub"]
        dataset_row = DBDataset(
            hdx_id=dataset_id,
            hdx_stub=hapi_dataset_metadata["hdx_stub"],
            title=hapi_dataset_metadata["title"],
            hdx_provider_stub=hapi_dataset_metadata["hdx_provider_stub"],
            hdx_provider_name=hapi_dataset_metadata["hdx_provider_name"],
        )
        self._session.add(dataset_row)

        self._dataset_id_to_name[dataset_id] = dataset_name
        return dataset_id

    def add_hapi_resource_metadata(
        self, dataset_id: str, hapi_resource_metadata: Dict
    ) -> None:
        resource_id = hapi_resource_metadata["hdx_id"]
        resource_name = hapi_resource_metadata["name"]
        hapi_resource_metadata["dataset_hdx_id"] = dataset_id
        hapi_resource_metadata["is_hxl"] = True
        hapi_resource_metadata["hapi_updated_date"] = self._today

        resource_row = DBResource(**hapi_resource_metadata)
        self._resource_id_to_name[resource_id] = resource_name
        self._session.add(resource_row)

    def add_hapi_metadata(
        self, hapi_dataset_metadata: Dict, hapi_resource_metadata: Dict
    ) -> None:
        dataset_id = self.add_hapi_dataset_metadata(hapi_dataset_metadata)
        self.add_hapi_resource_metadata(dataset_id, hapi_resource_metadata)
        self._session.commit()

    def get_hapi_dataset_metadata(self, dataset: Dataset) -> Dict:
        time_period = dataset.get_time_period()
        hapi_time_period = {
            "time_period": {
                "start": time_period["startdate"],
                "end": time_period["enddate"],
            }
        }
        return Read.get_hapi_dataset_metadata(dataset, hapi_time_period)

    def add_dataset(self, dataset: Dataset) -> None:
        hapi_dataset_metadata = self.get_hapi_dataset_metadata(dataset)
        self.add_hapi_dataset_metadata(hapi_dataset_metadata)

    def add_resource(self, dataset_id: str, resource: Resource) -> None:
        hapi_resource_metadata = Read.get_hapi_resource_metadata(resource)
        self.add_hapi_resource_metadata(dataset_id, hapi_resource_metadata)

    def add_dataset_first_resource(self, dataset: Dataset) -> None:
        hapi_dataset_metadata = self.get_hapi_dataset_metadata(dataset)
        hapi_resource_metadata = Read.get_hapi_resource_metadata(dataset.get_resource())
        self.add_hapi_metadata(hapi_dataset_metadata, hapi_resource_metadata)

    def get_dataset_name(self, dataset_id: str) -> Optional[str]:
        return self._dataset_id_to_name.get(dataset_id)

    def get_resource_name(self, resource_id: str) -> Optional[str]:
        return self._resource_id_to_name.get(resource_id)
