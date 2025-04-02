import logging
from datetime import datetime
from typing import Dict, Optional

from hdx.api.configuration import Configuration
from hdx.api.utilities.hdx_error_handler import HDXErrorHandler
from hdx.database import Database
from hdx.location.adminlevel import AdminLevel
from hdx.scraper.framework.runner import Runner
from hdx.scraper.framework.utilities.reader import Read
from hdx.scraper.framework.utilities.sources import Sources
from hdx.utilities.typehint import ListTuple

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
        scrapers_to_run: Optional[ListTuple[str]] = None,
        error_handler: Optional[HDXErrorHandler] = None,
        use_live: bool = True,
        countries_to_run: Optional[ListTuple[str]] = None,
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
        libhxl_dataset = AdminLevel.get_libhxl_dataset(
            retriever=reader
        ).cache()
        libhxl_format_dataset = AdminLevel.get_libhxl_dataset(
            url=AdminLevel.formats_url, retriever=reader
        ).cache()
        self._admins = Admins(
            configuration,
            database,
            self._locations,
            libhxl_dataset,
            error_handler,
        )
        admin1_config = configuration["admin1"]
        self._adminone = AdminLevel(admin_config=admin1_config, admin_level=1)
        admin2_config = configuration["admin2"]
        self._admintwo = AdminLevel(admin_config=admin2_config, admin_level=2)
        self._adminone.setup_from_libhxl_dataset(libhxl_dataset)
        self._adminone.load_pcode_formats_from_libhxl_dataset(
            libhxl_format_dataset
        )
        self._admintwo.setup_from_libhxl_dataset(libhxl_dataset)
        self._admintwo.load_pcode_formats_from_libhxl_dataset(
            libhxl_format_dataset
        )
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
        self._runner = Runner(
            self._countries,
            today=today,
            error_handler=error_handler,
            scrapers_to_run=scrapers_to_run,
        )
        self._configurable_scrapers = {}
        self.create_configurable_scrapers()

        self._metadata = Metadata(
            runner=self._runner, database=database, today=today
        )

    def setup_configurable_scrapers(
        self, prefix, level, suffix_attribute=None, adminlevel=None
    ):
        if self._themes_to_run:
            if prefix not in self._themes_to_run:
                return None, None, None, None
            countryiso3s = self._themes_to_run[prefix]
        else:
            countryiso3s = None
        source_configuration = Sources.create_source_configuration(
            suffix_attribute=suffix_attribute,
            admin_sources=True,
            adminlevel=adminlevel,
        )
        suffix = f"_{level}"
        if countryiso3s:
            configuration = {}
            # This assumes format prefix_iso_.... eg.
            # population_gtm
            iso3_index = len(prefix) + 1
            for key, value in self._configuration[f"{prefix}{suffix}"].items():
                if len(key) < iso3_index + 3:
                    continue
                countryiso3 = key[iso3_index : iso3_index + 3]
                if countryiso3.upper() not in countryiso3s:
                    continue
                configuration[key] = value
        else:
            configuration = self._configuration[f"{prefix}{suffix}"]
        return configuration, source_configuration, suffix, countryiso3s

    def create_configurable_scrapers(self):
        def _create_configurable_scrapers(
            prefix, level, suffix_attribute=None, adminlevel=None
        ):
            configuration, source_configuration, suffix, countryiso3s = (
                self.setup_configurable_scrapers(
                    prefix, level, suffix_attribute, adminlevel
                )
            )
            if not configuration:
                return
            scraper_names = self._runner.add_configurables(
                configuration,
                level,
                adminlevel=adminlevel,
                source_configuration=source_configuration,
                suffix=suffix,
                countryiso3s=countryiso3s,
            )
            current_scrapers = self._configurable_scrapers.get(prefix, [])
            self._configurable_scrapers[prefix] = (
                current_scrapers + scraper_names
            )

        _create_configurable_scrapers("national_risk", "national")

    def run(self):
        self._runner.run()

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
        if (
            not self._themes_to_run
            or "operational_presence" in self._themes_to_run
        ):
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
        if (
            not self._themes_to_run
            or "humanitarian_needs" in self._themes_to_run
        ):
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
            results = self._runner.get_hapi_results(
                self._configurable_scrapers["national_risk"]
            )
            national_risk = NationalRisk(
                database=self._database,
                metadata=self._metadata,
                locations=self._locations,
                results=results,
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
        self._metadata.populate()
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
