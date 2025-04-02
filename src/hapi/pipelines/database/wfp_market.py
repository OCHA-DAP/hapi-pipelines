"""Functions specific to the WFP food prices theme for markets."""

from logging import getLogger
from typing import Dict, Optional

from hapi_schema.db_wfp_market import DBWFPMarket
from hdx.api.configuration import Configuration
from hdx.api.utilities.hdx_error_handler import HDXErrorHandler
from hdx.database import Database

from hapi.pipelines.database import admins
from hapi.pipelines.database.hapi_basic_uploader import HapiBasicUploader

logger = getLogger(__name__)


class WFPMarket(HapiBasicUploader):
    def __init__(
        self,
        database: Database,
        admins: admins.Admins,
        configuration: Configuration,
        key: str,
        error_handler: HDXErrorHandler,
    ):
        super().__init__(database, configuration, key, error_handler)
        self._admins = admins

    def get_row(self, row: Dict) -> Optional[Dict]:
        if row.get("error"):
            return None
        admin_level = self._admins.get_admin_level_from_row(
            self._hxltag_to_header, row, 2
        )
        lat = row["lat"]
        if lat is not None:
            lat = float(lat)
        lon = row["lon"]
        if lon is not None:
            lon = float(lon)
        admin2_ref = self._admins.get_admin2_ref_from_row(
            self._hxltag_to_header,
            row,
            self._dataset_name,
            self._name,
            admin_level,
        )
        return {
            "code": row["market_code"],
            "name": row["market_name"],
            "lat": lat,
            "lon": lon,
            "admin2_ref": admin2_ref,
            "provider_admin1_name": row["provider_admin1_name"] or "",
            "provider_admin2_name": row["provider_admin2_name"] or "",
        }

    def populate(self) -> None:
        self.hapi_populate(DBWFPMarket)
