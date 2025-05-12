from typing import Dict

from hapi_schema.db_poverty_rate import DBPovertyRate

from hapi.pipelines.database.hapi_subcategory_uploader import (
    HapiSubcategoryUploader,
)


class PovertyRate(HapiSubcategoryUploader):
    def populate_row(self, output_row: Dict, row: Dict) -> None:
        output_row["mpi"] = row["mpi"]
        output_row["headcount_ratio"] = row["headcount_ratio"]
        output_row["intensity_of_deprivation"] = row["intensity_of_deprivation"]
        output_row["vulnerable_to_poverty"] = row["vulnerable_to_poverty"]
        output_row["in_severe_poverty"] = row["in_severe_poverty"]

    def populate(self) -> None:
        self.hapi_populate("poverty-rate", DBPovertyRate, max_admin_level=1)
