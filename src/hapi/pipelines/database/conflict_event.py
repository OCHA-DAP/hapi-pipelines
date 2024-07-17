"""Functions specific to the conflict event theme."""

from logging import getLogger
from typing import Dict

from hapi_schema.db_conflict_event import DBConflictEvent
from hapi_schema.utils.enums import EventType
from hdx.utilities.dateparse import parse_date_range
from sqlalchemy.orm import Session

from ..utilities.batch_populate import batch_populate
from ..utilities.logging_helpers import add_message
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
        config: Dict,
    ):
        super().__init__(session)
        self._metadata = metadata
        self._admins = admins
        self._results = results
        self._config = config

    def populate(self):
        logger.info("Populating conflict event table")
        errors = set()
        for dataset in self._results.values():
            dataset_name = dataset["hdx_stub"]
            conflict_event_rows = []
            number_duplicates = 0
            for admin_level, admin_results in dataset["results"].items():
                # TODO: this is only one resource id, but three resources are downloaded per dataset
                resource_id = admin_results["hapi_resource_metadata"]["hdx_id"]
                hxl_tags = admin_results["headers"][1]
                admin_codes = list(admin_results["values"][0].keys())
                values = admin_results["values"]

                for admin_code in admin_codes:
                    admin_rows = set()
                    admin2_code = admins.get_admin2_code_based_on_level(
                        admin_code=admin_code, admin_level=admin_level
                    )
                    for irow in range(len(values[0][admin_code])):
                        for et in EventType:
                            event_type = et.value
                            events = values[
                                hxl_tags.index(f"#event+num+{event_type}")
                            ][admin_code][irow]
                            fatalities = None
                            if f"#fatality+num+{event_type}" in hxl_tags:
                                fatalities = values[
                                    hxl_tags.index(
                                        f"#fatality+num+{event_type}"
                                    )
                                ][admin_code][irow]
                            month = values[
                                hxl_tags.index(f"#date+month+{event_type}")
                            ][admin_code][irow]
                            year = values[
                                hxl_tags.index(f"#date+year+{event_type}")
                            ][admin_code][irow]
                            time_period_range = parse_date_range(
                                f"{month} {year}", "%B %Y"
                            )
                            conflict_event_row = dict(
                                resource_hdx_id=resource_id,
                                admin2_ref=self._admins.admin2_data[
                                    admin2_code
                                ],
                                event_type=event_type,
                                events=events,
                                fatalities=fatalities,
                                reference_period_start=time_period_range[0],
                                reference_period_end=time_period_range[1],
                            )
                            conflict_event_tuple = tuple(
                                conflict_event_row.values()
                            )
                            if conflict_event_tuple in admin_rows:
                                number_duplicates += 1
                                continue
                            admin_rows.add(conflict_event_tuple)
                            conflict_event_rows.append(conflict_event_row)

            if number_duplicates > 0:
                add_message(
                    errors, dataset_name, f"{number_duplicates} duplicate rows"
                )
            if len(conflict_event_rows) == 0:
                add_message(errors, dataset_name, "no rows found")
                continue
            batch_populate(conflict_event_rows, self._session, DBConflictEvent)

        for dataset, msg in self._config.get(
            "conflict_event_error_messages", {}
        ).items():
            add_message(errors, dataset, msg)
        for error in sorted(errors):
            logger.error(error)
