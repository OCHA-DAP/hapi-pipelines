"""Functions specific to the idps theme."""

from logging import getLogger
from typing import Dict

from hapi_schema.db_idps import DBIDPs

from .hapi_subcategory_uploader import HapiSubcategoryUploader

logger = getLogger(__name__)


class IDPs(HapiSubcategoryUploader):
    def populate_row(self, output_row: Dict, row: Dict) -> None:
        output_row["assessment_type"] = row["assessment_type"]
        output_row["reporting_round"] = row["reporting_round"]
        output_row["operation"] = row["operation"]
        output_row["population"] = row["population"]

    def populate(self) -> None:
        self.hapi_populate(
            "idps",
            DBIDPs,
        )
