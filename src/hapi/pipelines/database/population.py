"""Functions specific to the population theme."""

from logging import getLogger
from typing import Dict

from hapi_schema.db_population import DBPopulation

from .hapi_subcategory_uploader import HapiSubcategoryUploader

logger = getLogger(__name__)


class Population(HapiSubcategoryUploader):
    def populate_row(self, output_row: Dict, row: Dict) -> None:
        output_row["gender"] = row["gender"]
        output_row["age_range"] = row["age_range"]
        output_row["min_age"] = row["min_age"] and int(row["min_age"])
        output_row["max_age"] = row["max_age"] and int(row["max_age"])
        output_row["population"] = int(row["population"])

    def populate(self) -> None:
        self.hapi_populate(
            "population",
            DBPopulation,
            end_resource=None,
        )
