"""Populate the WFP market table."""

from logging import getLogger
from typing import Dict, List, Optional

from hapi_schema.db_wfp_market import DBWFPMarket
from hdx.location.adminlevel import AdminLevel
from hdx.scraper.utilities.reader import Read
from hdx.utilities.dictandlist import dict_of_dicts_add
from sqlalchemy.orm import Session

from ..utilities.logging_helpers import add_missing_value_message
from . import admins
from .base_uploader import BaseUploader

logger = getLogger(__name__)


class WFPMarket(BaseUploader):
    def __init__(
        self,
        session: Session,
        datasetinfo: Dict[str, str],
        countryiso3s: List[str],
        admins: admins.Admins,
        adminone: AdminLevel,
        admintwo: AdminLevel,
    ):
        super().__init__(session)
        self._datasetinfo = datasetinfo
        self._countryiso3s = countryiso3s
        self._admins = admins
        self._adminone = adminone
        self._admintwo = admintwo
        self.data = {}
        self.name_to_code = {}

    def populate(self) -> None:
        logger.info("Populating WFP market table")
        reader = Read.get_reader("hdx")
        headers, iterator = reader.read(datasetinfo=self._datasetinfo)
        warnings = set()
        errors = set()
        next(iterator)  # ignore HXL hashtags
        for market in iterator:
            countryiso3 = market["countryiso3"]
            if countryiso3 not in self._countryiso3s:
                continue
            name = market["market"]
            adm1_name = market["admin1"]
            if adm1_name is None:
                add_missing_value_message(
                    warnings, countryiso3, "admin 1 name for market", name
                )
                continue
            adm1_code, _ = self._adminone.get_pcode(countryiso3, adm1_name)
            if adm1_code is None:
                add_missing_value_message(
                    warnings, countryiso3, "admin 1 code", adm1_name
                )
            adm2_name = market["admin2"]
            adm2_code, _ = self._admintwo.get_pcode(
                countryiso3, adm2_name, parent=adm1_code
            )
            if adm1_code is None:
                identifier = f"{countryiso3}-{adm1_name}"
            else:
                identifier = f"{countryiso3}-{adm1_code}"
            if adm2_code is None:
                add_missing_value_message(
                    errors, identifier, "admin 2 code", adm2_name
                )
                continue
            ref = self._admins.admin2_data.get(adm2_code)
            if ref is None:
                add_missing_value_message(
                    errors, identifier, "admin 2 ref", adm2_code
                )
            code = market["market_id"]
            lat = market["latitude"]
            lon = market["longitude"]
            dict_of_dicts_add(self.name_to_code, countryiso3, name, code)
            self.data[code] = name
            market_row = DBWFPMarket(
                code=code, admin2_ref=ref, name=name, lat=lat, lon=lon
            )
            self._session.add(market_row)
        self._session.commit()
        for warning in sorted(warnings):
            logger.warning(warning)
        for error in sorted(errors):
            logger.error(error)

    def get_market_name(self, code: str) -> Optional[str]:
        return self.data.get(code)

    def get_market_code(self, countryiso3: str, market: str) -> Optional[str]:
        country_name_to_market = self.name_to_code.get(countryiso3)
        if not country_name_to_market:
            return None
        return country_name_to_market.get(market)
