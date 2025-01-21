import logging
from datetime import datetime
from typing import Dict, Optional

from hdx.api.configuration import Configuration
from hdx.api.utilities.hdx_error_handler import HDXErrorHandler
from hdx.location.adminlevel import AdminLevel
from hdx.scraper.framework.runner import Runner
from hdx.scraper.framework.utilities.reader import Read
from hdx.scraper.framework.utilities.sources import Sources
from hdx.utilities.typehint import ListTuple
from sqlalchemy.orm import Session

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
from hapi.pipelines.database.refugees_and_returnees import RefugeesAndReturnees
from hapi.pipelines.database.sector import Sector
from hapi.pipelines.database.wfp_commodity import WFPCommodity
from hapi.pipelines.database.wfp_market import WFPMarket

logger = logging.getLogger(__name__)


class Pipelines:
    def __init__(
        self,
        configuration: Configuration,
        session: Session,
        today: datetime,
        themes_to_run: Optional[Dict] = None,
        scrapers_to_run: Optional[ListTuple[str]] = None,
        error_handler: Optional[HDXErrorHandler] = None,
        use_live: bool = True,
        countries_to_run: Optional[ListTuple[str]] = None,
    ):
        self.configuration = configuration
        self.session = session
        self.themes_to_run = themes_to_run
        self.locations = Locations(
            configuration=configuration,
            session=session,
            use_live=use_live,
            countries=countries_to_run,
        )
        self.countries = self.locations.hapi_countries
        self.error_handler = error_handler
        reader = Read.get_reader("hdx")
        libhxl_dataset = AdminLevel.get_libhxl_dataset(
            retriever=reader
        ).cache()
        libhxl_format_dataset = AdminLevel.get_libhxl_dataset(
            url=AdminLevel.formats_url, retriever=reader
        ).cache()
        self.admins = Admins(
            configuration, session, self.locations, libhxl_dataset
        )
        admin1_config = configuration["admin1"]
        self.adminone = AdminLevel(admin_config=admin1_config, admin_level=1)
        admin2_config = configuration["admin2"]
        self.admintwo = AdminLevel(admin_config=admin2_config, admin_level=2)
        self.adminone.setup_from_libhxl_dataset(libhxl_dataset)
        self.adminone.load_pcode_formats_from_libhxl_dataset(
            libhxl_format_dataset
        )
        self.admintwo.setup_from_libhxl_dataset(libhxl_dataset)
        self.admintwo.load_pcode_formats_from_libhxl_dataset(
            libhxl_format_dataset
        )
        self.admintwo.set_parent_admins_from_adminlevels([self.adminone])
        logger.info("Admin one name mappings:")
        self.adminone.output_admin_name_mappings()
        logger.info("Admin two name mappings:")
        self.admintwo.output_admin_name_mappings()
        logger.info("Admin two name replacements:")
        self.admintwo.output_admin_name_replacements()

        self.org = Org(
            session=session,
            datasetinfo=configuration["org"],
        )
        self.org_type = OrgType(
            session=session,
            datasetinfo=configuration["org_type"],
            org_type_map=configuration["org_type_map"],
        )
        self.sector = Sector(
            session=session,
            datasetinfo=configuration["sector"],
            sector_map=configuration["sector_map"],
        )
        self.currency = Currency(configuration=configuration, session=session)

        Sources.set_default_source_date_format("%Y-%m-%d")
        self.runner = Runner(
            self.countries,
            today=today,
            error_handler=error_handler,
            scrapers_to_run=scrapers_to_run,
        )
        self.configurable_scrapers = {}
        self.create_configurable_scrapers()
        self.metadata = Metadata(
            runner=self.runner, session=session, today=today
        )

    def setup_configurable_scrapers(
        self, prefix, level, suffix_attribute=None, adminlevel=None
    ):
        if self.themes_to_run:
            if prefix not in self.themes_to_run:
                return None, None, None, None
            countryiso3s = self.themes_to_run[prefix]
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
            # population_gtm, operational_presence_afg_total
            iso3_index = len(prefix) + 1
            for key, value in self.configuration[f"{prefix}{suffix}"].items():
                if len(key) < iso3_index + 3:
                    continue
                countryiso3 = key[iso3_index : iso3_index + 3]
                if countryiso3.upper() not in countryiso3s:
                    continue
                configuration[key] = value
        else:
            configuration = self.configuration[f"{prefix}{suffix}"]
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
            scraper_names = self.runner.add_configurables(
                configuration,
                level,
                adminlevel=adminlevel,
                source_configuration=source_configuration,
                suffix=suffix,
                countryiso3s=countryiso3s,
            )
            current_scrapers = self.configurable_scrapers.get(prefix, [])
            self.configurable_scrapers[prefix] = (
                current_scrapers + scraper_names
            )

        _create_configurable_scrapers(
            "operational_presence", "admintwo", adminlevel=self.admintwo
        )
        _create_configurable_scrapers(
            "operational_presence", "adminone", adminlevel=self.adminone
        )
        _create_configurable_scrapers("operational_presence", "national")
        _create_configurable_scrapers("national_risk", "national")
        _create_configurable_scrapers("refugees_and_returnees", "national")
        _create_configurable_scrapers("idps", "national")
        _create_configurable_scrapers(
            "idps", "adminone", adminlevel=self.adminone
        )
        _create_configurable_scrapers(
            "idps", "admintwo", adminlevel=self.admintwo
        )
        _create_configurable_scrapers("conflict_event", "national")
        _create_configurable_scrapers(
            "conflict_event", "admintwo", adminlevel=self.admintwo
        )

    def run(self):
        self.runner.run()

    def output_population(self):
        if not self.themes_to_run or "population" in self.themes_to_run:
            population = Population(
                session=self.session,
                metadata=self.metadata,
                admins=self.admins,
                configuration=self.configuration,
                error_handler=self.error_handler,
            )
            population.populate()

    def output_operational_presence(self):
        if (
            not self.themes_to_run
            or "operational_presence" in self.themes_to_run
        ):
            results = self.runner.get_hapi_results(
                self.configurable_scrapers["operational_presence"]
            )
            operational_presence = OperationalPresence(
                session=self.session,
                metadata=self.metadata,
                admins=self.admins,
                adminone=self.adminone,
                admintwo=self.admintwo,
                org=self.org,
                org_type=self.org_type,
                sector=self.sector,
                results=results,
                config=self.configuration,
                error_handler=self.error_handler,
            )
            operational_presence.populate()

    def output_food_security(self):
        if not self.themes_to_run or "food_security" in self.themes_to_run:
            food_security = FoodSecurity(
                session=self.session,
                metadata=self.metadata,
                admins=self.admins,
                adminone=self.adminone,
                admintwo=self.admintwo,
                countryiso3s=self.countries,
                configuration=self.configuration,
                error_handler=self.error_handler,
            )
            food_security.populate()

    def output_humanitarian_needs(self):
        if (
            not self.themes_to_run
            or "humanitarian_needs" in self.themes_to_run
        ):
            humanitarian_needs = HumanitarianNeeds(
                session=self.session,
                metadata=self.metadata,
                admins=self.admins,
                sector=self.sector,
                configuration=self.configuration,
                error_handler=self.error_handler,
            )
            humanitarian_needs.populate()

    def output_national_risk(self):
        if not self.themes_to_run or "national_risk" in self.themes_to_run:
            results = self.runner.get_hapi_results(
                self.configurable_scrapers["national_risk"]
            )
            national_risk = NationalRisk(
                session=self.session,
                metadata=self.metadata,
                locations=self.locations,
                results=results,
            )
            national_risk.populate()

    def output_refugees_and_returnees(self):
        if (
            not self.themes_to_run
            or "refugees_and_returnees" in self.themes_to_run
        ):
            results = self.runner.get_hapi_results(
                self.configurable_scrapers["refugees_and_returnees"]
            )
            refugees_and_returnees = RefugeesAndReturnees(
                session=self.session,
                metadata=self.metadata,
                locations=self.locations,
                results=results,
            )
            refugees_and_returnees.populate()

    def output_idps(self):
        if not self.themes_to_run or "idps" in self.themes_to_run:
            results = self.runner.get_hapi_results(
                self.configurable_scrapers["idps"]
            )
            idps = IDPs(
                session=self.session,
                metadata=self.metadata,
                admins=self.admins,
                results=results,
                error_handler=self.error_handler,
            )
            idps.populate()

    def output_funding(self):
        if not self.themes_to_run or "funding" in self.themes_to_run:
            funding = Funding(
                session=self.session,
                metadata=self.metadata,
                countryiso3s=self.countries,
                locations=self.locations,
                configuration=self.configuration,
                error_handler=self.error_handler,
            )
            funding.populate()

    def output_poverty_rate(self):
        if not self.themes_to_run or "poverty_rate" in self.themes_to_run:
            poverty_rate = PovertyRate(
                session=self.session,
                metadata=self.metadata,
                admins=self.admins,
                configuration=self.configuration,
                error_handler=self.error_handler,
            )
            poverty_rate.populate()

    def output_conflict_event(self):
        if not self.themes_to_run or "conflict_event" in self.themes_to_run:
            results = self.runner.get_hapi_results(
                self.configurable_scrapers["conflict_event"]
            )
            conflict_event = ConflictEvent(
                session=self.session,
                metadata=self.metadata,
                admins=self.admins,
                results=results,
                configuration=self.configuration,
                error_handler=self.error_handler,
            )
            conflict_event.populate()

    def output_food_prices(self):
        if not self.themes_to_run or "food_prices" in self.themes_to_run:
            wfp_commodity = WFPCommodity(
                session=self.session,
                datasetinfo=self.configuration["wfp_commodity"],
            )
            wfp_commodity.populate()
            wfp_market = WFPMarket(
                session=self.session,
                datasetinfo=self.configuration["wfp_market"],
                countryiso3s=self.countries,
                admins=self.admins,
                adminone=self.adminone,
                admintwo=self.admintwo,
                configuration=self.configuration,
                error_handler=self.error_handler,
            )
            wfp_market.populate()
            food_price = FoodPrice(
                session=self.session,
                datasetinfo=self.configuration["wfp_countries"],
                countryiso3s=self.countries,
                metadata=self.metadata,
                currency=self.currency,
                commodity=wfp_commodity,
                market=wfp_market,
                error_handler=self.error_handler,
            )
            food_price.populate()

    def output(self):
        self.locations.populate()
        self.admins.populate()
        self.metadata.populate()
        self.org.populate()
        self.org_type.populate()
        self.sector.populate()
        self.currency.populate()
        self.output_population()
        self.output_operational_presence()
        self.output_food_security()
        self.output_humanitarian_needs()
        self.output_national_risk()
        self.output_refugees_and_returnees()
        self.output_idps()
        self.output_funding()
        self.output_poverty_rate()
        self.output_conflict_event()
        self.output_food_prices()

    def debug(self, folder: str) -> None:
        self.org.output_org_map(folder)

    def output_errors(self) -> None:
        self.error_handler.output_errors()
