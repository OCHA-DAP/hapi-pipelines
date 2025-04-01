"""Functions specific to the rainfall theme."""

from logging import getLogger
from typing import Dict

from hapi_schema.db_rainfall import DBRainfall

from .hapi_dataset_uploader import HapiDatasetUploader

logger = getLogger(__name__)


class Rainfall(HapiDatasetUploader):
    def populate_row(self, output_row: Dict, row: Dict) -> None:
        output_row["provider_admin1_code"] = row["provider_admin1_code"] or ""
        output_row["provider_admin2_code"] = row["provider_admin2_code"] or ""
        output_row["aggregation_period"] = row["aggregation_period"]
        output_row["rainfall"] = row["rainfall"]
        output_row["rainfall_long_term_average"] = row[
            "rainfall_long_term_average"
        ]
        output_row["rainfall_anomaly_pct"] = row["rainfall_anomaly_pct"]
        output_row["number_pixels"] = int(row["number_pixels"])
        output_row["version"] = row["version"]

    def populate(self) -> None:
        self.hapi_populate(
            "rainfall",
            DBRainfall,
            end_resource=None,
        )
