"""Populate the org table."""

from logging import getLogger

from hapi_schema.db_org import DBOrg
from hdx.api.configuration import Configuration
from hdx.scraper.framework.utilities.reader import Read
from sqlalchemy.orm import Session

from .base_uploader import BaseUploader
from .metadata import Metadata

logger = getLogger(__name__)


class Org(BaseUploader):
    def __init__(
        self,
        session: Session,
        metadata: Metadata,
        configuration: Configuration,
    ):
        super().__init__(session)
        self._metadata = metadata
        self._configuration = configuration

    def populate(self) -> None:
        logger.info("Populating org table")
        reader = Read.get_reader("hdx")
        dataset = reader.read_dataset(
            "global-organisations", self._configuration
        )
        self._metadata.add_dataset(dataset)
        resource = dataset.get_resource()
        url = resource["url"]
        headers, rows = reader.get_tabular_rows(url, dict_form=True)
        # Acronym, Name, Org Type Code
        for row in rows:
            acronym = row["Acronym"]
            # Ignore HXL row
            if acronym == "#org+acronym":
                continue
            org_row = DBOrg(
                acronym=row["Acronym"],
                name=row["Name"],
                org_type_code=row["Org Type Code"],
            )
            self._session.add(org_row)
        self._session.commit()
