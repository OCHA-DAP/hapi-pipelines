"""Functions specific to the funding theme."""

from datetime import date
from logging import getLogger
from typing import Dict

from sqlalchemy.orm import Session

from . import locations
from .base_uploader import BaseUploader
from .metadata import Metadata

logger = getLogger(__name__)


class PovertyRate(BaseUploader):
    _TIMEPOINTS = ["t0", "t1"]
    _CLASSIFICATION = ["poor", "vulnerable", "severe_poverty"]  # Use enum?

    def __init__(
        self,
        session: Session,
        metadata: Metadata,
        locations: locations,
        results: Dict,
    ):
        super().__init__(session)
        self._metadata = metadata
        self._locations = locations
        self._results = results

    def populate(self):
        logger.info("Populating poverty rate table")
        # TODO reduce nesting
        for dataset in self._results.values():
            for admin_level, admin_results in dataset["results"].items():
                resource_id = admin_results["hapi_resource_metadata"]["hdx_id"]
                hxl_tags = admin_results["headers"][1]
                values = admin_results["values"]
                admin1_name_i = hxl_tags.index("#adm1+name")
                # Each row of the oxford dataset compares two timepoints. However, we want to
                # break up these timepoints to form a time series. The block below is getting the
                # column indices for the parameters of each timepoint.
                timepoint_indices = {}
                for timepoint in self._TIMEPOINTS:
                    timepoint_indices[timepoint] = dict(
                        year=hxl_tags.index(f"#year+{timepoint}"),
                        population_total_thousands=hxl_tags.index(
                            f"#population+total+{timepoint}+thousands"
                        ),
                        affected_poor_thousands=hxl_tags.index(
                            f"#affected+poor+{timepoint}+thousands"
                        ),
                        affected_vulnerable_thousands=hxl_tags.index(
                            f"#affected+vulnerable+{timepoint}+thousands"
                        ),
                        affected_severe_poverty_thousands=hxl_tags.index(
                            f"#affected+severe_poverty+{timepoint}+thousands"
                        ),
                    )
                # Keep a running list of years because sometimes a t1 may already have been
                # covered in a t10
                # years_considereed = []  # TODO: make this a default dict with admin1
                for admin_code in values[0].keys():
                    # TODO: add location ref
                    for irow in range(len(values[0][admin_code])):
                        admin1_name = values[admin1_name_i][admin_code][irow]
                        for timepoint in self._TIMEPOINTS:
                            indices = timepoint_indices[timepoint]
                            year = values[indices["year"]][admin_code][irow]
                            # if year in years_considereed:
                            #    print(f"Skipping duplicate year {year}")
                            #    continue
                            # years_considereed.append(year)
                            reference_period_start, reference_period_end = (
                                _convert_year_to_reference_period(year=year)
                            )
                            population_total_thousands = values[
                                indices["population_total_thousands"]
                            ][admin_code][irow]
                            for classification in self._CLASSIFICATION:
                                affected_thousands = values[
                                    indices[
                                        f"affected_{classification}_thousands"
                                    ]
                                ][admin_code][irow]
                                db_row = dict(
                                    resource_hdx_id=resource_id,
                                    admin1_name=admin1_name,
                                    classification=classification,
                                    population=round(
                                        population_total_thousands * 1_000
                                    ),
                                    affected=round(affected_thousands * 1_000),
                                    reference_period_start=reference_period_start,
                                    reference_period_end=reference_period_end,
                                )
                                print(db_row)


def _convert_year_to_reference_period(year: str) -> [date, date]:
    # The year column can either be a single year or a range split by a dash.
    # This function turns this into a reference period start and end date.
    try:
        start_year, end_year = year.split("-")
    except ValueError:
        start_year, end_year = year, year
    return date(int(start_year), 1, 1), date(int(end_year), 12, 31)
