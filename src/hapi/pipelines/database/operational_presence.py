"""Functions specific to the operational presence theme."""

from logging import getLogger

from hapi_schema.db_operational_presence import DBOperationalPresence
from hdx.api.configuration import Configuration
from hdx.api.utilities.hdx_error_handler import HDXErrorHandler
from hdx.scraper.framework.utilities.reader import Read
from hdx.utilities.dateparse import parse_date
from hdx.utilities.dictandlist import invert_dictionary
from sqlalchemy.orm import Session

from ..utilities.batch_populate import batch_populate
from . import admins
from .base_uploader import BaseUploader
from .metadata import Metadata

logger = getLogger(__name__)


class OperationalPresence(BaseUploader):
    def __init__(
        self,
        session: Session,
        metadata: Metadata,
        admins: admins.Admins,
        configuration: Configuration,
        error_handler: HDXErrorHandler,
    ):
        super().__init__(session)
        self._metadata = metadata
        self._admins = admins
        self._configuration = configuration
        self._error_handler = error_handler

    def populate(self) -> None:
        logger.info("Populating operational presence table")
        reader = Read.get_reader("hdx")
        dataset = reader.read_dataset(
            "hdx-hapi-operational-presence", self._configuration
        )
        resource = dataset.get_resource()
        url = resource["url"]
        headers, rows = reader.get_tabular_rows(url, dict_form=True)
        hxltag_to_header = invert_dictionary(next(rows))
        resources_to_ignore = []
        operational_presence_rows = []

        for row in rows:
            if row["error"]:
                continue
            resource_id = row["resource_hdx_id"]
            if resource_id in resources_to_ignore:
                continue
            dataset_id = row["dataset_hdx_id"]
            dataset_name = self._metadata.get_dataset_name(dataset_id)
            if not dataset_name:
                dataset_name = dataset_id
            admin_level = self._admins.get_admin_level_from_row(
                hxltag_to_header, row, 2
            )
            admin2_ref = self._admins.get_admin2_ref_from_row(
                hxltag_to_header,
                row,
                dataset_name,
                "OperationalPresence",
                admin_level,
            )

            countryiso3 = row["location_code"]
            provider_admin1_name = row["provider_admin1_name"] or ""
            provider_admin2_name = row["provider_admin2_name"] or ""

            resource_name = self._metadata.get_resource_name(resource_id)
            if not resource_name:
                dataset = reader.read_dataset(dataset_id, self._configuration)
                found = False
                for resource in dataset.get_resources():
                    if resource["id"] == resource_id:
                        self._metadata.add_dataset(dataset)
                        self._metadata.add_resource(dataset_id, resource)
                        found = True
                        break
                if not found:
                    self._error_handler.add_message(
                        "OperationalPresence",
                        dataset["name"],
                        f"resource {resource_id} does not exist in dataset for {countryiso3}",
                    )
                    resources_to_ignore.append(resource_id)
                    continue

            operational_presence_row = {
                "resource_hdx_id": resource_id,
                "admin2_ref": admin2_ref,
                "provider_admin1_name": provider_admin1_name,
                "provider_admin2_name": provider_admin2_name,
                "org_acronym": row["org_acronym"],
                "org_name": row["org_name"],
                "sector_code": row["sector_code"],
                "reference_period_start": parse_date(
                    row["reference_period_start"]
                ),
                "reference_period_end": parse_date(
                    row["reference_period_end"], max_time=True
                ),
            }
            operational_presence_rows.append(operational_presence_row)
        logger.info("Writing to operational presence table")
        batch_populate(
            operational_presence_rows, self._session, DBOperationalPresence
        )
