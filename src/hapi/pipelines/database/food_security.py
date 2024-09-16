"""Functions specific to the food security theme."""

from dataclasses import dataclass
from logging import getLogger
from typing import Dict, Optional, Set

from hapi_schema.db_food_security import DBFoodSecurity
from hdx.api.configuration import Configuration
from hdx.location.adminlevel import AdminLevel
from hdx.scraper.framework.utilities.reader import Read
from hdx.utilities.dateparse import parse_date
from hdx.utilities.typehint import ListTuple
from sqlalchemy.orm import Session

from ..utilities.logging_helpers import add_message
from . import admins
from .base_uploader import BaseUploader
from .metadata import Metadata

logger = getLogger(__name__)


@dataclass
class AdminInfo:
    countryiso3: str
    name: str
    fullname: str
    pcode: Optional[str]
    exact: bool


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

    @staticmethod
    def get_admin_level_from_resource_name(
        resource_name: str,
    ) -> Optional[str]:
        if "long_latest" not in resource_name:
            return None
        if "national" in resource_name:
            return "national"
        elif "level1" in resource_name:
            return "adminone"
        elif "area" in resource_name:
            return "admintwo"
        else:
            return None

    def get_adminoneinfo(
        self,
        adm_ignore_patterns: ListTuple,
        warnings: Set,
        dataset_name: str,
        countryiso3: str,
        adminone_name: str,
    ) -> Optional[AdminInfo]:
        full_adm1name = f"{countryiso3}|{adminone_name}"
        if any(x in adminone_name.lower() for x in adm_ignore_patterns):
            add_message(
                warnings,
                dataset_name,
                f"Admin 1: ignoring {full_adm1name}",
            )
            return None
        pcode, exact = self._adminone.get_pcode(countryiso3, adminone_name)
        return AdminInfo(
            countryiso3, adminone_name, full_adm1name, pcode, exact
        )

    def get_admintwoinfo(
        self,
        adm_ignore_patterns: ListTuple,
        warnings: Set,
        dataset_name: str,
        adminoneinfo: AdminInfo,
        admintwo_name: str,
    ) -> Optional[AdminInfo]:
        full_adm2name = (
            f"{adminoneinfo.countryiso3}|{adminoneinfo.name}|{admintwo_name}"
        )
        if any(x in admintwo_name.lower() for x in adm_ignore_patterns):
            add_message(
                warnings,
                dataset_name,
                f"Admin 2: ignoring {full_adm2name}",
            )
            return None
        pcode, exact = self._admintwo.get_pcode(
            adminoneinfo.countryiso3, admintwo_name, parent=adminoneinfo.pcode
        )
        return AdminInfo(
            adminoneinfo.countryiso3,
            admintwo_name,
            full_adm2name,
            pcode,
            exact,
        )

    def get_adminone_admin2_ref(
        self,
        food_sec_config: Dict,
        warnings: Set,
        errors: Set,
        dataset_name: str,
        adminoneinfo: AdminInfo,
    ) -> Optional[int]:
        if not adminoneinfo.pcode:
            add_message(
                warnings,
                dataset_name,
                f"Admin 1: could not match {adminoneinfo.fullname}!",
            )
            return None
        if not adminoneinfo.exact:
            name = self._adminone.pcode_to_name[adminoneinfo.pcode]
            if adminoneinfo.name in food_sec_config["adm1_errors"]:
                add_message(
                    errors,
                    dataset_name,
                    f"Admin 1: ignoring erroneous {adminoneinfo.fullname} match to {name} {(adminoneinfo.pcode)}!",
                )
                return None
            add_message(
                warnings,
                dataset_name,
                f"Admin 1: matching {adminoneinfo.fullname} to {name} {(adminoneinfo.pcode)}",
            )
        return self._admins.get_admin2_ref(
            "adminone", adminoneinfo.pcode, dataset_name, errors
        )

    def get_admintwo_admin2_ref(
        self,
        food_sec_config: Dict,
        warnings: Set,
        errors: Set,
        dataset_name: str,
        row: Dict,
        adminoneinfo: AdminInfo,
    ) -> Optional[int]:
        admintwo_name = row["Area"]
        if not admintwo_name:
            add_message(
                warnings,
                dataset_name,
                f"Admin 1: ignoring blank Area name in {adminoneinfo.countryiso3}|{adminoneinfo.name}",
            )
            return None
        admintwoinfo = self.get_admintwoinfo(
            food_sec_config["adm_ignore_patterns"],
            warnings,
            dataset_name,
            adminoneinfo,
            admintwo_name,
        )
        if not admintwoinfo:
            return None
        if not admintwoinfo.pcode:
            add_message(
                warnings,
                dataset_name,
                f"Admin 2: could not match {admintwoinfo.fullname}!",
            )
            return None
        if not admintwoinfo.exact:
            name = self._admintwo.pcode_to_name[admintwoinfo.pcode]
            if admintwo_name in food_sec_config["adm2_errors"]:
                add_message(
                    errors,
                    dataset_name,
                    f"Admin 2: ignoring erroneous {admintwoinfo.fullname} match to {name} {(admintwoinfo.pcode)}!",
                )
                return None
            add_message(
                warnings,
                dataset_name,
                f"Admin 2: matching {admintwoinfo.fullname} to {name} {(admintwoinfo.pcode)}",
            )
        return self._admins.get_admin2_ref(
            "admintwo", admintwoinfo.pcode, dataset_name, errors
        )

    def process_subnational(
        self,
        food_sec_config: Dict,
        warnings: Set,
        errors: Set,
        dataset_name: str,
        countryiso3: str,
        admin_level: str,
        row: Dict,
    ) -> Optional[int]:
        # Some countries only have data in the ipc_global_level1 file
        if (
            admin_level == "admintwo"
            and countryiso3 in food_sec_config["adm1_only"]
        ):
            return None
        # The YAML configuration "adm2_only" specifies locations where
        # "Level 1" is not populated and "Area" is admin 2. (These are
        # exceptions since "Level 1" would normally be populated if "Area" is
        # admin 2.)
        if countryiso3 in food_sec_config["adm2_only"]:
            # Some countries only have data in the ipc_global_area file
            if admin_level == "adminone":
                return None
            adminoneinfo = AdminInfo(countryiso3, "NOT GIVEN", "", None, False)
            return self.get_admintwo_admin2_ref(
                food_sec_config,
                warnings,
                errors,
                dataset_name,
                row,
                adminoneinfo,
            )

        adminone_name = row["Level 1"]

        if not adminone_name:
            if admin_level == "adminone":
                if not adminone_name:
                    add_message(
                        warnings,
                        dataset_name,
                        f"Admin 1: ignoring blank Level 1 name in {countryiso3}",
                    )
                    return None
            else:
                # "Level 1" and "Area" are used loosely, so admin 1 or admin 2 data can
                # be in "Area". Usually if "Level 1" is populated, "Area" is admin 2
                # and if it isn't, "Area" is admin 1.
                adminone_name = row["Area"]
                if not adminone_name:
                    add_message(
                        warnings,
                        dataset_name,
                        f"Admin 1: ignoring blank Area name in {countryiso3}",
                    )
                    return None
                adminoneinfo = self.get_adminoneinfo(
                    food_sec_config["adm_ignore_patterns"],
                    warnings,
                    dataset_name,
                    countryiso3,
                    adminone_name,
                )
                if not adminoneinfo:
                    return None
                return self.get_adminone_admin2_ref(
                    food_sec_config,
                    warnings,
                    errors,
                    dataset_name,
                    adminoneinfo,
                )

        adminoneinfo = self.get_adminoneinfo(
            food_sec_config["adm_ignore_patterns"],
            warnings,
            dataset_name,
            countryiso3,
            adminone_name,
        )
        if not adminoneinfo:
            return None
        if admin_level == "adminone":
            return self.get_adminone_admin2_ref(
                food_sec_config, warnings, errors, dataset_name, adminoneinfo
            )
        return self.get_admintwo_admin2_ref(
            food_sec_config,
            warnings,
            errors,
            dataset_name,
            row,
            adminoneinfo,
        )

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
        food_sec_config = self._configuration["food_security"]
        for resource in dataset.get_resources():
            admin_level = self.get_admin_level_from_resource_name(
                resource["name"]
            )
            if not admin_level:
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
                if countryiso3 not in self._configuration["HAPI_countries"]:
                    continue
                if admin_level == "national":
                    admin2_ref = self._admins.get_admin2_ref(
                        admin_level, countryiso3, dataset_name, errors
                    )
                else:
                    admin2_ref = self.process_subnational(
                        food_sec_config,
                        warnings,
                        errors,
                        dataset_name,
                        countryiso3,
                        admin_level,
                        row,
                    )
                if not admin2_ref:
                    continue
                time_period_start = parse_date(row["From"])
                time_period_end = parse_date(row["To"])

                food_security_row = DBFoodSecurity(
                    resource_hdx_id=resource_id,
                    admin2_ref=admin2_ref,
                    ipc_phase=row["Phase"],
                    ipc_type=row["Validity period"],
                    reference_period_start=time_period_start,
                    reference_period_end=time_period_end,
                    population_in_phase=row["Number"],
                    population_fraction_in_phase=row["Percentage"],
                )
                self._session.add(food_security_row)
            self._session.commit()
        for warning in sorted(warnings):
            logger.warning(warning)
        for error in sorted(errors):
            logger.error(error)
