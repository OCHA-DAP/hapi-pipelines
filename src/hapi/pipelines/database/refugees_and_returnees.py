"""Functions specific to the refugees theme."""

from logging import getLogger
from typing import Dict

from hapi_schema.db_refugees import DBRefugees
from hapi_schema.db_returnees import DBReturnees
from hapi_schema.utils.enums import PopulationGroup
from hdx.utilities.dateparse import parse_date
from hdx.utilities.dictandlist import dict_of_lists_add
from sqlalchemy.orm import Session

from ..utilities.parse_tags import (
    get_gender_and_age_range,
    get_min_and_max_age,
)
from . import admins
from .base_uploader import BaseUploader
from .metadata import Metadata

logger = getLogger(__name__)


REFUGEE_POPULATION_GROUPS = [
    PopulationGroup.REFUGEES.value,
    PopulationGroup.ROC.value,
    PopulationGroup.ASYLUM_SEEKERS.value,
    PopulationGroup.OIP.value,
    PopulationGroup.IOC.value,
    PopulationGroup.STATELESS.value,
    PopulationGroup.OOC.value,
    PopulationGroup.HOST_COMMUNITY.value,
    PopulationGroup.RESETTLED.value,
    PopulationGroup.NATURALIZED.value,
]

RETURNEE_POPULATION_GROUPS = [
    PopulationGroup.RET.value,
    PopulationGroup.RDP.value,
    PopulationGroup.RRI.value,
]


class RefugeesAndReturnees(BaseUploader):
    def __init__(
        self,
        session: Session,
        metadata: Metadata,
        locations: admins.Locations,
        results: Dict,
    ):
        super().__init__(session)
        self._metadata = metadata
        self._locations = locations
        self._results = results

    def populate(self) -> None:
        logger.info("Populating refugees table")
        for dataset in self._results.values():
            for admin_level, admin_results in dataset["results"].items():
                resource_id = admin_results["hapi_resource_metadata"]["hdx_id"]
                results = admin_results["values"]
                hxl_tags = admin_results["headers"][1]
                date_i = hxl_tags.index("#date+year")
                asylum_location_i = hxl_tags.index("#country+code+asylum")
                population_group_i = hxl_tags.index(
                    "#indicator+population_type"
                )

                for hxl_index, hxl_tag in enumerate(hxl_tags):
                    if hxl_index in [
                        date_i,
                        asylum_location_i,
                        population_group_i,
                    ]:
                        continue
                    gender, age_range = get_gender_and_age_range(hxl_tag)
                    min_age, max_age = get_min_and_max_age(age_range)
                    rows = {}
                    for origin_location in results[hxl_index]:
                        values = results[hxl_index][origin_location]
                        for i, population in enumerate(values):
                            date = results[date_i][origin_location][i]
                            asylum_location = results[asylum_location_i][
                                origin_location
                            ][i]
                            population_group = results[population_group_i][
                                origin_location
                            ][i]
                            # Append the population in each row to a list to aggregate subnational locations
                            dict_of_lists_add(
                                rows,
                                (
                                    origin_location,
                                    asylum_location,
                                    population_group,
                                    date,
                                ),
                                int(population),
                            )
                    for key in rows:
                        population_group = key[2]
                        if population_group in REFUGEE_POPULATION_GROUPS:
                            db_table = DBRefugees
                        elif population_group in RETURNEE_POPULATION_GROUPS:
                            db_table = DBReturnees
                        else:
                            continue
                        refugees_and_returnees_row = db_table(
                            resource_hdx_id=resource_id,
                            origin_location_ref=self._locations.data[key[0]],
                            asylum_location_ref=self._locations.data[key[1]],
                            population_group=population_group,
                            gender=gender,
                            age_range=age_range,
                            min_age=min_age,
                            max_age=max_age,
                            population=sum(rows[key]),
                            reference_period_start=parse_date(
                                f"{key[3]}-01-01", "%Y-%m-%d"
                            ),
                            reference_period_end=parse_date(
                                f"{key[3]}-12-31", "%Y-%m-%d"
                            ),
                        )

                        self._session.add(refugees_and_returnees_row)
        self._session.commit()
