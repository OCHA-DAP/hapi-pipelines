"""Functions specific to the conflict event theme."""

from logging import getLogger
from typing import Dict

from hapi_schema.db_conflict_event import DBConflictEvent
from hdx.utilities.dateparse import parse_date_range
from sqlalchemy.orm import Session

from . import admins
from .base_uploader import BaseUploader
from .metadata import Metadata

logger = getLogger(__name__)


class ConflictEvent(BaseUploader):
    def __init__(
        self,
        session: Session,
        metadata: Metadata,
        admins: admins.Admins,
        results: Dict,
    ):
        super().__init__(session)
        self._metadata = metadata
        self._admins = admins
        self._results = results

    def populate(self):
        logger.info("Populating conflict event table")
        for dataset in self._results.values():
            for admin_level, admin_results in dataset["results"].items():
                resource_id = admin_results["hapi_resource_metadata"]["hdx_id"]
                resource_name = admin_results["hapi_resource_metadata"]["name"]
                hxl_tags = admin_results["headers"][1]
                admin_codes = list(admin_results["values"][0].keys())
                values = admin_results["values"]

                event_types = [
                    "political_violence",
                    "civilian_targeting",
                    "demonstration",
                ]
                event_type = [et for et in event_types if et in resource_name]
                if len(event_type) != 1:
                    logger.error(
                        f"Missing conflict event type for resource {resource_name}"
                    )
                    continue
                event_type = event_type[0]

                for admin_code in admin_codes:
                    admin2_code = admins.get_admin2_code_based_on_level(
                        admin_code=admin_code, admin_level=admin_level
                    )
                    events = values[hxl_tags.index("#event+num")].get(
                        admin_code
                    )
                    fatalities = None
                    if "#fatalities+num" in hxl_tags:
                        fatalities = values[
                            hxl_tags.index("#fatalities+num")
                        ].get(admin_code)
                    month = values[hxl_tags.index("#date+month")].get(
                        admin_code
                    )
                    year = values[hxl_tags.index("#date+year")].get(admin_code)
                    time_period_range = parse_date_range(
                        f"{month} {year}", "%B %Y"
                    )
                    conflict_event_row = DBConflictEvent(
                        resource_hdx_id=resource_id,
                        admin2_ref=self._admins.admin2_data[admin2_code],
                        event_type=event_type,
                        events=events,
                        fatalities=fatalities,
                        reference_period_start=time_period_range[0],
                        reference_period_end=time_period_range[1],
                    )
                    self._session.add(conflict_event_row)

            self._session.commit()
