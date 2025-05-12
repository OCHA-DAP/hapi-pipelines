"""Populate the location table."""

from typing import List, Optional

from hapi_schema.db_location import DBLocation
from hdx.api.configuration import Configuration
from hdx.database import Database
from hdx.location.country import Country
from hdx.utilities.dateparse import parse_date

from .base_uploader import BaseUploader


class Locations(BaseUploader):
    def __init__(
        self,
        configuration: Configuration,
        database: Database,
        use_live: bool = True,
        countries: Optional[List[str]] = None,
    ):
        super().__init__(database)
        Country.countriesdata(
            use_live=use_live,
            country_name_overrides=configuration["country_name_overrides"],
            country_name_mappings=configuration["country_name_mappings"],
        )
        if countries:
            self.hapi_countries = countries
        else:
            self.hapi_countries = list(Country.countriesdata()["countries"].keys())
        self.data = {}

    def populate(self) -> None:
        for country in Country.countriesdata()["countries"].values():
            code = country["#country+code+v_iso3"]
            has_hrp = True if country["#indicator+bool+hrp"] == "Y" else False
            in_gho = True if country["#indicator+bool+gho"] == "Y" else False
            location_row = DBLocation(
                code=code,
                name=country["#country+name+preferred"],
                has_hrp=has_hrp,
                in_gho=in_gho,
                reference_period_start=parse_date(country["#date+start"]),
            )
            self._session.add(location_row)
            self._session.commit()
            self.data[code] = location_row.id
