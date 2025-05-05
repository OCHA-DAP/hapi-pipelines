"""Functions specific to the WFP food prices theme."""

from logging import getLogger
from typing import Dict

from hapi_schema.db_food_price import DBFoodPrice

from .hapi_subcategory_uploader import HapiSubcategoryUploader

logger = getLogger(__name__)


class FoodPrice(HapiSubcategoryUploader):
    def populate_row(self, output_row: Dict, row: Dict) -> None:
        output_row["market_code"] = row["market_code"]
        output_row["commodity_code"] = row["commodity_code"]
        output_row["currency_code"] = row["currency_code"]
        output_row["unit"] = row["unit"]
        output_row["price_flag"] = row["price_flag"]
        output_row["price_type"] = row["price_type"]
        output_row["price"] = row["price"]

    def populate(self) -> None:
        self.hapi_populate(
            "food-price",
            DBFoodPrice,
            end_resource=None,
            resource_name_match="Food Prices",
            max_admin_level=None,
        )
