"""Functions specific to the WFP food prices theme for markets."""

from logging import getLogger

from hapi_schema.db_wfp_market import DBWFPMarket
from hdx.api.configuration import Configuration
from hdx.api.utilities.hdx_error_handler import HDXErrorHandler
from hdx.database import Database
from hdx.scraper.framework.utilities.reader import Read
from hdx.utilities.dictandlist import invert_dictionary

from . import admins
from hapi.pipelines.database.base_uploader import BaseUploader

logger = getLogger(__name__)


class WFPMarket(BaseUploader):
    def __init__(
        self,
        database: Database,
        admins: admins.Admins,
        configuration: Configuration,
        error_handler: HDXErrorHandler,
    ):
        super().__init__(database)
        self._admins = admins
        self._configuration = configuration
        self._error_handler = error_handler

    def populate(self) -> None:
        datasetinfo = self._configuration["wfp_market"]
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
                "FoodMarket", dataset_name, f"{resource_name} not found"
            )
            return
        url = resource["url"]
        headers, rows = reader.get_tabular_rows(url, dict_form=True)
        hxltag_to_header = invert_dictionary(next(rows))

        output_rows = []
        for row in rows:
            if row.get("error"):
                continue
            admin_level = self._admins.get_admin_level_from_row(
                hxltag_to_header, row, 2
            )
            lat = row["lat"]
            if lat is not None:
                lat = float(lat)
            lon = row["lon"]
            if lon is not None:
                lon = float(lon)
            output_row = {
                "code": row["market_code"],
                "name": row["market_name"],
                "lat": lat,
                "lon": lon,
            }
            admin2_ref = self._admins.get_admin2_ref_from_row(
                hxltag_to_header,
                row,
                dataset_name,
                pipeline,
                admin_level,
            )
            output_row["admin2_ref"] = admin2_ref
            output_row["provider_admin1_name"] = (
                row["provider_admin1_name"] or ""
            )
            output_row["provider_admin2_name"] = (
                row["provider_admin2_name"] or ""
            )
            output_rows.append(output_row)
        logger.info(f"Writing to {log_name} table")
        self._database.batch_populate(output_rows, DBWFPMarket)
