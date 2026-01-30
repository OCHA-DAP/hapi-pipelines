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
            code = country["ISO 3166-1 Alpha 3-Codes"]
            has_hrp = True if country["Has HRP"] == "Y" else False
            in_gho = True if country["In GHO"] == "Y" else False
            location_row = DBLocation(
                code=code,
                name=country["Preferred Term"],
                has_hrp=has_hrp,
                in_gho=in_gho,
                reference_period_start=parse_date(country["Reference Period Start"]),
            )
            self._session.add(location_row)
            self._session.commit()
            self.data[code] = location_row.id
