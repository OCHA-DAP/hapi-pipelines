"""Populate the org table."""

from logging import getLogger

from hapi_schema.db_org import DBOrg
from hdx.api.configuration import Configuration
from hdx.database import Database
from hdx.scraper.framework.utilities.reader import Read

from .base_uploader import BaseUploader
from .metadata import Metadata

logger = getLogger(__name__)


class Org(BaseUploader):
    def __init__(
        self,
        database: Database,
        metadata: Metadata,
        configuration: Configuration,
    ):
        super().__init__(database)
        self._metadata = metadata
        self._configuration = configuration

    def populate(self) -> None:
        logger.info("Populating org table")
        reader = Read.get_reader("hdx")
        dataset = reader.read_dataset("hdx-hapi-organisations", self._configuration)
        self._metadata.add_dataset(dataset)
        resource = dataset.get_resource()
        url = resource["url"]
        headers, rows = reader.get_tabular_rows(url, dict_form=True)
        # Acronym, Name, Org Type Code
        for row in rows:
            acronym = row["acronym"] or ""
            # Ignore HXL row
            if acronym == "#org+acronym":
                continue
            org_row = DBOrg(
                acronym=acronym,
                name=row["name"],
                org_type_code=row["org_type_code"],
            )
            self._session.add(org_row)
        self._session.commit()
