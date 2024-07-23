import logging
from datetime import datetime
from typing import Dict, Optional

from hdx.api.configuration import Configuration
from hdx.location.adminlevel import AdminLevel
from hdx.scraper.runner import Runner
from hdx.scraper.utilities.sources import Sources
from hdx.utilities.errors_onexit import ErrorsOnExit
from hdx.utilities.typehint import ListTuple
from sqlalchemy.orm import Session

from hapi.pipelines.database.admins import Admins
from hapi.pipelines.database.conflict_event import ConflictEvent
from hapi.pipelines.database.currency import Currency
from hapi.pipelines.database.food_price import FoodPrice
from hapi.pipelines.database.food_security import FoodSecurity
from hapi.pipelines.database.funding import Funding
from hapi.pipelines.database.humanitarian_needs import HumanitarianNeeds
from hapi.pipelines.database.locations import Locations
from hapi.pipelines.database.metadata import Metadata
from hapi.pipelines.database.national_risk import NationalRisk
from hapi.pipelines.database.operational_presence import OperationalPresence
from hapi.pipelines.database.org import Org
from hapi.pipelines.database.org_type import OrgType
from hapi.pipelines.database.population import Population
from hapi.pipelines.database.poverty_rate import PovertyRate
from hapi.pipelines.database.refugees import Refugees
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
        errors_on_exit: Optional[ErrorsOnExit] = None,
        use_live: bool = True,
    ):
        self.configuration = configuration
        self.session = session
        self.themes_to_run = themes_to_run
        self.locations = Locations(
            configuration=configuration,
            session=session,
            use_live=use_live,
        )
        countries = configuration["HAPI_countries"]
        libhxl_dataset = AdminLevel.get_libhxl_dataset().cache()
        self.admins = Admins(
            configuration, session, self.locations, libhxl_dataset
        )
        admin1_config = configuration["admin1"]
        self.adminone = AdminLevel(admin_config=admin1_config, admin_level=1)
        admin2_config = configuration["admin2"]
        self.admintwo = AdminLevel(admin_config=admin2_config, admin_level=2)
        self.adminone.setup_from_libhxl_dataset(libhxl_dataset, countries)
        self.adminone.load_pcode_formats()
        self.admintwo.setup_from_libhxl_dataset(libhxl_dataset, countries)
        self.admintwo.load_pcode_formats()
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
            countries,
            today=today,
            errors_on_exit=errors_on_exit,
            scrapers_to_run=scrapers_to_run,
        )
        self.configurable_scrapers = {}
        self.create_configurable_scrapers()
        self.metadata = Metadata(
            runner=self.runner, session=session, today=today
        )
        self.wfp_commodity = WFPCommodity(
            session=session,
            datasetinfo=configuration["wfp_commodity"],
        )
        self.wfp_market = WFPMarket(
            session=session,
            datasetinfo=configuration["wfp_market"],
            countryiso3s=countries,
            admins=self.admins,
            adminone=self.adminone,
            admintwo=self.admintwo,
        )
        self.food_price = FoodPrice(
            session=session,
            datasetinfo=configuration["wfp_countries"],
            countryiso3s=countries,
            metadata=self.metadata,
            currency=self.currency,
            commodity=self.wfp_commodity,
            market=self.wfp_market,
        )

    def create_configurable_scrapers(self):
        def _create_configurable_scrapers(
            prefix, level, suffix_attribute=None, adminlevel=None
        ):
            if self.themes_to_run:
                if prefix not in self.themes_to_run:
                    return
                countryiso3s = self.themes_to_run[prefix]
            else:
                countryiso3s = None
            suffix = f"_{level}"
            source_configuration = Sources.create_source_configuration(
                suffix_attribute=suffix_attribute,
                admin_sources=True,
                adminlevel=adminlevel,
            )
            if countryiso3s:
                configuration = {}
                # This assumes format prefix_iso_.... eg.
                # population_gtm, humanitarian_needs_afg_total
                iso3_index = len(prefix) + 1
                for key, value in self.configuration[
                    f"{prefix}{suffix}"
                ].items():
                    if len(key) < iso3_index + 3:
                        continue
                    countryiso3 = key[iso3_index : iso3_index + 3]
                    if countryiso3.upper() not in countryiso3s:
                        continue
                    configuration[key] = value
            else:
                configuration = self.configuration[f"{prefix}{suffix}"]
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

        _create_configurable_scrapers("population", "national")
        _create_configurable_scrapers(
            "population", "adminone", adminlevel=self.adminone
        )
        _create_configurable_scrapers(
            "population", "admintwo", adminlevel=self.admintwo
        )
        _create_configurable_scrapers(
            "operational_presence", "admintwo", adminlevel=self.admintwo
        )
        _create_configurable_scrapers(
            "operational_presence", "adminone", adminlevel=self.adminone
        )
        _create_configurable_scrapers("operational_presence", "national")
        _create_configurable_scrapers(
            "food_security", "adminone", adminlevel=self.adminone
        )
        _create_configurable_scrapers(
            "food_security", "admintwo", adminlevel=self.admintwo
        )
        _create_configurable_scrapers("national_risk", "national")
        _create_configurable_scrapers("funding", "national")
        _create_configurable_scrapers("refugees", "national")
        _create_configurable_scrapers("poverty_rate", "national")
        _create_configurable_scrapers("conflict_event", "national")
        _create_configurable_scrapers(
            "conflict_event", "admintwo", adminlevel=self.admintwo
        )

    def run(self):
        self.runner.run()

    def output(self):
        self.locations.populate()
        self.admins.populate()
        self.metadata.populate()
        self.org.populate()
        self.org_type.populate()
        self.sector.populate()
        self.currency.populate()

        if not self.themes_to_run or "population" in self.themes_to_run:
            results = self.runner.get_hapi_results(
                self.configurable_scrapers["population"]
            )
            population = Population(
                session=self.session,
                metadata=self.metadata,
                admins=self.admins,
                results=results,
            )
            population.populate()

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
            )
            operational_presence.populate()

        if not self.themes_to_run or "food_security" in self.themes_to_run:
            results = self.runner.get_hapi_results(
                self.configurable_scrapers["food_security"]
            )
            food_security = FoodSecurity(
                session=self.session,
                metadata=self.metadata,
                admins=self.admins,
                results=results,
            )
            food_security.populate()

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
            )
            humanitarian_needs.populate()

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

        if not self.themes_to_run or "refugees" in self.themes_to_run:
            results = self.runner.get_hapi_results(
                self.configurable_scrapers["refugees"]
            )
            refugees = Refugees(
                session=self.session,
                metadata=self.metadata,
                locations=self.locations,
                results=results,
            )
            refugees.populate()

        if not self.themes_to_run or "funding" in self.themes_to_run:
            results = self.runner.get_hapi_results(
                self.configurable_scrapers["funding"]
            )
            funding = Funding(
                session=self.session,
                metadata=self.metadata,
                locations=self.locations,
                results=results,
            )
            funding.populate()

        if not self.themes_to_run or "poverty_rate" in self.themes_to_run:
            results = self.runner.get_hapi_results(
                self.configurable_scrapers["poverty_rate"]
            )
            poverty_rate = PovertyRate(
                session=self.session,
                metadata=self.metadata,
                admins=self.admins,
                config=self.configuration["poverty_rate_national"],
                results=results,
            )
            poverty_rate.populate()

        if not self.themes_to_run or "conflict_event" in self.themes_to_run:
            results = self.runner.get_hapi_results(
                self.configurable_scrapers["conflict_event"]
            )
            conflict_event = ConflictEvent(
                session=self.session,
                metadata=self.metadata,
                admins=self.admins,
                results=results,
                config=self.configuration,
            )
            conflict_event.populate()

        if not self.themes_to_run or "food_prices" in self.themes_to_run:
            self.wfp_commodity.populate()
            self.wfp_market.populate()
            self.food_price.populate()

    def debug(self, folder: str) -> None:
        self.org.output_org_map(folder)
