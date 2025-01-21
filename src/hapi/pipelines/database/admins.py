"""Populate the admin tables."""

import logging
import re
from abc import ABC
from typing import Dict, List, Literal, Optional

import hxl
from hapi_schema.db_admin1 import DBAdmin1
from hapi_schema.db_admin2 import DBAdmin2
from hapi_schema.db_location import DBLocation
from hdx.api.configuration import Configuration
from hdx.api.utilities.hdx_error_handler import HDXErrorHandler
from hdx.utilities.dateparse import parse_date
from hxl.filters import AbstractStreamingFilter
from sqlalchemy import select
from sqlalchemy.orm import Session

from .base_uploader import BaseUploader
from .locations import Locations

logger = logging.getLogger(__name__)

_ADMIN_LEVELS = ("1", "2")
_ADMIN_LEVELS_LITERAL = Literal["1", "2"]


class Admins(BaseUploader):
    admin_name_regex = re.compile(r"Admin (\d) Name")

    def __init__(
        self,
        configuration: Configuration,
        session: Session,
        locations: Locations,
        libhxl_dataset: hxl.Dataset,
        error_handler: HDXErrorHandler,
    ):
        super().__init__(session)
        self._limit = configuration["commit_limit"]
        self._orphan_admin2s = configuration["orphan_admin2s"]
        self._locations = locations
        self._libhxl_dataset = libhxl_dataset
        self._error_handler = error_handler
        self.admin1_data = {}
        self.admin2_data = {}

    def populate(self) -> None:
        logger.info("Populating admin1 table")
        self._update_admin_table(
            desired_admin_level="1",
            parent_dict=self._locations.data,
        )
        self._add_admin1_connector_rows()
        results = self._session.execute(select(DBAdmin1.id, DBAdmin1.code))
        self.admin1_data = {result[1]: result[0] for result in results}
        logger.info("Populating admin2 table")
        self._update_admin_table(
            desired_admin_level="2",
            parent_dict=self.admin1_data,
        )
        self._add_admin2_connector_rows()
        results = self._session.execute(select(DBAdmin2.id, DBAdmin2.code))
        for result in results:
            self.admin2_data[result[1]] = result[0]

    def _update_admin_table(
        self,
        desired_admin_level: _ADMIN_LEVELS_LITERAL,
        parent_dict: Dict,
    ):
        if desired_admin_level not in _ADMIN_LEVELS:
            raise ValueError(f"Admin levels must be one of {_ADMIN_LEVELS}")
        # Filter admin level and countries
        admin_filter = _AdminFilter(
            source=self._libhxl_dataset,
            desired_admin_level=desired_admin_level,
            country_codes=list(self._locations.hapi_countries),
        )
        for i, row in enumerate(admin_filter):
            code = row.get("#adm+code")
            name = row.get("#adm+name")
            time_period_start = parse_date(row.get("#date+start"))
            parent = row.get("#adm+code+parent")
            parent_ref = parent_dict.get(parent)
            if not parent_ref:
                if (
                    desired_admin_level == "2"
                    and code in self._orphan_admin2s.keys()
                ):
                    parent_ref = self.admin1_data[
                        get_admin1_to_location_connector_code(
                            location_code=self._orphan_admin2s[code]
                        )
                    ]
                else:
                    logger.warning(f"Missing parent {parent} for code {code}")
                    continue
            if desired_admin_level == "1":
                admin_row = DBAdmin1(
                    location_ref=parent_ref,
                    code=code,
                    name=name,
                    reference_period_start=time_period_start,
                )
            elif desired_admin_level == "2":
                admin_row = DBAdmin2(
                    admin1_ref=parent_ref,
                    code=code,
                    name=name,
                    reference_period_start=time_period_start,
                )
            self._session.add(admin_row)
            if i % self._limit == 0:
                self._session.commit()
        self._session.commit()

    def _add_admin1_connector_rows(self):
        for location_code, location_ref in self._locations.data.items():
            time_period_start = (
                self._session.query(DBLocation)
                .filter(DBLocation.id == location_ref)
                .one()
                .reference_period_start
            )
            admin_row = DBAdmin1(
                location_ref=location_ref,
                code=get_admin1_to_location_connector_code(
                    location_code=location_code
                ),
                name="UNSPECIFIED",
                is_unspecified=True,
                reference_period_start=time_period_start,
            )
            self._session.add(admin_row)
        self._session.commit()

    def _add_admin2_connector_rows(self):
        for admin1_code, admin1_ref in self.admin1_data.items():
            time_period_start = (
                self._session.query(DBAdmin1)
                .filter(DBAdmin1.id == admin1_ref)
                .one()
                .reference_period_start
            )
            admin_row = DBAdmin2(
                admin1_ref=admin1_ref,
                code=get_admin2_to_admin1_connector_code(
                    admin1_code=admin1_code
                ),
                name="UNSPECIFIED",
                is_unspecified=True,
                reference_period_start=time_period_start,
            )
            self._session.add(admin_row)
        self._session.commit()

    def get_admin_level(self, pcode: str) -> _ADMIN_LEVELS_LITERAL:
        """Given a pcode, return the admin level."""
        if pcode in self.admin1_data:
            return "1"
        elif pcode in self.admin2_data:
            return "2"
        raise ValueError(f"Pcode {pcode} not in admin1 or admin2 tables.")

    def get_admin1_ref(
        self,
        admin_level: str,
        admin_code: str,
        dataset_name: str,
        pipeline: str,
        error_handler: HDXErrorHandler,
    ) -> Optional[int]:
        admin1_code = get_admin1_code_based_on_level(
            admin_code=admin_code, admin_level=admin_level
        )
        ref = self.admin1_data.get(admin1_code)
        if ref is None:
            # TODO: resolve pipeline name
            error_handler.add_missing_value_message(
                pipeline, dataset_name, "admin 1 code", admin1_code
            )
        return ref

    def get_admin2_ref(
        self,
        admin_level: str,
        admin_code: str,
        dataset_name: str,
        pipeline: str,
        error_handler: HDXErrorHandler,
    ) -> Optional[int]:
        admin2_code = get_admin2_code_based_on_level(
            admin_code=admin_code, admin_level=admin_level
        )
        ref = self.admin2_data.get(admin2_code)
        if ref is None:
            # TODO: resolve pipeline name
            error_handler.add_missing_value_message(
                pipeline, dataset_name, "admin 2 code", admin2_code
            )
        return ref

    def get_admin2_ref_from_row(
        self, row: Dict, dataset_name: str, pipeline: str
    ):
        countryiso3 = row["Country ISO3"]
        if countryiso3 == "#country+code":  # ignore HXL row
            return None
        admin_level = "0"
        for header in row:
            match = self.admin_name_regex.match(header)
            if match and row[header]:
                admin_level = match.group(1)
        match admin_level:
            case "0":
                admin_level = "national"
                admin_code = countryiso3
            case "1":
                admin_code = row["Admin 1 PCode"]
                if admin_code:
                    admin_level = "adminone"
                else:
                    admin_level = "national"
                    admin_code = countryiso3
            case "2":
                admin_code = row["Admin 2 PCode"]
                if admin_code:
                    admin_level = "admintwo"
                else:
                    admin_code = row["Admin 1 PCode"]
                    if admin_code:
                        admin_level = "adminone"
                    else:
                        admin_level = "national"
                        admin_code = countryiso3
            case _:
                return None
        admin2_ref = self.get_admin2_ref(
            admin_level,
            admin_code,
            dataset_name,
            pipeline,
            self._error_handler,
        )
        if admin2_ref is None:
            if admin_level == "adminone":
                admin_code = get_admin1_to_location_connector_code(countryiso3)
            elif admin_level == "admintwo":
                admin_code = get_admin2_to_location_connector_code(countryiso3)
            else:
                return None
            admin2_ref = self.get_admin2_ref(
                admin_level,
                admin_code,
                dataset_name,
                pipeline,
                self._error_handler,
            )
        return admin2_ref


def get_admin2_to_admin1_connector_code(admin1_code: str) -> str:
    """Get the code for an unspecified admin2, based on the admin1 code."""
    return f"{admin1_code}-XXX"


def get_admin2_to_location_connector_code(location_code: str) -> str:
    """Get the code for an unspecified admin2, based on the location code."""
    return f"{location_code}-XXX-XXX"


def get_admin1_to_location_connector_code(location_code: str) -> str:
    """Get the code for an unspecified admin1, based on the location code."""
    return f"{location_code}-XXX"


def get_admin1_code_based_on_level(admin_code: str, admin_level: str) -> str:
    if admin_level == "national":
        admin1_code = get_admin1_to_location_connector_code(
            location_code=admin_code
        )
    elif admin_level == "adminone":
        admin1_code = admin_code
    else:
        raise KeyError(
            f"Admin level {admin_level} not one of 'national',"
            f"'adminone', 'admintwo'"
        )
    return admin1_code


def get_admin2_code_based_on_level(admin_code: str, admin_level: str) -> str:
    if admin_level == "national":
        admin1_code = get_admin1_to_location_connector_code(
            location_code=admin_code
        )
        admin2_code = get_admin2_to_admin1_connector_code(
            admin1_code=admin1_code
        )
    elif admin_level == "adminone":
        admin2_code = get_admin2_to_admin1_connector_code(
            admin1_code=admin_code
        )
    elif admin_level == "admintwo":
        admin2_code = admin_code
    else:
        raise KeyError(
            f"Admin level {admin_level} not one of 'national',"
            f"'adminone', 'admintwo'"
        )
    return admin2_code


class _AdminFilter(AbstractStreamingFilter, ABC):
    """Filter admin rows by level and country code."""

    def __init__(
        self,
        source: hxl.Dataset,
        desired_admin_level: _ADMIN_LEVELS_LITERAL,
        country_codes: List[str],
    ):
        self._desired_admin_level = desired_admin_level
        self._country_codes = country_codes
        super(AbstractStreamingFilter, self).__init__(source)

    def filter_row(self, row):
        if (
            row.get("#geo+admin_level") != self._desired_admin_level
            or row.get("#country+code") not in self._country_codes
        ):
            return None
        return row.values
