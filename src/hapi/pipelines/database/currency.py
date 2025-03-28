"""Functions specific to the WFP food prices theme for currencies."""

from logging import getLogger
from typing import Dict

from hapi_schema.db_currency import DBCurrency
from hdx.database import Database
from hdx.scraper.framework.utilities.reader import Read

from .base_uploader import BaseUploader

logger = getLogger(__name__)


class Currency(BaseUploader):
    def __init__(
        self,
        database: Database,
        datasetinfo: Dict[str, str],
    ):
        super().__init__(database)
        self._datasetinfo = datasetinfo

    def populate(self) -> None:
        logger.info("Populating currency table")
        reader = Read.get_reader("hdx")
        headers, iterator = reader.read(datasetinfo=self._datasetinfo)
        next(iterator)  # ignore HXL hashtags
        for currency in iterator:
            code = currency["code"]
            name = currency["name"]
            if not name:
                logger.warning(f"Using {code} as name because name is empty!")
                name = code
            currency_row = DBCurrency(code=code, name=name)
            self._session.add(currency_row)
        self._session.commit()
