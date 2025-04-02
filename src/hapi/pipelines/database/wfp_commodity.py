"""Functions specific to the WFP food prices theme for commodities."""

from logging import getLogger

from hapi_schema.db_wfp_commodity import DBWFPCommodity

from hapi.pipelines.database.hapi_basic_uploader import HapiBasicUploader

logger = getLogger(__name__)


class WFPCommodity(HapiBasicUploader):
    def populate(self) -> None:
        self.hapi_populate(DBWFPCommodity)
