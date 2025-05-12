"""Functions specific to the national risk theme."""

from logging import getLogger
from typing import Dict

from hapi_schema.db_national_risk import DBNationalRisk
from hdx.database import Database

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
        results: Dict,
    ):
        super().__init__(database)
        self._metadata = metadata
        self._locations = locations
        self._results = results

    def populate(self) -> None:
        logger.info("Populating national risk table")
        for dataset in self._results.values():
            time_period_start = dataset["time_period"]["start"]
            time_period_end = dataset["time_period"]["end"]
            for admin_level, admin_results in dataset["results"].items():
                resource_id = admin_results["hapi_resource_metadata"]["hdx_id"]
                hxl_tags = admin_results["headers"][1]
                admin_codes = list(admin_results["values"][0].keys())
                values = admin_results["values"]

                for admin_code in admin_codes:
                    risk_class = values[hxl_tags.index("#risk+class")].get(admin_code)
                    if risk_class:
                        risk_class = _get_risk_class_code_from_data(risk_class)

                    national_risk_row = DBNationalRisk(
                        resource_hdx_id=resource_id,
                        location_ref=self._locations.data[admin_code],
                        risk_class=risk_class,
                        global_rank=values[hxl_tags.index("#risk+rank")].get(
                            admin_code
                        ),
                        overall_risk=values[hxl_tags.index("#risk+total")].get(
                            admin_code
                        ),
                        hazard_exposure_risk=values[hxl_tags.index("#risk+hazard")].get(
                            admin_code
                        ),
                        vulnerability_risk=values[
                            hxl_tags.index("#risk+vulnerability")
                        ].get(admin_code),
                        coping_capacity_risk=values[
                            hxl_tags.index("#risk+coping+capacity")
                        ].get(admin_code),
                        meta_missing_indicators_pct=values[
                            hxl_tags.index("#meta+missing+indicators+pct")
                        ].get(admin_code),
                        meta_avg_recentness_years=values[
                            hxl_tags.index("#meta+recentness+avg")
                        ].get(admin_code),
                        reference_period_start=time_period_start,
                        reference_period_end=time_period_end,
                    )

                    self._session.add(national_risk_row)
        self._session.commit()


def _get_risk_class_code_from_data(risk_class: str) -> int:
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
