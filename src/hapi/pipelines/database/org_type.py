"""Populate the org type table."""

import logging

from hapi_schema.db_org_type import DBOrgType
from hdx.scraper.framework.utilities.org_type import OrgType as OrgTypeData
from sqlalchemy.orm import Session

from .base_uploader import BaseUploader

logger = logging.getLogger(__name__)


class OrgType(BaseUploader, OrgTypeData):
    def __init__(
        self,
        session: Session,
    ):
        BaseUploader.__init__(self, session)
        OrgTypeData.__init__(self)

    def populate(self) -> None:
        logger.info("Populating org type table")
        for code, description in self._code_to_name.items():
            sector_row = DBOrgType(
                code=code,
                description=description,
            )
            self._session.add(sector_row)
        self._session.commit()
