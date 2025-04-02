"""Functions specific to the returnees theme."""

from logging import getLogger
from typing import Dict

from hapi_schema.db_returnees import DBReturnees

from .hapi_subcategory_uploader import HapiSubcategoryUploader

logger = getLogger(__name__)


class Returnees(HapiSubcategoryUploader):
    def populate_row(self, output_row: Dict, row: Dict) -> None:
        output_row["population_group"] = row["population_group"]
        output_row["gender"] = row["gender"]
        output_row["age_range"] = row["age_range"]
        output_row["min_age"] = row["min_age"] and int(row["min_age"])
        output_row["max_age"] = row["max_age"] and int(row["max_age"])
        output_row["population"] = row["population"]

    def populate(self) -> None:
        self.hapi_populate(
            "returnees",
            DBReturnees,
            max_admin_level=0,
            location_headers=["origin_location_code", "asylum_location_code"],
        )
