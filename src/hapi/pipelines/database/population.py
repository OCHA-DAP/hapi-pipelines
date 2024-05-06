"""Functions specific to the population theme."""

import re
from logging import getLogger
from typing import Dict

from hapi_schema.db_population import DBPopulation
from sqlalchemy.orm import Session

from . import admins
from .age_range import AgeRange
from .base_uploader import BaseUploader
from .gender import Gender
from .metadata import Metadata

logger = getLogger(__name__)

_HXL_PATTERN = re.compile(
    r"^#population(\+[a-z])*(\+age_(\d+_\d+|\d+_plus))*(\+total)?$"
)


class Population(BaseUploader):
    def __init__(
        self,
        session: Session,
        metadata: Metadata,
        admins: admins.Admins,
        gender: Gender,
        age_range: AgeRange,
        results: Dict,
    ):
        super().__init__(session)
        self._metadata = metadata
        self._admins = admins
        self._gender = gender
        self._age_range = age_range
        self._results = results

    def populate(self):
        logger.info("Populating population table")
        for dataset in self._results.values():
            time_period_start = dataset["time_period"]["start"]
            time_period_end = dataset["time_period"]["end"]

            for admin_level, admin_results in dataset["results"].items():
                resource_id = admin_results["hapi_resource_metadata"]["hdx_id"]
                for hxl_tag, values in zip(
                    admin_results["headers"][1], admin_results["values"]
                ):
                    if not _validate_hxl_tag(hxl_tag):
                        raise ValueError(
                            f"HXL tag {hxl_tag} not in valid format"
                        )
                    gender_code, age_range_code = _get_hxl_mapping(
                        hxl_tag=hxl_tag
                    )
                    if (
                        gender_code is not None
                        and gender_code not in self._gender.data
                    ):
                        raise ValueError(
                            f"Gender code {gender_code} not in table"
                        )
                    if (
                        age_range_code is not None
                        and age_range_code not in self._age_range.data
                    ):
                        raise ValueError(
                            f"Age range code {age_range_code} not in table"
                        )
                    for admin_code, value in values.items():
                        admin2_code = admins.get_admin2_code_based_on_level(
                            admin_code=admin_code, admin_level=admin_level
                        )
                        population_row = DBPopulation(
                            resource_hdx_id=resource_id,
                            admin2_ref=self._admins.admin2_data[admin2_code],
                            gender_code=gender_code,
                            age_range_code=age_range_code,
                            population=int(value),
                            reference_period_start=time_period_start,
                            reference_period_end=time_period_end,
                            # TODO: For v2+, add to scraper (HAPI-199)
                            source_data="not yet implemented",
                        )

                        self._session.add(population_row)
        self._session.commit()


def _validate_hxl_tag(hxl_tag: str) -> bool:
    """Validate HXL tags

    Assume they have the form:
        #population+total
        #population+f+total
        #population+age_5_12+total
        #population+age_80_plus+total
        #population+f+age_5_12
        #population+f+age_80_plus
    """
    # TODO: add tests for this (HAPI-159)
    return bool(_HXL_PATTERN.match(hxl_tag))


def _get_hxl_mapping(hxl_tag: str) -> (str, str):
    components = hxl_tag.split("+")
    gender_code = None
    age_range_code = None
    for component in components[1:]:
        # components can only be age, gender, or the word "total"
        if component.startswith("age_"):
            age_component = component[4:]
            if age_component.endswith("_plus"):
                age_range_code = age_component[:-5] + "+"
            else:
                age_range_code = age_component.replace("_", "-")
        elif component != "total":
            gender_code = component
    return gender_code, age_range_code
