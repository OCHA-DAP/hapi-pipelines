"""Functions specific to the WFP food prices theme."""

from logging import getLogger

from hapi_schema.db_food_price import DBFoodPrice
from hdx.api.configuration import Configuration
from hdx.api.utilities.hdx_error_handler import HDXErrorHandler
from hdx.database import Database
from hdx.scraper.framework.utilities.reader import Read
from hdx.utilities.dateparse import parse_date

from .metadata import Metadata
from hapi.pipelines.database.base_uploader import BaseUploader

logger = getLogger(__name__)


class FoodPrice(BaseUploader):
    def __init__(
        self,
        database: Database,
        metadata: Metadata,
        configuration: Configuration,
        error_handler: HDXErrorHandler,
    ):
        super().__init__(database)
        self._metadata = metadata
        self._configuration = configuration
        self._error_handler = error_handler
        self._data = {}

    def populate(self) -> None:
        datasetinfo = self._configuration["wfp_price"]
        log_name = datasetinfo["log_name"]
        pipeline = datasetinfo["pipeline"]
        logger.info(f"Populating {log_name} table")
        reader = Read.get_reader("hdx")
        dataset_name = datasetinfo["dataset"]
        dataset = reader.read_dataset(dataset_name, self._configuration)
        resource = None
        resource_name = datasetinfo["resource"]
        for resource in dataset.get_resources():
            if resource["name"] == resource_name:
                break
        if not resource:
            self._error_handler.add_message(
                "FoodPrice", dataset_name, f"{resource_name} not found"
            )
            return
        url = resource["url"]
        headers, rows = reader.get_tabular_rows(url, dict_form=True)

        output_rows = []
        resources_to_ignore = []
        for row in rows:
            if row.get("error"):
                continue

            resource_id = row["resource_hdx_id"]
            if resource_id in resources_to_ignore:
                continue
            dataset_id = row["dataset_hdx_id"]
            dataset_name = self._metadata.get_dataset_name(dataset_id)

            countryiso3 = row["location_code"]
            resource_name = self._metadata.get_resource_name(resource_id)
            if not resource_name:
                dataset = reader.read_dataset(dataset_id, self._configuration)
                found = False
                for resource in dataset.get_resources():
                    if resource["id"] == resource_id:
                        if not dataset_name:
                            self._metadata.add_dataset(dataset)
                        self._metadata.add_resource(dataset_id, resource)
                        found = True
                        break
                if not found:
                    self._error_handler.add_message(
                        pipeline,
                        dataset["name"],
                        f"resource {resource_id} does not exist in dataset for {countryiso3}",
                    )
                    resources_to_ignore.append(resource_id)
                    continue

            output_row = {
                "resource_hdx_id": resource_id,
                "market_code": row["market_code"],
                "commodity_code": row["commodity_code"],
                "currency_code": row["currency_code"],
                "unit": row["unit"],
                "price_flag": row["price_flag"],
                "price_type": row["price_type"],
                "price": row["price"],
                "reference_period_start": parse_date(
                    row["reference_period_start"]
                ),
                "reference_period_end": parse_date(
                    row["reference_period_end"], max_time=True
                ),
            }
            output_rows.append(output_row)
        logger.info(f"Writing to {log_name} table")
        self._database.batch_populate(output_rows, DBFoodPrice)
