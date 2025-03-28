"""Functions specific to the WFP food prices theme for commodities."""

from logging import getLogger
from typing import Dict

from hapi_schema.db_wfp_commodity import DBWFPCommodity
from hapi_schema.utils.enums import CommodityCategory
from hdx.database import Database
from hdx.scraper.framework.utilities.reader import Read

from .base_uploader import BaseUploader

logger = getLogger(__name__)


class WFPCommodity(BaseUploader):
    def __init__(
        self,
        database: Database,
        datasetinfo: Dict[str, str],
    ):
        super().__init__(database)
        self._datasetinfo = datasetinfo

    def populate(self) -> None:
        logger.info("Populating WFP commodity table")
        reader = Read.get_reader("hdx")
        headers, iterator = reader.read(datasetinfo=self._datasetinfo)
        next(iterator)  # ignore HXL hashtags
        for commodity in iterator:
            code = commodity["commodity_id"]
            category = CommodityCategory(commodity["category"])
            name = commodity["commodity"]

            commodity_row = DBWFPCommodity(
                code=code, category=category, name=name
            )
            self._session.add(commodity_row)
        self._session.commit()
