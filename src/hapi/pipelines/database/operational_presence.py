"""Functions specific to the operational presence theme."""

from logging import getLogger

from hapi_schema.db_operational_presence import DBOperationalPresence
from hdx.api.configuration import Configuration
from hdx.scraper.framework.utilities.reader import Read
from hdx.utilities.dateparse import parse_date
from sqlalchemy.orm import Session

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
    ):
        super().__init__(session)
        self._metadata = metadata
        self._admins = admins
        self._configuration = configuration

    def populate(self) -> None:
        logger.info("Populating operational presence table")
        reader = Read.get_reader("hdx")
        dataset = reader.read_dataset(
            "global-operational-presence", self._configuration
        )
        self._metadata.add_dataset(dataset)
        dataset_id = dataset["id"]
        dataset_name = dataset["name"]
        resource = dataset.get_resource()
        self._metadata.add_resource(dataset_id, resource)
        url = resource["url"]
        headers, rows = reader.get_tabular_rows(url, dict_form=True)
        resource_ids = self._metadata.get_resource_ids()
        # Country ISO3,Admin 1 PCode,Admin 1 Name,Admin 2 PCode,Admin 2 Name,Admin 3 PCode,Admin 3 Name,Org Name,Org Acronym,Org Type,Sector,Start Date,End Date,Resource Id
        for row in rows:
            admin2_ref = self._admins.get_admin2_ref_from_row(
                row, dataset_name, "OperationalPresence"
            )
            if not admin2_ref:
                continue
            provider_admin1_name = get_provider_name(row, "Admin 1 Name")
            provider_admin2_name = get_provider_name(row, "Admin 2 Name")

            resource_id = row["Resource Id"]
            if resource_id not in resource_ids:
                dataset_id = row["Dataset Id"]
                dataset = reader.read_dataset(
                    row["Dataset Id"], self._configuration
                )
                self._metadata.add_dataset(dataset)
                for resource in dataset.get_resources():
                    if resource["id"] == resource_id:
                        self._metadata.add_resource(dataset_id, resource)
                        break
            operational_presence_row = DBOperationalPresence(
                resource_hdx_id=row["Resource Id"],
                admin2_ref=admin2_ref,
                provider_admin1_name=provider_admin1_name,
                provider_admin2_name=provider_admin2_name,
                org_acronym=row["Org Acronym"],
                org_name=row["Org Name"],
                sector_code=row["Sector"],
                reference_period_start=parse_date(row["Start Date"]),
                reference_period_end=parse_date(
                    row["End Date"], max_time=True
                ),
            )
            self._session.add(operational_presence_row)
        self._session.commit()
