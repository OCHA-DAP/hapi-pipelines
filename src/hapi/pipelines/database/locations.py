"""Populate the location table."""

from hapi_schema.db_location import DBLocation
from hdx.api.configuration import Configuration
from hdx.location.country import Country
from hdx.scraper.utilities.reader import Read
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
        self._datasetinfo = configuration["locations_hrp_gho"]

    def populate(self):
        has_hrp, in_gho = self.read_hrp_gho_data()
        for country in Country.countriesdata()["countries"].values():
            code = country["#country+code+v_iso3"]
            location_row = DBLocation(
                code=code,
                name=country["#country+name+preferred"],
                has_hrp=has_hrp.get(code, False),
                in_gho=in_gho.get(code, False),
                reference_period_start=parse_date(country["#date+start"]),
            )
            self._session.add(location_row)
            self._session.commit()
            self.data[code] = location_row.id

    def read_hrp_gho_data(self):
        has_hrp = {}
        in_gho = {}
        reader = Read.get_reader()
        headers, iterator = reader.get_tabular_rows(
            self._datasetinfo["url"],
            headers=2,
            dict_form=True,
            format="csv",
            file_prefix="locations",
        )
        for row in iterator:
            if (
                row["#indicator+hrp+bool"]
                and row["#indicator+hrp+bool"].upper() == "Y"
            ):
                has_hrp[row["#country+code"]] = True
            if (
                row["#indicator+gho+bool"]
                and row["#indicator+gho+bool"].upper() == "Y"
            ):
                in_gho[row["#country+code"]] = True
        return has_hrp, in_gho
