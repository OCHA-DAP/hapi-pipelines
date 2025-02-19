"""Functions specific to the operational presence theme."""

from logging import getLogger
from typing import Dict

from hapi_schema.db_operational_presence import DBOperationalPresence

from .hapi_dataset_uploader import HapiDatasetUploader

logger = getLogger(__name__)


class OperationalPresence(HapiDatasetUploader):
    def populate_row(self, output_row: Dict, row: Dict) -> None:
        output_row["org_acronym"] = row["org_acronym"]
        output_row["org_name"] = row["org_name"]
        output_row["sector_code"] = row["sector_code"]

    def populate(self) -> None:
        self.hapi_populate(
            "operational-presence",
            DBOperationalPresence,
        )
