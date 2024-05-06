import logging
from datetime import datetime

from hapi_schema.db_dataset import DBDataset
from hapi_schema.db_resource import DBResource
from hdx.scraper.runner import Runner
from sqlalchemy.orm import Session

from .base_uploader import BaseUploader

logger = logging.getLogger(__name__)


class Metadata(BaseUploader):
    def __init__(self, runner: Runner, session: Session, today: datetime):
        super().__init__(session)
        self.runner = runner
        self.today = today
        self.dataset_data = []

    def populate(self):
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
