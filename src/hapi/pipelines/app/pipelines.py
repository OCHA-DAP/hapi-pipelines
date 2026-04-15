import logging
from collections.abc import Sequence
from datetime import datetime
from typing import Dict, Optional

from hdx.api.configuration import Configuration
from hdx.api.utilities.hdx_error_handler import HDXErrorHandler
from hdx.database import Database
from hdx.location.adminlevel import AdminLevel
from hdx.scraper.framework.utilities.reader import Read
from hdx.scraper.framework.utilities.sources import Sources

from hapi.pipelines.database.admins import Admins
from hapi.pipelines.database.conflict_event import ConflictEvent
from hapi.pipelines.database.currency import Currency
from hapi.pipelines.database.food_price import FoodPrice
from hapi.pipelines.database.food_security import FoodSecurity
from hapi.pipelines.database.funding import Funding
from hapi.pipelines.database.humanitarian_needs import HumanitarianNeeds
from hapi.pipelines.database.idps import IDPs
from hapi.pipelines.database.locations import Locations
from hapi.pipelines.database.metadata import Metadata
from hapi.pipelines.database.national_risk import NationalRisk
from hapi.pipelines.database.operational_presence import OperationalPresence
from hapi.pipelines.database.org import Org
from hapi.pipelines.database.org_type import OrgType
from hapi.pipelines.database.population import Population
from hapi.pipelines.database.poverty_rate import PovertyRate
from hapi.pipelines.database.rainfall import Rainfall
from hapi.pipelines.database.refugees import Refugees
from hapi.pipelines.database.returnees import Returnees
from hapi.pipelines.database.sector import Sector
from hapi.pipelines.database.wfp_commodity import WFPCommodity
from hapi.pipelines.database.wfp_market import WFPMarket

logger = logging.getLogger(__name__)


class Pipelines:
    def __init__(
        self,
        configuration: Configuration,
        database: Database,
        today: datetime,
        themes_to_run: Optional[Dict] = None,
        error_handler: Optional[HDXErrorHandler] = None,
        use_live: bool = True,
        countries_to_run: Optional[Sequence[str]] = None,
    ):
        self._configuration = configuration
        self._database = database
        self._themes_to_run = themes_to_run
        self._locations = Locations(
            configuration=configuration,
            database=database,
            use_live=use_live,
            countries=countries_to_run,
        )
        self._countries = self._locations.hapi_countries
        self._error_handler = error_handler
        reader = Read.get_reader("hdx")
        _, iterator = reader.get_tabular_rows(AdminLevel.admin_url, dict_form=True)
        pcode_rows = []
        for row in iterator:
            if row["Location"] not in self._locations.hapi_countries:
                continue
            pcode_rows.append(row)
        _, iterator = reader.get_tabular_rows(AdminLevel.formats_url, dict_form=True)
        pcode_formats_rows = []
        for row in iterator:
            if row["Location"] not in self._locations.hapi_countries:
                continue
            pcode_formats_rows.append(row)
        self._admins = Admins(
            configuration,
            database,
            self._locations,
            pcode_rows,
            error_handler,
        )
        admin1_config = configuration["admin1"]
        self._adminone = AdminLevel(admin_config=admin1_config, admin_level=1)
        admin2_config = configuration["admin2"]
        self._admintwo = AdminLevel(admin_config=admin2_config, admin_level=2)
        self._adminone.setup_from_iterable(pcode_rows)
        self._adminone.load_pcode_formats_from_iterable(pcode_formats_rows)
        self._admintwo.setup_from_iterable(pcode_rows)
        self._admintwo.load_pcode_formats_from_iterable(pcode_formats_rows)
        self._admintwo.set_parent_admins_from_adminlevels([self._adminone])
        logger.info("Admin one name mappings:")
        self._adminone.output_admin_name_mappings()
        logger.info("Admin two name mappings:")
        self._admintwo.output_admin_name_mappings()
        logger.info("Admin two name replacements:")
        self._admintwo.output_admin_name_replacements()

        self._org_type = OrgType(
            database=database,
        )
        self._sector = Sector(
            database=database,
        )
        Sources.set_default_source_date_format("%Y-%m-%d")
        self._metadata = Metadata(database=database, today=today)

    def output_population(self):
        if not self._themes_to_run or "population" in self._themes_to_run:
            population = Population(
                database=self._database,
                metadata=self._metadata,
                locations=self._locations,
                admins=self._admins,
                configuration=self._configuration,
                error_handler=self._error_handler,
            )
            population.populate()

    def output_operational_presence(self):
        if not self._themes_to_run or "operational_presence" in self._themes_to_run:
            org = Org(
                database=self._database,
                metadata=self._metadata,
                configuration=self._configuration,
            )
            org.populate()
            operational_presence = OperationalPresence(
                database=self._database,
                metadata=self._metadata,
                locations=self._locations,
                admins=self._admins,
                configuration=self._configuration,
                error_handler=self._error_handler,
            )
            operational_presence.populate()

    def output_food_security(self):
        if not self._themes_to_run or "food_security" in self._themes_to_run:
            food_security = FoodSecurity(
                database=self._database,
                metadata=self._metadata,
                locations=self._locations,
                admins=self._admins,
                configuration=self._configuration,
                error_handler=self._error_handler,
            )
            food_security.populate()

    def output_humanitarian_needs(self):
        if not self._themes_to_run or "humanitarian_needs" in self._themes_to_run:
            humanitarian_needs = HumanitarianNeeds(
                database=self._database,
                metadata=self._metadata,
                locations=self._locations,
                admins=self._admins,
                configuration=self._configuration,
                error_handler=self._error_handler,
            )
            humanitarian_needs.populate()

    def output_national_risk(self):
        if not self._themes_to_run or "national_risk" in self._themes_to_run:
            national_risk = NationalRisk(
                database=self._database,
                metadata=self._metadata,
                locations=self._locations,
                configuration=self._configuration,
            )
            national_risk.populate()

    def output_refugees(self):
        if not self._themes_to_run or "refugees" in self._themes_to_run:
            refugees = Refugees(
                database=self._database,
                metadata=self._metadata,
                locations=self._locations,
                admins=self._admins,
                configuration=self._configuration,
                error_handler=self._error_handler,
            )
            refugees.populate()

    def output_returnees(self):
        if not self._themes_to_run or "returnees" in self._themes_to_run:
            returnees = Returnees(
                database=self._database,
                metadata=self._metadata,
                locations=self._locations,
                admins=self._admins,
                configuration=self._configuration,
                error_handler=self._error_handler,
            )
            returnees.populate()

    def output_idps(self):
        if not self._themes_to_run or "idps" in self._themes_to_run:
            idps = IDPs(
                database=self._database,
                metadata=self._metadata,
                locations=self._locations,
                admins=self._admins,
                configuration=self._configuration,
                error_handler=self._error_handler,
            )
            idps.populate()

    def output_funding(self):
        if not self._themes_to_run or "funding" in self._themes_to_run:
            funding = Funding(
                database=self._database,
                metadata=self._metadata,
                locations=self._locations,
                admins=self._admins,
                configuration=self._configuration,
                error_handler=self._error_handler,
            )
            funding.populate()

    def output_poverty_rate(self):
        if not self._themes_to_run or "poverty_rate" in self._themes_to_run:
            poverty_rate = PovertyRate(
                database=self._database,
                metadata=self._metadata,
                locations=self._locations,
                admins=self._admins,
                configuration=self._configuration,
                error_handler=self._error_handler,
            )
            poverty_rate.populate()

    def output_conflict_event(self):
        if not self._themes_to_run or "conflict_event" in self._themes_to_run:
            conflict_event = ConflictEvent(
                database=self._database,
                metadata=self._metadata,
                locations=self._locations,
                admins=self._admins,
                configuration=self._configuration,
                error_handler=self._error_handler,
            )
            conflict_event.populate()

    def output_food_prices(self):
        if not self._themes_to_run or "food_prices" in self._themes_to_run:
            currency = Currency(
                database=self._database,
                configuration=self._configuration,
                key="wfp_currency",
                error_handler=self._error_handler,
            )
            currency.populate()
            wfp_commodity = WFPCommodity(
                database=self._database,
                configuration=self._configuration,
                key="wfp_commodity",
                error_handler=self._error_handler,
            )
            wfp_commodity.populate()
            wfp_market = WFPMarket(
                database=self._database,
                admins=self._admins,
                configuration=self._configuration,
                key="wfp_market",
                error_handler=self._error_handler,
            )
            wfp_market.populate()
            food_price = FoodPrice(
                database=self._database,
                metadata=self._metadata,
                locations=self._locations,
                admins=self._admins,
                configuration=self._configuration,
                error_handler=self._error_handler,
            )
            food_price.populate()

    def output_rainfall(self):
        if not self._themes_to_run or "rainfall" in self._themes_to_run:
            rainfall = Rainfall(
                database=self._database,
                metadata=self._metadata,
                locations=self._locations,
                admins=self._admins,
                configuration=self._configuration,
                error_handler=self._error_handler,
            )
            rainfall.populate()

    def output(self):
        self._locations.populate()
        self._admins.populate()
        self._org_type.populate()
        self._sector.populate()
        self.output_population()
        self.output_operational_presence()
        self.output_food_security()
        self.output_humanitarian_needs()
        self.output_national_risk()
        self.output_refugees()
        self.output_returnees()
        self.output_idps()
        self.output_funding()
        self.output_poverty_rate()
        self.output_conflict_event()
        self.output_food_prices()
        self.output_rainfall()
