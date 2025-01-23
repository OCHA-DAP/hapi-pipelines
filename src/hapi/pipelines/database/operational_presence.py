"""Functions specific to the operational presence theme."""

from logging import getLogger

from hapi_schema.db_operational_presence import DBOperationalPresence
from hdx.api.configuration import Configuration
from hdx.api.utilities.hdx_error_handler import HDXErrorHandler
from hdx.scraper.framework.utilities.reader import Read
from hdx.utilities.dateparse import parse_date
from sqlalchemy.orm import Session

from ..utilities.batch_populate import batch_populate
from ..utilities.provider_admin_names import get_provider_name
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
            "global-operational-presence", self._configuration
        )
        resource = dataset.get_resource()
        url = resource["url"]
        headers, rows = reader.get_tabular_rows(url, dict_form=True)
        max_admin_level = self._admins.get_max_admin_from_headers(headers)
        resources_to_ignore = []
        operational_presence_rows = []
        # Country ISO3,Admin 1 PCode,Admin 1 Name,Admin 2 PCode,Admin 2 Name,Admin 3 PCode,Admin 3 Name,Org Name,Org Acronym,Org Type,Sector,Start Date,End Date,Resource Id
        for row in rows:
            resource_id = row["Resource Id"]
            if resource_id in resources_to_ignore:
                continue
            countryiso3 = row["Country ISO3"]
            dataset_id = row["Dataset Id"]
            if dataset_id[0] == "#":
                continue
            dataset_name = self._metadata.get_dataset_name(dataset_id)
            if not dataset_name:
                dataset_name = dataset_id
            admin_level = self._admins.get_admin_level_from_row(
                row, max_admin_level
            )
            actual_admin_level = admin_level
            # Higher admin levels treat as admin 2
            if admin_level > 2:
                error_when_duplicate = False
                admin_level = 2
            else:
                error_when_duplicate = True
            admin2_ref = self._admins.get_admin2_ref_from_row(
                row, dataset_name, "OperationalPresence", admin_level
            )
            if not admin2_ref:
                continue
            provider_admin1_name = get_provider_name(row, "Admin 1 Name")
            provider_admin2_name = get_provider_name(row, "Admin 2 Name")

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

            resource_id = row["Resource Id"]
            operational_presence_row = {
                "resource_hdx_id": resource_id,
                "admin2_ref": admin2_ref,
                "provider_admin1_name": provider_admin1_name,
                "provider_admin2_name": provider_admin2_name,
                "org_acronym": row["Org Acronym"],
                "org_name": row["Org Name"],
                "sector_code": row["Sector"],
                "reference_period_start": parse_date(row["Start Date"]),
                "reference_period_end": parse_date(
                    row["End Date"], max_time=True
                ),
            }
            if operational_presence_row in operational_presence_rows:
                if error_when_duplicate:
                    self._error_handler.add_message(
                        "OperationalPresence",
                        dataset_name,
                        f"admin level {actual_admin_level} row {str(operational_presence_row)} is a duplicate in {countryiso3}",
                    )
                else:
                    self._error_handler.add_message(
                        "OperationalPresence",
                        dataset_name,
                        f"admin level {actual_admin_level} duplicate rows in {countryiso3}",
                        message_type="warning",
                    )
            else:
                operational_presence_rows.append(operational_presence_row)
        logger.info("Writing to operational presence table")
        batch_populate(
            operational_presence_rows, self._session, DBOperationalPresence
        )
