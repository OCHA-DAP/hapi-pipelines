"""Populate the currency table."""

from logging import getLogger

from hapi_schema.db_currency import DBCurrency
from hdx.api.configuration import Configuration
from hdx.scraper.utilities.reader import Read
from sqlalchemy.orm import Session

from .base_uploader import BaseUploader

logger = getLogger(__name__)


class Currency(BaseUploader):
    def __init__(
        self,
        configuration: Configuration,
        session: Session,
    ):
        super().__init__(session)
        self._configuration = configuration

    def populate(self) -> None:
        logger.info("Populating currencies table")
        reader = Read.get_reader("wfp_token")
        bearer_json = reader.download_json(
            self._configuration["wfp_token_url"],
            post=True,
            parameters={"grant_type": "client_credentials"},
        )
        bearer_token = bearer_json["access_token"]
        reader = Read.get_reader("wfp_databridges")
        reader.downloader.set_bearer_token(bearer_token)
        json = reader.download_json(self._configuration["wfp_currencies_url"])
        for currency in json["items"]:
            code = currency["name"]
            name = currency["extendedName"]
            if not name:
                logger.warning(f"Using {code} as name because name is empty!")
                name = code
            currency_row = DBCurrency(code=code, name=name)
            self._session.add(currency_row)
        self._session.commit()
