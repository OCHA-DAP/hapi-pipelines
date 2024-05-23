"""Populate the location table."""

from hapi_schema.db_location import DBLocation
from hdx.api.configuration import Configuration
from hdx.location.country import Country
from hdx.utilities.dateparse import parse_date
from sqlalchemy.orm import Session

from .base_uploader import BaseUploader


class Locations(BaseUploader):
    def __init__(
        self,
        configuration: Configuration,
        session: Session,
        use_live: bool = True,
    ):
        super().__init__(session)
        Country.countriesdata(
            use_live=use_live,
            country_name_overrides=configuration["country_name_overrides"],
            country_name_mappings=configuration["country_name_mappings"],
        )
        self.hapi_countries = configuration["HAPI_countries"]
        self.data = {}

    def populate(self):
        for country in Country.countriesdata()["countries"].values():
            code = country["#country+code+v_iso3"]
            location_row = DBLocation(
                code=code,
                name=country["#country+name+preferred"],
                reference_period_start=parse_date(country["#date+start"]),
            )
            self._session.add(location_row)
            self._session.commit()
            self.data[code] = location_row.id
