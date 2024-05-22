"""Functions specific to the funding theme."""

from collections import defaultdict
from datetime import date
from logging import getLogger
from typing import Dict

from sqlalchemy.orm import Session

from . import admins, locations
from .admins import get_admin1_code_based_on_level
from .base_uploader import BaseUploader
from .metadata import Metadata

logger = getLogger(__name__)


class PovertyRate(BaseUploader):
    _CLASSIFICATION = ["poor", "vulnerable", "severe_poverty"]  # Use enum?
    _DEFAULT_NUMBER_OF_TIMEPOINTS = 2

    def __init__(
        self,
        session: Session,
        metadata: Metadata,
        admins: admins.Admins,
        locations: locations,
        results: Dict,
        config: Dict,
    ):
        super().__init__(session)
        self._metadata = metadata
        # TODO: remove one of these
        self._admins = admins
        self._locations = locations
        self._results = results
        self._config = config

    def populate(self):
        logger.info("Populating poverty rate table")
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
            # There should only be one key in this list:
            admin0_code = list(values[0].keys())[0]
            # Each row of the oxford dataset compares two timepoints. However, we want to
            # break up these timepoints to form a time series. The block below is getting the
            # column indices for the parameters of each timepoint.
            timepoint_indices = {}
            number_of_timepoints = self._config[
                f"poverty_rate_{admin0_code.lower()}"
            ].get("number_of_timepoints", self._DEFAULT_NUMBER_OF_TIMEPOINTS)
            for timepoint in range(number_of_timepoints):
                timepoint_indices[timepoint] = dict(
                    multidimensional_poverty_index=hxl_tags.index(
                        f"#poverty+index+multidimensional+t{timepoint}"
                    ),
                    multidimensional_headcount_ratio=hxl_tags.index(
                        f"#poverty+headcount+ratio+t{timepoint}"
                    ),
                    intensity_of_poverty=hxl_tags.index(
                        f"#poverty+intensity+t{timepoint}"
                    ),
                    vulnerable_to_poverty=hxl_tags.index(
                        f"#poverty+vulnerable+t{timepoint}"
                    ),
                    in_severe_poverty=hxl_tags.index("#poverty+severe+t0"),
                )
            # Keep a running list of years because sometimes a t1 may already have been
            # covered in a t10
            # TODO: is this actually needed? Maybe can remove, DB would catch it if it comes up
            years_covered = defaultdict(set)
            # Get the admin ref for the DB
            admin1_code = get_admin1_code_based_on_level(
                admin_code=admin0_code, admin_level=admin_level
            )
            admin1_ref = self._admins.admin1_data[admin1_code]
            # TODO: see if we want to use admin1 ref or location ref
            for irow in range(len(values[0][admin0_code])):
                admin1_name = values[admin1_name_i][admin0_code][irow]
                for timepoint in range(number_of_timepoints):
                    year = values[hxl_tags.index(f"#year+t{timepoint}")][
                        admin0_code
                    ][irow]
                    if year in defaultdict[admin1_name]:
                        logger.info(f"Skipping duplicate year {year}")
                        continue
                    years_covered[admin1_name].add(year)
                    reference_period_start, reference_period_end = (
                        _convert_year_to_reference_period(year=year)
                    )
                    # row = DBPovertyRate(
                    row = dict(
                        resource_hdx_id=resource_id,
                        admin1_name=admin1_name,
                        admin1_ref=admin1_ref,
                        reference_period_start=reference_period_start,
                        reference_period_end=reference_period_end,
                        population_total=round(
                            values[
                                hxl_tags.index(
                                    f"#population+total+t{timepoint}+thousands"
                                )
                            ][admin0_code][irow]
                            * 1_000
                        ),
                        multidimensional_poverty_index=values[
                            hxl_tags.index(
                                f"#poverty+index+multidimensional+t{timepoint}"
                            )
                        ][admin0_code][irow],
                        multidimensional_headcount_ratio=values[
                            hxl_tags.index(
                                f"#poverty+headcount+ratio+t{timepoint}"
                            )
                        ][admin0_code][irow],
                        intensity_of_poverty=values[
                            hxl_tags.index(f"#poverty+intensity+t{timepoint}")
                        ][admin0_code][irow],
                        vulnerable_to_poverty=values[
                            hxl_tags.index(f"#poverty+vulnerable+t{timepoint}")
                        ][admin0_code][irow],
                        in_severe_poverty=values[
                            hxl_tags.index("#poverty+severe+t0")
                        ][admin0_code][irow],
                    )
                    print(row)
                    # self._session.add(row)
        # self._session.commit()


def _convert_year_to_reference_period(year: str) -> [date, date]:
    # The year column can either be a single year or a range split by a dash.
    # This function turns this into a reference period start and end date.
    try:
        start_year, end_year = year.split("-")
    except ValueError:
        start_year, end_year = year, year
    return date(int(start_year), 1, 1), date(int(end_year), 12, 31)
