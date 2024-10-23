import logging
from os.path import join

import pytest
from hapi_schema.db_admin1 import DBAdmin1
from hapi_schema.db_admin2 import DBAdmin2
from hapi_schema.db_conflict_event import DBConflictEvent
from hapi_schema.db_currency import DBCurrency
from hapi_schema.db_dataset import DBDataset
from hapi_schema.db_food_price import DBFoodPrice
from hapi_schema.db_food_security import DBFoodSecurity
from hapi_schema.db_funding import DBFunding
from hapi_schema.db_humanitarian_needs import DBHumanitarianNeeds
from hapi_schema.db_idps import DBIDPs
from hapi_schema.db_location import DBLocation
from hapi_schema.db_national_risk import DBNationalRisk
from hapi_schema.db_operational_presence import DBOperationalPresence
from hapi_schema.db_org import DBOrg
from hapi_schema.db_org_type import DBOrgType
from hapi_schema.db_population import DBPopulation
from hapi_schema.db_poverty_rate import DBPovertyRate
from hapi_schema.db_refugees import DBRefugees
from hapi_schema.db_resource import DBResource
from hapi_schema.db_returnees import DBReturnees
from hapi_schema.db_sector import DBSector
from hapi_schema.db_wfp_commodity import DBWFPCommodity
from hapi_schema.db_wfp_market import DBWFPMarket
from hapi_schema.views import prepare_hapi_views
from hdx.api.configuration import Configuration
from hdx.database import Database
from hdx.scraper.framework.utilities.reader import Read
from hdx.utilities.dateparse import parse_date
from hdx.utilities.errors_onexit import ErrorsOnExit
from hdx.utilities.path import temp_dir
from hdx.utilities.useragent import UserAgent
from pytest_check import check
from sqlalchemy import func, select

from .org_mappings import check_org_mappings
from hapi.pipelines.app import load_yamls
from hapi.pipelines.app.__main__ import add_defaults
from hapi.pipelines.app.pipelines import Pipelines

logger = logging.getLogger(__name__)


class TestHAPIPipelines:
    @pytest.fixture(scope="function")
    def configuration(self):
        UserAgent.set_global("test")
        project_configs = [
            "core.yaml",
            "conflict_event.yaml",
            "food_security.yaml",
            "idps.yaml",
            "national_risk.yaml",
            "operational_presence.yaml",
            "population.yaml",
            "poverty_rate.yaml",
            "refugees_and_returnees.yaml",
            "wfp.yaml",
        ]
        project_config_dict = load_yamls(project_configs)
        project_config_dict = add_defaults(project_config_dict)
        Configuration._create(
            hdx_read_only=True,
            hdx_site="prod",
            project_config_dict=project_config_dict,
        )
        return Configuration.read()

    @pytest.fixture(scope="function")
    def folder(self):
        return join("tests", "fixtures")

    @pytest.fixture(scope="function")
    def pipelines(self, configuration, folder, themes_to_run):
        with ErrorsOnExit() as errors_on_exit:
            with temp_dir(
                "TestHAPIPipelines",
                delete_on_success=True,
                delete_on_failure=False,
            ) as temp_folder:
                db_uri = "postgresql+psycopg://postgres:postgres@localhost:5432/hapitest"
                logger.info(f"Connecting to database {db_uri}")
                with Database(
                    db_uri=db_uri,
                    recreate_schema=True,
                    prepare_fn=prepare_hapi_views,
                ) as database:
                    session = database.get_session()
                    today = parse_date("2023-10-11")
                    Read.create_readers(
                        temp_folder,
                        join(folder, "input"),
                        temp_folder,
                        False,
                        True,
                        today=today,
                    )
                    logger.info("Initialising pipelines")
                    pipelines = Pipelines(
                        configuration,
                        session,
                        today,
                        themes_to_run=themes_to_run,
                        errors_on_exit=errors_on_exit,
                        use_live=False,
                        countries_to_run=configuration["HAPI_countries"],
                    )
                    logger.info("Running pipelines")
                    pipelines.run()
                    logger.info("Writing to database")
                    pipelines.output()
                    logger.info("Writing debug output")
                    pipelines.debug(temp_folder)
                    pipelines.output_errors(flag_to_hdx=False)
                    count = session.scalar(select(func.count(DBLocation.id)))
                    check.equal(count, 249)
                    count = session.scalar(select(func.count(DBAdmin1.id)))
                    check.equal(count, 703)
                    count = session.scalar(select(func.count(DBAdmin2.id)))
                    check.equal(count, 5942)
                    count = session.scalar(select(func.count(DBSector.code)))
                    check.equal(count, 19)
                    count = session.scalar(select(func.count(DBCurrency.code)))
                    check.equal(count, 127)
                    yield pipelines

    @pytest.mark.parametrize(
        "themes_to_run", [{"population": ("AFG", "BFA", "MLI", "NGA", "TCD")}]
    )
    def test_population(self, configuration, folder, pipelines):
        session = pipelines.session
        count = session.scalar(select(func.count(DBDataset.hdx_id)))
        check.equal(count, 5)
        count = session.scalar(select(func.count(DBResource.hdx_id)))
        check.equal(count, 11)
        count = session.scalar(
            select(func.count(DBPopulation.resource_hdx_id))
        )
        check.equal(count, 8601)

    @pytest.mark.parametrize(
        "themes_to_run", [{"operational_presence": ("AFG", "MLI", "NGA")}]
    )
    def test_operational_presence(self, configuration, folder, pipelines):
        session = pipelines.session
        count = session.scalar(select(func.count(DBDataset.hdx_id)))
        check.equal(count, 3)
        count = session.scalar(select(func.count(DBResource.hdx_id)))
        check.equal(count, 3)
        count = session.scalar(select(func.count(DBOrg.acronym)))
        check.equal(count, 508)
        count = session.scalar(select(func.count(DBOrgType.code)))
        check.equal(count, 18)
        count = session.scalar(
            select(func.count(DBOperationalPresence.resource_hdx_id))
        )
        check.equal(count, 12926)
        # Comparison must be performed in this test method,
        # otherwise error details are not logged
        comparisons = check_org_mappings(pipelines)
        for lhs, rhs in comparisons:
            check.equal(lhs, rhs)

    @pytest.mark.parametrize("themes_to_run", [{"food_security": None}])
    def test_food_security(self, configuration, folder, pipelines):
        session = pipelines.session
        count = session.scalar(select(func.count(DBDataset.hdx_id)))
        check.equal(count, 1)
        count = session.scalar(select(func.count(DBResource.hdx_id)))
        check.equal(count, 3)
        count = session.scalar(
            select(func.count(DBFoodSecurity.resource_hdx_id))
        )
        check.equal(count, 36365)

    @pytest.mark.parametrize("themes_to_run", [{"humanitarian_needs": None}])
    def test_humanitarian_needs(self, configuration, folder, pipelines):
        session = pipelines.session
        count = session.scalar(select(func.count(DBDataset.hdx_id)))
        check.equal(count, 1)
        count = session.scalar(select(func.count(DBResource.hdx_id)))
        check.equal(count, 1)
        count = session.scalar(
            select(func.count(DBHumanitarianNeeds.resource_hdx_id))
        )
        # This test uses a cut down test file with MLI, SDN and UKR
        check.equal(count, 44938)

    @pytest.mark.parametrize("themes_to_run", [{"national_risk": None}])
    def test_national_risk(self, configuration, folder, pipelines):
        session = pipelines.session
        count = session.scalar(select(func.count(DBDataset.hdx_id)))
        check.equal(count, 1)
        count = session.scalar(select(func.count(DBResource.hdx_id)))
        check.equal(count, 1)
        count = session.scalar(
            select(func.count(DBNationalRisk.resource_hdx_id))
        )
        check.equal(count, 25)

    @pytest.mark.parametrize(
        "themes_to_run", [{"refugees_and_returnees": None}]
    )
    def test_refugees_and_returnees(self, configuration, folder, pipelines):
        session = pipelines.session
        count = session.scalar(select(func.count(DBDataset.hdx_id)))
        check.equal(count, 1)
        count = session.scalar(select(func.count(DBResource.hdx_id)))
        check.equal(count, 1)
        count = session.scalar(select(func.count(DBRefugees.resource_hdx_id)))
        check.equal(count, 570921)
        count = session.scalar(select(func.count(DBReturnees.resource_hdx_id)))
        check.equal(count, 5408)

    @pytest.mark.parametrize("themes_to_run", [{"idps": None}])
    def test_idps(self, configuration, folder, pipelines):
        session = pipelines.session
        count = session.scalar(select(func.count(DBResource.hdx_id)))
        check.equal(count, 1)
        count = session.scalar(select(func.count(DBDataset.hdx_id)))
        check.equal(count, 1)
        count = session.scalar(select(func.count(DBIDPs.resource_hdx_id)))
        check.equal(count, 35034)

    @pytest.mark.parametrize(
        "themes_to_run", [{"funding": ("AFG", "BFA", "UKR")}]
    )
    def test_funding(self, configuration, folder, pipelines):
        session = pipelines.session
        count = session.scalar(select(func.count(DBDataset.hdx_id)))
        check.equal(count, 3)
        count = session.scalar(select(func.count(DBResource.hdx_id)))
        check.equal(count, 3)
        count = session.scalar(select(func.count(DBFunding.resource_hdx_id)))
        check.equal(count, 56)

    @pytest.mark.parametrize(
        "themes_to_run", [{"conflict_event": ("BFA", "COL")}]
    )
    def test_conflict_event(self, configuration, folder, pipelines):
        session = pipelines.session
        count = session.scalar(select(func.count(DBDataset.hdx_id)))
        check.equal(count, 2)
        count = session.scalar(select(func.count(DBResource.hdx_id)))
        check.equal(count, 6)
        count = session.scalar(
            select(func.count(DBConflictEvent.resource_hdx_id))
        )
        check.equal(count, 313455)

    @pytest.mark.parametrize(
        "themes_to_run", [{"poverty_rate": ("AFG", "BFA")}]
    )
    def test_poverty_rate(self, configuration, folder, pipelines):
        # AFG has two timepoints, BFA has one
        session = pipelines.session
        count = session.scalar(select(func.count(DBDataset.hdx_id)))
        check.equal(count, 2)
        count = session.scalar(select(func.count(DBResource.hdx_id)))
        check.equal(count, 2)
        count = session.scalar(
            select(func.count(DBPovertyRate.resource_hdx_id))
        )
        check.equal(count, 29)

    @pytest.mark.parametrize("themes_to_run", [{"food_prices": None}])
    def test_food_prices(self, configuration, folder, pipelines):
        session = pipelines.session
        count = session.scalar(select(func.count(DBDataset.hdx_id)))
        check.equal(count, 1)
        count = session.scalar(select(func.count(DBResource.hdx_id)))
        check.equal(count, 1)
        count = session.scalar(select(func.count(DBWFPCommodity.code)))
        check.equal(count, 1077)
        count = session.scalar(select(func.count(DBWFPMarket.code)))
        check.equal(count, 4113)
        count = session.scalar(select(func.count(DBFoodPrice.resource_hdx_id)))
        check.equal(count, 31615)
