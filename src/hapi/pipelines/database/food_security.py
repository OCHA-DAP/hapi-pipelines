"""Functions specific to the food security theme."""

from logging import getLogger

from hapi_schema.db_food_security import DBFoodSecurity
from hdx.api.configuration import Configuration
from hdx.location.adminlevel import AdminLevel
from hdx.scraper.utilities.reader import Read
from hdx.utilities.dateparse import parse_date
from sqlalchemy.orm import Session

from ..utilities.logging_helpers import add_missing_value_message, add_message
from . import admins
from .base_uploader import BaseUploader
from .metadata import Metadata

logger = getLogger(__name__)


class FoodSecurity(BaseUploader):
    def __init__(
        self,
        session: Session,
        metadata: Metadata,
        admins: admins.Admins,
        adminone: AdminLevel,
        admintwo: AdminLevel,
        configuration: Configuration,
    ):
        super().__init__(session)
        self._metadata = metadata
        self._admins = admins
        self._adminone = adminone
        self._admintwo = admintwo
        self._configuration = configuration

    def get_admin2_ref(self, admin_level, admin_code, dataset_name, errors):
        admin2_code = admins.get_admin2_code_based_on_level(
            admin_code=admin_code, admin_level=admin_level
        )
        ref = self._admins.admin2_data.get(admin2_code)
        if ref is None:
            add_missing_value_message(
                errors, dataset_name, "admin 2 code", admin2_code
            )
        return ref

    def populate(self) -> None:
        logger.info("Populating food security table")
        warnings = set()
        errors = set()
        reader = Read.get_reader("hdx")
        dataset = reader.read_dataset(
            "global-acute-food-insecurity-country-data", self._configuration
        )
        self._metadata.add_dataset(dataset)
        dataset_id = dataset["id"]
        dataset_name = dataset["name"]
        for resource in dataset.get_resources():
            resource_name = resource["name"]
            if "long_latest" not in resource_name:
                continue
            if "national" in resource_name:
                admin_level = "national"
            elif "level1" in resource_name:
                admin_level = "adminone"
            elif "area" in resource_name:
                admin_level = "admintwo"
            else:
                continue
            self._metadata.add_resource(dataset_id, resource)
            resource_id = resource["id"]
            url = resource["url"]
            headers, rows = reader.get_tabular_rows(url, dict_form=True)
            # Date of analysis,Country,Total country population,Level 1,Area,Validity period,From,To,Phase,Number,Percentage
            for row in rows:
                if "#" in row["Date of analysis"]:  # ignore HXL row
                    continue
                countryiso3 = row["Country"]
                if admin_level == "national":
                    admin2_ref = self.get_admin2_ref(
                        admin_level, countryiso3, dataset_name, errors
                    )
                else:
                    adminone_name = row["Level 1"]
                    subnational_level = admin_level
                    if not adminone_name and subnational_level == "admintwo":
                        subnational_level = "adminone"
                        adminone_name = row["Area"]
                    if adminone_name:
                        adminone, exact = self._adminone.get_pcode(
                            countryiso3, adminone_name
                        )
                    else:
                        continue
                    if subnational_level == "adminone":
                        if not adminone:
                            continue
                        if not exact:
                            name = self._adminone.pcode_to_name[adminone]
                            add_message(warnings, dataset_name, f"Admin 1: matching {adminone_name} to {name} {(adminone)}")
                        admin2_ref = self.get_admin2_ref(
                            subnational_level, adminone, dataset_name,
                            errors
                        )
                    elif subnational_level == "admintwo":
                        admintwo_name = row["Area"]
                        if any(x in admintwo_name.lower() for x in (" urban", " rural", "(1)", "(2)", "(3)", "(4)", "(5)", "_1", "_2", "idp")):
                            add_message(warnings, dataset_name,f"Admin 2: Ignoring {admintwo_name}")
                            continue
                        admintwo, exact = self._admintwo.get_pcode(
                            countryiso3, admintwo_name, parent=adminone
                        )
                        if not admintwo:
                            continue
                        if not exact:
                            name = self._admintwo.pcode_to_name[admintwo]
                            add_message(warnings, dataset_name, f"Admin 2: matching {admintwo_name} to {name} {(admintwo)}")
                        admin2_ref = self.get_admin2_ref(
                            subnational_level, admintwo, dataset_name, errors
                        )
                    else:
                        continue
                if not admin2_ref:
                    continue
                time_period_start = parse_date(row["From"])
                time_period_end = parse_date(row["To"])

                # food_security_row = DBFoodSecurity(
                #     resource_hdx_id=resource_id,
                #     admin2_ref=admin2_ref,
                #     ipc_phase=row["Phase"],
                #     ipc_type=row["Validity period"],
                #     reference_period_start=time_period_start,
                #     reference_period_end=time_period_end,
                #     population_in_phase=row["Number"],
                #     population_fraction_in_phase=row["Percentage"],
                # )
                # self._session.add(food_security_row)
                # self._session.commit()
        for warning in sorted(warnings):
            logger.warning(warning)
        for error in sorted(errors):
            logger.error(error)
