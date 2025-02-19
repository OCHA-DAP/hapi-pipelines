"""Functions specific to the humanitarian needs theme."""

from logging import getLogger
from typing import Dict

from hapi_schema.db_humanitarian_needs import DBHumanitarianNeeds

from hapi.pipelines.database.hapi_dataset_uploader import HapiDatasetUploader

logger = getLogger(__name__)


class HumanitarianNeeds(HapiDatasetUploader):
    def populate_row(self, output_row: Dict, row: Dict) -> None:
        output_row["category"] = row["category"] or ""
        output_row["sector_code"] = row["sector_code"]
        output_row["population_status"] = row["population_status"]
        output_row["population"] = row["population"]

    def populate(self) -> None:
        self.hapi_populate(
            "humanitarian-needs",
            DBHumanitarianNeeds,
            end_resource=None,
        )
