"""Functions specific to the humanitarian needs theme."""

from datetime import datetime
from logging import getLogger

from hapi_schema.db_humanitarian_needs import DBHumanitarianNeeds
from hdx.api.configuration import Configuration
from hdx.scraper.framework.utilities.reader import Read
from hdx.utilities.dictandlist import invert_dictionary
from hdx.utilities.text import get_numeric_if_possible
from sqlalchemy.orm import Session

from ..utilities.provider_admin_names import get_provider_name
from . import admins
from .base_uploader import BaseUploader
from .metadata import Metadata

logger = getLogger(__name__)


class HumanitarianNeeds(BaseUploader):
    def __init__(
        self,
        session: Session,
        metadata: Metadata,
        admins: admins.Admins,
        configuration: Configuration,
    ):
        super().__init__(session)
        self._metadata = metadata
        self._admins = admins
        self._configuration = configuration

    def populate(self) -> None:
        logger.info("Populating humanitarian needs table")
        reader = Read.get_reader("hdx")
        dataset = reader.read_dataset("global-hpc-hno", self._configuration)
        self._metadata.add_dataset(dataset)
        dataset_id = dataset["id"]
        dataset_name = dataset["name"]
        resources = dataset.get_resources()
        for resource in resources:
            self._metadata.add_resource(dataset_id, resource)
            resource_id = resource["id"]
            resource_name = resource["name"]
            year = int(resource_name[-4:])
            time_period_start = datetime(year, 1, 1)
            time_period_end = datetime(year, 12, 31, 23, 59, 59)
            url = resource["url"]
            headers, rows = reader.get_tabular_rows(url, dict_form=True)
            hxltag_to_header = invert_dictionary(next(rows))
            max_admin_level = self._admins.get_max_admin_from_hxltags(
                hxltag_to_header
            )
            # Admin 1 PCode,Admin 2 PCode,Sector,Gender,Age Group,Disabled,Population Group,Population,In Need,Targeted,Affected,Reached
            for row in rows:
                error = row.get("Error")
                if error:
                    continue
                admin_level = self._admins.get_admin_level_from_row(
                    hxltag_to_header, row, max_admin_level
                )
                # Can't handle higher admin levels
                if admin_level > 2:
                    continue
                admin2_ref = self._admins.get_admin2_ref_from_row(
                    hxltag_to_header,
                    row,
                    dataset_name,
                    "HumanitarianNeeds",
                    admin_level,
                )
                if not admin2_ref:
                    continue
                provider_admin1_name = get_provider_name(row, "Admin 1 Name")
                provider_admin2_name = get_provider_name(row, "Admin 2 Name")
                sector_code = row["Sector"]
                category = row["Category"]
                if category is None:
                    category = ""

                def create_row(in_col, population_status):
                    value = row[in_col]
                    if value is None:
                        return
                    value = get_numeric_if_possible(value)
                    humanitarian_needs_row = DBHumanitarianNeeds(
                        resource_hdx_id=resource_id,
                        admin2_ref=admin2_ref,
                        provider_admin1_name=provider_admin1_name,
                        provider_admin2_name=provider_admin2_name,
                        category=category,
                        sector_code=sector_code,
                        population_status=population_status,
                        population=value,
                        reference_period_start=time_period_start,
                        reference_period_end=time_period_end,
                    )
                    self._session.add(humanitarian_needs_row)

                create_row("Population", "all")
                create_row("Affected", "AFF")
                create_row("In Need", "INN")
                create_row("Targeted", "TGT")
                create_row("Reached", "REA")

            self._session.commit()
