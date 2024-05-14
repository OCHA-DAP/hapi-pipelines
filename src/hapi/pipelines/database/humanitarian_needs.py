"""Functions specific to the humanitarian needs theme."""

from logging import getLogger
from typing import Dict

from hapi_schema.db_humanitarian_needs import DBHumanitarianNeeds
from hdx.api.configuration import Configuration
from hdx.data.dataset import Dataset
from hdx.scraper.utilities.reader import Read
from hdx.utilities.text import get_numeric_if_possible
from sqlalchemy.orm import Session

from . import admins
from .base_uploader import BaseUploader
from .metadata import Metadata
from .sector import Sector

logger = getLogger(__name__)


class HumanitarianNeeds(BaseUploader):
    def __init__(
        self,
        session: Session,
        metadata: Metadata,
        admins: admins.Admins,
        sector: Sector,
    ):
        super().__init__(session)
        self._metadata = metadata
        self._admins = admins
        self._sector = sector

    def get_admin2_ref(self, countryiso3, row):
        admin_code = row["Admin 2 PCode"]
        if admin_code == "#adm2+code":  # ignore HXL row
            return None
        if admin_code:
            admin_level = "admintwo"
        else:
            admin_code = row["Admin 1 PCode"]
            if admin_code:
                admin_level = "adminone"
            else:
                admin_code = countryiso3
                admin_level = "national"
        admin2_code = admins.get_admin2_code_based_on_level(
            admin_code=admin_code, admin_level=admin_level
        )
        return self._admins.admin2_data[admin2_code]

    def populate(self):
        logger.info("Populating humanitarian needs table")
        reader = Read.get_reader("hdx")
        configuration = Configuration(hdx_site="stage", hdx_read_only=True)
        configuration.setup_session_remoteckan()
        datasets = Dataset.search_in_hdx(fq="name:hno-data-for-*", configuration=configuration)
        for dataset in datasets:
            self._metadata.add_dataset(dataset)
            countryiso3 = dataset.get_location_iso3s()[0]
            time_period = dataset.get_time_period()
            time_period_start = time_period["startdate_str"],
            time_period_end = time_period["enddate_str"]
            resource = dataset.get_resource()
            resource_id = resource["id"]
            url = resource["url"]
            headers, rows = reader.get_tabular_rows(url, dict_form=True)
            # Admin 1 PCode,Admin 2 PCode,Sector,Gender,Age Group,Disabled,Population Group,Population,In Need,Targeted,Affected,Reached
            for row in rows:
                admin2_ref = self.get_admin2_ref(countryiso3, row)
                if not admin2_ref:
                    continue
                population_group = row["Population Group"]
                if population_group == "ALL":
                    population_group = "*"
                sector = row["Sector"]
                sector_code = self._sector.get_sector_code(sector)
                if not sector_code:
                    logger.warning(f"Sector {sector} not found!")
                    continue
                gender = row["Gender"]
                if gender == "a":
                    gender = "*"
                age_range = row["Age Range"]
                min_age = row["Min Age"]
                max_age = row["Max Age"]
                disabled_marker = row["Disabled"]
                if disabled_marker == "a":
                    disabled_marker = "*"

                def create_row(in_col, population_status):
                    value = row[in_col]
                    if value is None:
                        return
                    value = get_numeric_if_possible(value)
                    if value < 0:
                        logger.warning(f"Negative {population_status} {value}!")
                        return
                    if isinstance(value, float):
                        value = round(value)
                    humanitarian_needs_row = DBHumanitarianNeeds(
                        resource_hdx_id=resource_id,
                        admin2_ref=admin2_ref,
                        gender=gender,
                        age_range=age_range,
                        min_age=min_age,
                        max_age=max_age,
                        sector_code=sector_code,
                        population_group=population_group,
                        population_status=population_status,
                        disabled_marker=disabled_marker,
                        population=int(value),
                        reference_period_start=time_period_start,
                        reference_period_end=time_period_end,
                    )
                    self._session.add(humanitarian_needs_row)
                    self._session.commit()

                create_row("Population", "POP")
                create_row("Affected", "AFF")
                create_row("In Need", "INN")
                create_row("Targeted", "TGT")
                create_row("Reached", "REA")
