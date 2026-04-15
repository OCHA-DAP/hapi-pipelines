import logging
from datetime import datetime
from typing import Dict, Optional

from hapi_schema.db_dataset import DBDataset
from hapi_schema.db_resource import DBResource
from hdx.data.dataset import Dataset
from hdx.data.resource import Resource
from hdx.database import Database
from hdx.scraper.framework.utilities.reader import Read

logger = logging.getLogger(__name__)


class Metadata:
    def __init__(self, database: Database, today: datetime) -> None:
        self._today = today
        self._dataset_id_to_name = {}
        self._resource_id_to_name = {}
        self._session = database.get_session()

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
        hapi_resource_metadata["is_hxl"] = False
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
