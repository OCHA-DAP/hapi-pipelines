"""Populate the sector table."""

import logging

from hapi_schema.db_sector import DBSector
from hdx.scraper.framework.utilities.sector import Sector as SectorData
from sqlalchemy.orm import Session

from .base_uploader import BaseUploader

logger = logging.getLogger(__name__)


class Sector(BaseUploader, SectorData):
    def __init__(
        self,
        session: Session,
    ):
        BaseUploader.__init__(self, session)
        SectorData.__init__(self)

    def populate(self) -> None:
        logger.info("Populating sector table")
        for code, name in self._code_to_name.items():
            sector_row = DBSector(
                code=code,
                name=name,
            )
            self._session.add(sector_row)
        self._session.commit()
