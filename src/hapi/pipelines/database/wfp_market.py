"""Populate the WFP market table."""

from logging import getLogger
from typing import Dict, List, Optional

from hapi_schema.db_wfp_market import DBWFPMarket
from hdx.api.configuration import Configuration
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
        configuration: Configuration,
    ):
        super().__init__(session)
        self._datasetinfo = datasetinfo
        self._countryiso3s = countryiso3s
        self._admins = admins
        self._adminone = adminone
        self._admintwo = admintwo
        self.data = {}
        self.name_to_code = {}
        self._configuration = configuration

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
            admin_level = "admintwo"
            name = market["market"]
            adm1_name = market["admin1"]
            adm2_name = market["admin2"]
            if countryiso3 in self._configuration["unused_adm1"]:
                admin_level = "adminone"
                adm1_name = market["admin2"]
            if countryiso3 in self._configuration["adm1_only"]:
                admin_level = "adminone"
            if adm1_name is None:
                add_missing_value_message(
                    warnings, countryiso3, "admin 1 name for market", name
                )
                continue
            if countryiso3 in self._configuration["unused_adm2"]:
                adm1_code = None
                adm2_name = market["admin1"]
            else:
                adm1_code, _ = self._adminone.get_pcode(countryiso3, adm1_name)
            if adm1_code is None:
                add_missing_value_message(
                    warnings, countryiso3, "admin 1 code", adm1_name
                )
            if admin_level == "adminone":
                adm2_code = admins.get_admin2_code_based_on_level(
                    admin_code=adm1_code, admin_level=admin_level
                )
            if admin_level == "admintwo":
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
                if adm1_code is None:
                    # Map units that cannot be p-coded to national level
                    adm2_code = admins.get_admin2_code_based_on_level(
                        admin_code=countryiso3, admin_level="national"
                    )
                else:
                    # Map units that cannot be p-coded to adminone level
                    adm2_code = admins.get_admin2_code_based_on_level(
                        admin_code=adm1_code, admin_level="adminone"
                    )
            ref = self._admins.admin2_data.get(adm2_code)
            if ref is None:
                add_missing_value_message(
                    errors, identifier, "admin 2 ref", adm2_code
                )
                continue
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
