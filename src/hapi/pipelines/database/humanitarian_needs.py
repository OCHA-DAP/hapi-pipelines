"""Functions specific to the humanitarian needs theme."""

from logging import getLogger
from typing import Dict

from hapi_schema.db_humanitarian_needs import DBHumanitarianNeeds
from hxl.model import Column, TagPattern
from sqlalchemy.orm import Session

from . import admins
from .age_range import AgeRange
from .base_uploader import BaseUploader
from .gender import Gender
from .metadata import Metadata
from .population_group import PopulationGroup
from .population_status import PopulationStatus
from .sector import Sector

logger = getLogger(__name__)


class HumanitarianNeeds(BaseUploader):
    def __init__(
        self,
        session: Session,
        metadata: Metadata,
        admins: admins.Admins,
        population_status: PopulationStatus,
        population_group: PopulationGroup,
        sector: Sector,
        gender: Gender,
        age_range: AgeRange,
        results: Dict,
    ):
        super().__init__(session)
        self._metadata = metadata
        self._admins = admins
        self.population_status_pattern_to_code = (
            population_status.pattern_to_code
        )
        self.population_group_pattern_to_code = (
            population_group.pattern_to_code
        )
        self.sector_pattern_to_code = sector.pattern_to_code
        self.gender_pattern_to_code = gender.pattern_to_code
        self.age_range_pattern_to_code = age_range.pattern_to_code
        self.disabled_pattern = TagPattern.parse("#*+disabled")
        self._results = results

    def populate(self):
        logger.info("Populating humanitarian needs table")

        def match_column(col, pattern_to_code):
            for pattern in pattern_to_code:
                if pattern.match(col):
                    return pattern_to_code[pattern]
            return None

        for dataset in self._results.values():
            time_period_start = dataset["time_period"]["start"]
            time_period_end = dataset["time_period"]["end"]

            for admin_level, admin_results in dataset["results"].items():
                resource_id = admin_results["hapi_resource_metadata"]["hdx_id"]
                for hxl_tag, values in zip(
                    admin_results["headers"][1], admin_results["values"]
                ):
                    column = Column.parse(hxl_tag)
                    # "#inneed" "#affected"
                    population_status_code = match_column(
                        column, self.population_status_pattern_to_code
                    )
                    if not population_status_code:
                        raise ValueError(f"Invalid HXL tag {hxl_tag}!")
                    # "#*+idps" "#*+refugees"
                    population_group_code = match_column(
                        column, self.population_group_pattern_to_code
                    )
                    # "#*+wsh" "#*+pro_gbv"
                    sector_code = match_column(
                        column, self.sector_pattern_to_code
                    )
                    if sector_code:
                        sector_code = sector_code.upper()
                    # "#*+f" "#*+m"
                    gender_code = match_column(
                        column, self.gender_pattern_to_code
                    )
                    # "#*+age0_4" "#*+age80plus"
                    age_range_code = match_column(
                        column, self.age_range_pattern_to_code
                    )
                    # "#*+disabled"
                    disabled_marker = self.disabled_pattern.match(column)
                    if not disabled_marker:
                        disabled_marker = None  # no disabled attribute
                    # TODO: Will there be columns for able bodied?
                    for admin_code, value in values.items():
                        try:
                            value = int(value)
                        except (ValueError, TypeError):
                            continue
                        admin2_code = admins.get_admin2_code_based_on_level(
                            admin_code=admin_code, admin_level=admin_level
                        )
                        humanitarian_needs_row = DBHumanitarianNeeds(
                            resource_hdx_id=resource_id,
                            admin2_ref=self._admins.admin2_data[admin2_code],
                            population_status_code=population_status_code,
                            population_group_code=population_group_code,
                            sector_code=sector_code,
                            gender_code=gender_code,
                            age_range_code=age_range_code,
                            disabled_marker=disabled_marker,
                            population=value,
                            reference_period_start=time_period_start,
                            reference_period_end=time_period_end,
                            # TODO: For v2+, add to scraper (HAPI-199)
                            source_data="not yet implemented",
                        )

                        self._session.add(humanitarian_needs_row)
        self._session.commit()
