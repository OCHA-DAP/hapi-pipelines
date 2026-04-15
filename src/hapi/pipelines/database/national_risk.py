"""Functions specific to the national risk theme."""

from logging import getLogger
from typing import Dict, Optional

from hapi_schema.db_national_risk import DBNationalRisk
from hdx.api.configuration import Configuration
from hdx.database import Database
from hdx.scraper.framework.utilities.reader import Read

from . import locations
from .base_uploader import BaseUploader
from .metadata import Metadata

logger = getLogger(__name__)


class NationalRisk(BaseUploader):
    def __init__(
        self,
        database: Database,
        metadata: Metadata,
        locations: locations,
        configuration: Configuration,
    ):
        super().__init__(database)
        self._metadata = metadata
        self._locations = locations
        self._datasetinfo = configuration["national_risk"]

    def get_row(self, row: Dict, resource_id: str, time_period: Dict) -> Optional[Dict]:
        return {
            "resource_hdx_id": resource_id,
            "location_ref": self._locations.data[row["ISO3"]],
            "risk_class": self.get_risk_class_code_from_data(row["RISK CLASS"]),
            "global_rank": row["Rank"],
            "overall_risk": row["INFORM RISK"],
            "hazard_exposure_risk": row["HAZARD & EXPOSURE"],
            "vulnerability_risk": row["VULNERABILITY"],
            "coping_capacity_risk": row["LACK OF COPING CAPACITY"],
            "meta_missing_indicators_pct": row["% of Missing Indicators"],
            "meta_avg_recentness_years": row["Recentness data (average years)"],
            "reference_period_start": time_period["start"],
            "reference_period_end": time_period["end"],
        }

    def populate(self) -> None:
        reader = Read.get_reader("hdx")
        headers, iterator = reader.read(self._datasetinfo)
        hapi_dataset_metadata = self._datasetinfo["hapi_dataset_metadata"]
        time_period = hapi_dataset_metadata["time_period"]
        hapi_resource_metadata = self._datasetinfo["hapi_resource_metadata"]
        resource_id = hapi_resource_metadata["hdx_id"]
        resource_name = self._metadata.get_resource_name(resource_id)
        if not resource_name:
            self._metadata.add_hapi_metadata(
                hapi_dataset_metadata, hapi_resource_metadata
            )
        next(iterator)  # ignore filter row
        output_rows = []
        for row in iterator:
            output_rows.append(self.get_row(row, resource_id, time_period))
        logger.info("Writing to national_risk table")
        self._database.batch_populate(output_rows, DBNationalRisk)

    @staticmethod
    def get_risk_class_code_from_data(risk_class: str) -> int:
        risk_class = risk_class.lower()
        risk_class_code = None
        if risk_class == "very high":
            risk_class_code = "5"
        if risk_class == "high":
            risk_class_code = "4"
        if risk_class == "medium":
            risk_class_code = "3"
        if risk_class == "low":
            risk_class_code = "2"
        if risk_class == "very low":
            risk_class_code = "1"
        return risk_class_code
