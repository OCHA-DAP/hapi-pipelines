"""Functions specific to the funding theme."""

from collections import defaultdict
from datetime import date
from logging import getLogger
from typing import Dict

from hapi_schema.db_poverty_rate import DBPovertyRate
from sqlalchemy.orm import Session

from . import admins
from .admins import get_admin1_code_based_on_level
from .base_uploader import BaseUploader
from .metadata import Metadata

logger = getLogger(__name__)


class PovertyRate(BaseUploader):
    _DEFAULT_NUMBER_OF_TIMEPOINTS = 2

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

    def populate(self) -> None:
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
            # Get the admin ref for the DB
            admin1_code = get_admin1_code_based_on_level(
                admin_code=admin0_code, admin_level=admin_level
            )
            admin1_ref = self._admins.admin1_data[admin1_code]
            # In most datasets, each row compares two timepoints. We want to
            # break up these timepoints to form a time series.
            # First we get the number of timepoints, it defaults to 2, but some datasets have
            # 1 and this is specified in teh config file.
            number_of_timepoints = self._config[
                f"poverty_rate_{admin0_code.lower()}"
            ].get("number_of_timepoints", self._DEFAULT_NUMBER_OF_TIMEPOINTS)
            # We need to keep a running list of years because sometimes a t1 may already have been
            # covered in a t0
            years_covered = defaultdict(set)
            for irow in range(len(values[0][admin0_code])):
                admin1_name = values[admin1_name_i][admin0_code][irow]
                for timepoint in range(number_of_timepoints):
                    year = values[hxl_tags.index(f"#year+t{timepoint}")][
                        admin0_code
                    ][irow]
                    if year in years_covered[admin1_name]:
                        continue
                    years_covered[admin1_name].add(year)
                    reference_period_start, reference_period_end = (
                        _convert_year_to_reference_period(year=year)
                    )
                    row = DBPovertyRate(
                        resource_hdx_id=resource_id,
                        admin1_name=admin1_name,
                        admin1_ref=admin1_ref,
                        reference_period_start=reference_period_start,
                        reference_period_end=reference_period_end,
                        mpi=values[
                            hxl_tags.index(
                                f"#poverty+index+multidimensional+t{timepoint}"
                            )
                        ][admin0_code][irow],
                        headcount_ratio=values[
                            hxl_tags.index(
                                f"#poverty+headcount+ratio+t{timepoint}"
                            )
                        ][admin0_code][irow],
                        intensity_of_deprivation=values[
                            hxl_tags.index(f"#poverty+intensity+t{timepoint}")
                        ][admin0_code][irow],
                        vulnerable_to_poverty=values[
                            hxl_tags.index(f"#poverty+vulnerable+t{timepoint}")
                        ][admin0_code][irow],
                        in_severe_poverty=values[
                            hxl_tags.index("#poverty+severe+t0")
                        ][admin0_code][irow],
                    )
                    self._session.add(row)
        self._session.commit()


def _convert_year_to_reference_period(year: str) -> [date, date]:
    # The year column can either be a single year or a range split by a dash.
    # This function turns this into a reference period start and end date.
    try:
        start_year, end_year = year.split("-")
    except ValueError:
        start_year, end_year = year, year
    return date(int(start_year), 1, 1), date(int(end_year), 12, 31)
