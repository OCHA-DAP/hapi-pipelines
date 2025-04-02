"""Functions specific to the WFP food prices theme for currencies."""

from logging import getLogger
from typing import Dict, Optional

from hapi_schema.db_currency import DBCurrency

from hapi.pipelines.database.hapi_basic_uploader import HapiBasicUploader

logger = getLogger(__name__)


class Currency(HapiBasicUploader):
    def get_row(self, row: Dict) -> Optional[Dict]:
        if not row["name"]:
            row["name"] = ""
        return row

    def populate(self) -> None:
        self.hapi_populate(DBCurrency)
