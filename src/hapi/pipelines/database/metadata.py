import logging
from datetime import datetime
from typing import Dict

from hapi_schema.db_dataset import DBDataset
from hapi_schema.db_resource import DBResource
from hdx.data.dataset import Dataset
from hdx.data.resource import Resource
from hdx.scraper.framework.runner import Runner
from hdx.scraper.framework.utilities.reader import Read
from sqlalchemy.orm import Session

from .base_uploader import BaseUploader

logger = logging.getLogger(__name__)


class Metadata(BaseUploader):
    def __init__(
        self, runner: Runner, session: Session, today: datetime
    ) -> None:
        super().__init__(session)
        self.runner = runner
        self.today = today
        self.dataset_data = []

    def populate(self) -> None:
        logger.info("Populating metadata")
        datasets = self.runner.get_hapi_metadata()
        for dataset_id, dataset in datasets.items():
            # First add dataset

            # Make sure dataset hasn't already been added - hapi_metadata
            # contains duplicate datasets since it contains
            # dataset-resource pairs
            if dataset_id in self.dataset_data:
                continue
            dataset_row = DBDataset(
                hdx_id=dataset_id,
                hdx_stub=dataset["hdx_stub"],
                title=dataset["title"],
                hdx_provider_stub=dataset["hdx_provider_stub"],
                hdx_provider_name=dataset["hdx_provider_name"],
            )
            self._session.add(dataset_row)
            self._session.commit()
            self.dataset_data.append(dataset_id)

            resources = dataset["resources"]
            for resource_id, resource in resources.items():
                # Then add the resources
                resource_row = DBResource(
                    hdx_id=resource_id,
                    dataset_hdx_id=dataset_row.hdx_id,
                    name=resource["name"],
                    format=resource["format"],
                    update_date=resource["update_date"],
                    is_hxl=resource["is_hxl"],
                    download_url=resource["download_url"],
                    hapi_updated_date=self.today,
                )
                self._session.add(resource_row)
                self._session.commit()

    def add_hapi_dataset_metadata(self, hapi_dataset_metadata: Dict) -> str:
        dataset_id = hapi_dataset_metadata["hdx_id"]
        dataset_row = DBDataset(
            hdx_id=dataset_id,
            hdx_stub=hapi_dataset_metadata["hdx_stub"],
            title=hapi_dataset_metadata["title"],
            hdx_provider_stub=hapi_dataset_metadata["hdx_provider_stub"],
            hdx_provider_name=hapi_dataset_metadata["hdx_provider_name"],
        )
        self._session.add(dataset_row)

        self.dataset_data.append(dataset_id)
        return dataset_id

    def add_hapi_resource_metadata(
        self, dataset_id: str, hapi_resource_metadata: Dict
    ) -> None:
        hapi_resource_metadata["dataset_hdx_id"] = dataset_id
        hapi_resource_metadata["is_hxl"] = True
        hapi_resource_metadata["hapi_updated_date"] = self.today

        resource_row = DBResource(**hapi_resource_metadata)
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
        hapi_resource_metadata = Read.get_hapi_resource_metadata(
            dataset.get_resource()
        )
        self.add_hapi_metadata(hapi_dataset_metadata, hapi_resource_metadata)
