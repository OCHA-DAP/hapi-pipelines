"""Functions specific to the funding theme."""

from datetime import date
from logging import getLogger
from typing import Dict

from sqlalchemy.orm import Session

from . import admins
from .admins import get_admin2_code_based_on_level
from .base_uploader import BaseUploader
from .metadata import Metadata

logger = getLogger(__name__)


class PovertyRate(BaseUploader):
    _CLASSIFICATION = ["poor", "vulnerable", "severe_poverty"]  # Use enum?

    def __init__(
        self,
        session: Session,
        metadata: Metadata,
        admins: admins.Admins,
        results: Dict,
        config: Dict,
    ):
        super().__init__(session)
        self._metadata = metadata
        self._admins = admins
        self._results = results
        self._config = config

    def populate(self):
        logger.info("Populating poverty rate table")
        # TODO reduce nesting
        # Loop through datasets (countries)
        for dataset in self._results.values():
            # There is only one admin level, so no need to loop, just take the national level for now,
            # and change after p-coding.
            admin_level = "national"
            admin_results = dataset["results"][admin_level]
            resource_id = admin_results["hapi_resource_metadata"]["hdx_id"]
            hxl_tags = admin_results["headers"][1]
            admin1_name_i = hxl_tags.index("#adm1+name")
            # values is a list of columns. Each column is a dictionary where the key is the admin code
            # and the value is a list of rows.
            values = admin_results["values"]
            # Since there's only one country per file, get the ISO3
            admin0_code = list(values[0].keys())[
                0
            ]  # There sound only be one key
            # Each row of the oxford dataset compares two timepoints. However, we want to
            # break up these timepoints to form a time series. The block below is getting the
            # column indices for the parameters of each timepoint.
            timepoint_indices = {}
            number_of_timepoints = self._config[
                f"poverty_rate_{admin0_code.lower()}"
            ]["number_of_timepoints"]
            # TODO: check if we can just hard code this
            for timepoint in range(number_of_timepoints):
                timepoint_indices[timepoint] = dict(
                    year=hxl_tags.index(f"#year+t{timepoint}"),
                    population_total_thousands=hxl_tags.index(
                        f"#population+total+t{timepoint}+thousands"
                    ),
                    affected_poor_thousands=hxl_tags.index(
                        f"#affected+poor+t{timepoint}+thousands"
                    ),
                    affected_vulnerable_thousands=hxl_tags.index(
                        f"#affected+vulnerable+t{timepoint}+thousands"
                    ),
                    affected_severe_poverty_thousands=hxl_tags.index(
                        f"#affected+severe_poverty+t{timepoint}+thousands"
                    ),
                )
            # Keep a running list of years because sometimes a t1 may already have been
            # covered in a t10
            from collections import defaultdict

            years_covered = defaultdict(set)
            # Get the admin ref for the DB
            admin2_code = get_admin2_code_based_on_level(
                admin_code=admin0_code, admin_level=admin_level
            )
            admin2_ref = self._admins.admin2_data[admin2_code]
            # TODO: add location ref
            for irow in range(len(values[0][admin0_code])):
                admin1_name = values[admin1_name_i][admin0_code][irow]
                for timepoint in range(number_of_timepoints):
                    indices = timepoint_indices[timepoint]
                    year = values[indices["year"]][admin0_code][irow]
                    if year in defaultdict[admin1_name]:
                        logger.info(f"Skipping duplicate year {year}")
                        continue
                    years_covered[admin1_name].add(year)
                    reference_period_start, reference_period_end = (
                        _convert_year_to_reference_period(year=year)
                    )
                    population_total_thousands = values[
                        indices["population_total_thousands"]
                    ][admin0_code][irow]
                    for classification in self._CLASSIFICATION:
                        affected_thousands = values[
                            indices[f"affected_{classification}_thousands"]
                        ][admin0_code][irow]
                        db_row = dict(
                            resource_hdx_id=resource_id,
                            admin1_name=admin1_name,
                            admin2_ref=admin2_ref,
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
