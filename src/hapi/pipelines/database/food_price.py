"""Populate the WFP market table."""

from logging import getLogger
from typing import Dict, List

from dateutil.relativedelta import relativedelta
from hapi_schema.db_food_price import DBFoodPrice
from hdx.scraper.utilities.reader import Read
from hdx.utilities.dateparse import parse_date
from sqlalchemy.orm import Session

from ..utilities.logging_helpers import add_missing_value_message
from .base_uploader import BaseUploader
from .currency import Currency
from .metadata import Metadata
from .wfp_commodity import WFPCommodity
from .wfp_market import WFPMarket

logger = getLogger(__name__)


class FoodPrice(BaseUploader):
    def __init__(
        self,
        session: Session,
        datasetinfo: Dict[str, str],
        countryiso3s: List[str],
        metadata: Metadata,
        currency: Currency,
        commodity: WFPCommodity,
        market: WFPMarket,
    ):
        super().__init__(session)
        self._datasetinfo = datasetinfo
        self._countryiso3s = countryiso3s
        self._metadata = metadata
        self._currency = currency
        self._commodity = commodity
        self._market = market

    def populate(self) -> None:
        logger.info("Populating WFP price table")
        reader = Read.get_reader("hdx")
        headers, country_iterator = reader.read(datasetinfo=self._datasetinfo)
        datasetinfos = []
        for country in country_iterator:
            countryiso3 = country["countryiso3"]
            if countryiso3 not in self._countryiso3s:
                continue
            dataset_name = country["url"].split("/")[-1]
            datasetinfos.append(
                {
                    "dataset": dataset_name,
                    "format": "csv",
                    "admin_single": countryiso3,
                }
            )
        warnings = set()
        errors = set()
        for datasetinfo in datasetinfos:
            headers, iterator = reader.read(datasetinfo)
            hapi_dataset_metadata = datasetinfo["hapi_dataset_metadata"]
            hapi_resource_metadata = datasetinfo["hapi_resource_metadata"]
            self._metadata.add_hapi_metadata(
                hapi_dataset_metadata, hapi_resource_metadata
            )
            countryiso3 = datasetinfo["admin_single"]
            dataset_name = hapi_dataset_metadata["hdx_stub"]
            resource_id = hapi_resource_metadata["hdx_id"]
            next(iterator)  # ignore HXL hashtags
            for row in iterator:
                market = row["market"]
                market_code = self._market.get_market_code(countryiso3, market)
                if not market_code:
                    add_missing_value_message(
                        errors, dataset_name, "market code", market
                    )
                    continue
                commodity_code = self._commodity.get_commodity_code(
                    row["commodity"]
                )
                currency_code = row["currency"]
                unit = row["unit"]
                price_flag = row["priceflag"]
                price_type = row["pricetype"]
                price = row["price"]
                reference_period_start = parse_date(
                    row["date"], date_format="%Y-%m-%d"
                )
                reference_period_end = reference_period_start + relativedelta(
                    months=1,
                    days=-1,
                    hours=23,
                    minutes=59,
                    seconds=59,
                    microseconds=999999,
                )  # food price reference period is one month
                price_row = DBFoodPrice(
                    resource_hdx_id=resource_id,
                    market_code=market_code,
                    commodity_code=commodity_code,
                    currency_code=currency_code,
                    unit=unit,
                    price_flag=price_flag,
                    price_type=price_type,
                    price=price,
                    reference_period_start=reference_period_start,
                    reference_period_end=reference_period_end,
                )
                self._session.add(price_row)
            self._session.commit()
        for warning in sorted(warnings):
            logger.warning(warning)
        for error in sorted(errors):
            logger.error(error)
