"""Functions specific to the funding theme."""

from logging import getLogger

from hapi_schema.db_funding import DBFunding
from hdx.api.configuration import Configuration
from hdx.scraper.framework.utilities.reader import Read
from hdx.utilities.dateparse import parse_date
from sqlalchemy.orm import Session

from ..utilities.logging_helpers import add_message, add_missing_value_message
from . import locations
from .base_uploader import BaseUploader
from .metadata import Metadata

logger = getLogger(__name__)


class Funding(BaseUploader):
    def __init__(
        self,
        session: Session,
        metadata: Metadata,
        locations: locations,
        configuration: Configuration,
    ):
        super().__init__(session)
        self._metadata = metadata
        self._locations = locations
        self._configuration = configuration

    def populate(self) -> None:
        logger.info("Populating funding table")
        reader = Read.get_reader("hdx")
        datasets = reader.search_datasets(
            filename="fts_requirements_funding_*",
            fq="name:fts-requirements-and-funding-data-for-*",
            configuration=self._configuration,
        )
        funding_keys = []
        errors = set()
        for dataset in datasets:
            dataset_id = dataset["id"]
            dataset_name = dataset["name"]
            if dataset["archived"]:
                continue
            admin_code = dataset.get_location_iso3s()[0]
            resource = [
                r
                for r in dataset.get_resources()
                if r["name"]
                == f"fts_requirements_funding_{admin_code.lower()}.csv"
            ]
            if len(resource) != 1:
                continue
            resource = resource[0]
            resource_id = resource["id"]
            url = resource["url"]
            headers, rows = reader.get_tabular_rows(
                url,
                dict_form=True,
                headers=2,
            )
            if "#activity+appeal+type+name" not in headers:
                add_message(
                    errors,
                    dataset_name,
                    "appeal_type missing from dataset",
                )
                continue
            self._metadata.add_dataset(dataset)
            self._metadata.add_resource(dataset_id, resource)
            for row in rows:
                requirements_usd = row["#value+funding+required+usd"]
                if not requirements_usd:
                    continue
                appeal_name = row["#activity+appeal+name"]
                appeal_code = row["#activity+appeal+id+external"]
                if appeal_code is None:
                    add_message(
                        errors,
                        dataset_name,
                        f"Blank appeal_code for {appeal_name}",
                    )
                    continue

                appeal_type = row["#activity+appeal+type+name"]
                funding_usd = row["#value+funding+total+usd"]
                # This check for a missing funding line has been added due to
                # an error in the UKR funding requirements data
                if funding_usd is None:
                    add_missing_value_message(
                        errors,
                        dataset_name,
                        "funding_usd",
                        appeal_code,
                    )
                    continue
                funding_pct = row["#value+funding+pct"]
                reference_period_start = parse_date(row["#date+start"])
                reference_period_end = parse_date(row["#date+end"])

                if reference_period_start > reference_period_end:
                    add_message(
                        errors,
                        dataset_name,
                        f"Appeal start date occurs after end date for {appeal_code} in {admin_code}",
                    )
                    continue

                # Check for duplicates (these come up when countries are renamed in the FTS system)
                location_ref = self._locations.data[admin_code]
                funding_key = (
                    appeal_code,
                    location_ref,
                    reference_period_start,
                )
                if funding_key in funding_keys:
                    add_message(
                        errors,
                        dataset_name,
                        f"Duplicate location/appeal/time period for {appeal_code} in {admin_code}",
                    )
                    continue
                funding_keys.append(funding_key)

                funding_row = DBFunding(
                    resource_hdx_id=resource_id,
                    location_ref=location_ref,
                    appeal_code=appeal_code,
                    appeal_name=appeal_name,
                    appeal_type=appeal_type,
                    requirements_usd=requirements_usd,
                    funding_usd=funding_usd,
                    funding_pct=funding_pct,
                    reference_period_start=reference_period_start,
                    reference_period_end=reference_period_end,
                )

                self._session.add(funding_row)
        self._session.commit()
        for error in sorted(errors):
            logger.error(error)
