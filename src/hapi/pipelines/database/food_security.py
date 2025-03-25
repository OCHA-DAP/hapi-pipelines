"""Functions specific to the food security theme."""

from logging import getLogger
from typing import Dict

from hapi_schema.db_food_security import DBFoodSecurity

from .hapi_dataset_uploader import HapiDatasetUploader

logger = getLogger(__name__)


class FoodSecurity(HapiDatasetUploader):
    def populate_row(self, output_row: Dict, row: Dict) -> None:
        output_row["ipc_phase"] = row["ipc_phase"]
        output_row["ipc_type"] = row["ipc_type"]
        output_row["population_in_phase"] = row["population_in_phase"]
        output_row["population_fraction_in_phase"] = row[
            "population_fraction_in_phase"
        ]

    def populate(self) -> None:
        self.hapi_populate(
            "food-security",
            DBFoodSecurity,
            end_resource=None,
        )
