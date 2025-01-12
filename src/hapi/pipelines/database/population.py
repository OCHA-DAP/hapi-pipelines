"""Functions specific to the population theme."""

from logging import getLogger

from hapi_schema.db_population import DBPopulation
from hdx.api.configuration import Configuration
from hdx.api.utilities.hdx_error_handler import HDXErrorHandler
from hdx.scraper.framework.utilities.reader import Read
from hdx.utilities.dateparse import parse_date_range
from sqlalchemy.orm import Session

from ..utilities.batch_populate import batch_populate
from ..utilities.provider_admin_names import get_provider_name
from . import admins
from .base_uploader import BaseUploader
from .metadata import Metadata

logger = getLogger(__name__)


class Population(BaseUploader):
    def __init__(
        self,
        session: Session,
        metadata: Metadata,
        admins: admins.Admins,
        configuration: Configuration,
        error_handler: HDXErrorHandler,
    ):
        super().__init__(session)
        self._metadata = metadata
        self._admins = admins
        self._configuration = configuration
        self._error_handler = error_handler

    def get_admin2_ref(self, row, headers, dataset_name, admin_level):
        countryiso3 = row[headers.index("#country+code")]
        if admin_level == "national":
            admin_code = countryiso3
        if admin_level == "adminone":
            admin_code = row[headers.index("#adm1+code")]
        if admin_level == "admintwo":
            admin_code = row[headers.index("#adm2+code")]
        admin2_code = admins.get_admin2_code_based_on_level(
            admin_code=admin_code, admin_level=admin_level
        )
        admin2_ref = self._admins.admin2_data.get(admin2_code)
        if admin2_ref is None:
            if admin_level == "adminone":
                admin_code = admins.get_admin1_to_location_connector_code(
                    countryiso3
                )
            elif admin_level == "admintwo":
                admin_code = admins.get_admin2_to_location_connector_code(
                    countryiso3
                )
            else:
                return None
            admin2_ref = self._admins.get_admin2_ref(
                admin_level,
                admin_code,
                dataset_name,
                "Population",
                self._error_handler,
            )
        return admin2_ref

    def populate(self) -> None:
        logger.info("Populating population table")
        reader = Read.get_reader("hdx")
        dataset = reader.read_dataset("cod-ps-global", self._configuration)
        self._metadata.add_dataset(dataset)
        dataset_id = dataset["id"]
        dataset_name = dataset["name"]
        for resource in dataset.get_resources():
            resource_id = resource["id"]
            resource_name = resource["name"]
            admin_level = _get_admin_level(resource_name)
            if not admin_level:
                continue
            self._metadata.add_resource(dataset_id, resource)
            url = resource["url"]
            headers, rows = reader.get_tabular_rows(url, headers=2)
            population_rows = []
            for row in rows:
                admin2_ref = self.get_admin2_ref(
                    row, headers, dataset_name, admin_level
                )
                gender = row[headers.index("#gender")]
                age_range = row[headers.index("#age+range")]
                min_age = row[headers.index("#age+min")]
                max_age = row[headers.index("#age+max")]
                population = row[headers.index("#population")]
                reference_year = row[headers.index("#date+year")]
                time_period_range = parse_date_range(reference_year, "%Y")
                provider_admin1_name = get_provider_name(
                    row,
                    "#adm1+name",
                    headers,
                )
                provider_admin2_name = get_provider_name(
                    row,
                    "#adm2+name",
                    headers,
                )
                population_row = dict(
                    resource_hdx_id=resource_id,
                    admin2_ref=admin2_ref,
                    provider_admin1_name=provider_admin1_name,
                    provider_admin2_name=provider_admin2_name,
                    gender=gender,
                    age_range=age_range,
                    min_age=min_age,
                    max_age=max_age,
                    population=int(population),
                    reference_period_start=time_period_range[0],
                    reference_period_end=time_period_range[1],
                )
                population_rows.append(population_row)
            batch_populate(population_rows, self._session, DBPopulation)


def _get_admin_level(resource_name: str) -> str or None:
    admin_level = resource_name.split(".")[0][-1]
    if admin_level == "0":
        return "national"
    if admin_level == "1":
        return "adminone"
    if admin_level == "2":
        return "admintwo"
    return None
