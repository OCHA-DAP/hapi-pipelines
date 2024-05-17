"""Functions specific to the funding theme."""

from logging import getLogger
from typing import Dict

from sqlalchemy.orm import Session

from . import locations
from .base_uploader import BaseUploader
from .metadata import Metadata

logger = getLogger(__name__)


class PovertyRate(BaseUploader):
    def __init__(
        self,
        session: Session,
        metadata: Metadata,
        locations: locations,
        results: Dict,
    ):
        super().__init__(session)
        self._metadata = metadata
        self._locations = locations
        self._results = results

    def populate(self):
        logger.info("Populating poverty rate table")
        for dataset in self._results.values():
            print(dataset)
            for admin_level, admin_results in dataset["results"].items():
                # resource_id = admin_results["hapi_resource_metadata"]["hdx_id"]
                results = admin_results["values"]
                print(results)
