"""Functions specific to the conflict event theme."""

from logging import getLogger
from typing import Dict

from hapi_schema.db_conflict_event import DBConflictEvent
from hapi_schema.utils.enums import EventType
from hdx.api.configuration import Configuration
from hdx.api.utilities.hdx_error_handler import HDXErrorHandler
from hdx.utilities.dateparse import parse_date_range
from sqlalchemy.orm import Session

from ..utilities.batch_populate import batch_populate
from ..utilities.provider_admin_names import get_provider_name
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
        configuration: Configuration,
        error_handler: HDXErrorHandler,
    ):
        super().__init__(session)
        self._metadata = metadata
        self._admins = admins
        self._results = results
        self._configuration = configuration
        self._error_handler = error_handler

    def populate(self) -> None:
        logger.info("Populating conflict event table")
        for dataset in self._results.values():
            dataset_name = dataset["hdx_stub"]
            conflict_event_rows = []
            number_duplicates = 0
            for admin_level, admin_results in dataset["results"].items():
                # TODO: this is only one resource id, but three resources are downloaded per dataset at admintwo
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
                            events = None
                            if f"#event+num+{event_type}" in hxl_tags:
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
                            if events is None and fatalities is None:
                                continue
                            month = values[
                                hxl_tags.index(f"#date+month+{event_type}")
                            ][admin_code][irow]
                            year = values[
                                hxl_tags.index(f"#date+year+{event_type}")
                            ][admin_code][irow]
                            time_period_range = parse_date_range(
                                f"{month} {year}", "%B %Y"
                            )
                            provider_admin1_name = get_provider_name(
                                values,
                                f"#adm1+name+{event_type}",
                                hxl_tags,
                                admin_code,
                                irow,
                            )
                            provider_admin2_name = get_provider_name(
                                values,
                                f"#adm2+name+{event_type}",
                                hxl_tags,
                                admin_code,
                                irow,
                            )
                            conflict_event_row = dict(
                                resource_hdx_id=resource_id,
                                admin2_ref=self._admins.admin2_data[
                                    admin2_code
                                ],
                                provider_admin1_name=provider_admin1_name,
                                provider_admin2_name=provider_admin2_name,
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
                self._error_handler.add_message(
                    "ConflictEvent",
                    dataset_name,
                    f"{number_duplicates} duplicate rows",
                )
            if len(conflict_event_rows) == 0:
                self._error_handler.add_message(
                    "ConflictEvent", dataset_name, "no rows found"
                )
                continue
            batch_populate(conflict_event_rows, self._session, DBConflictEvent)

        for identifier, message in self._configuration.get(
            "conflict_event_error_messages", {}
        ).items():
            dataset, resource_name = identifier.split("|")
            self._error_handler.add_message(
                "ConfictEvent",
                dataset,
                message,
                resource_name=resource_name,
                err_to_hdx=True,
            )
