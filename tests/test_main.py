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
from hapi_schema.db_location import DBLocation
from hapi_schema.db_national_risk import DBNationalRisk
from hapi_schema.db_operational_presence import DBOperationalPresence
from hapi_schema.db_org import DBOrg
from hapi_schema.db_org_type import DBOrgType
from hapi_schema.db_population import DBPopulation
from hapi_schema.db_poverty_rate import DBPovertyRate
from hapi_schema.db_refugees import DBRefugees
from hapi_schema.db_resource import DBResource
from hapi_schema.db_sector import DBSector
from hapi_schema.db_wfp_commodity import DBWFPCommodity
from hapi_schema.db_wfp_market import DBWFPMarket
from hapi_schema.views import prepare_hapi_views
from hdx.api.configuration import Configuration
from hdx.database import Database
from hdx.scraper.utilities.reader import Read
from hdx.utilities.dateparse import parse_date
from hdx.utilities.errors_onexit import ErrorsOnExit
from hdx.utilities.path import temp_dir
from hdx.utilities.useragent import UserAgent
from pytest_check import check
from sqlalchemy import func, select

from hapi.pipelines.app import load_yamls
from hapi.pipelines.app.__main__ import add_defaults
from hapi.pipelines.app.pipelines import Pipelines
from hapi.pipelines.database.org import OrgInfo

logger = logging.getLogger(__name__)


class TestHAPIPipelines:
    @pytest.fixture(scope="function")
    def configuration(self):
        UserAgent.set_global("test")
        project_configs = [
            "core.yaml",
            "conflict_event.yaml",
            "food_security.yaml",
            "funding.yaml",
            "national_risk.yaml",
            "operational_presence.yaml",
            "population.yaml",
            "poverty_rate.yaml",
            "refugees.yaml",
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

    def test_pipelines(self, configuration, folder):
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
                    themes_to_run = {
                        "population": ("AFG", "BFA", "MLI", "NGA", "TCD"),
                        "operational_presence": ("AFG", "MLI", "NGA"),
                        "food_security": None,
                        "humanitarian_needs": None,
                        "national_risk": None,
                        "refugees": None,
                        "funding": ("AFG", "BFA", "UKR"),
                        "food_prices": None,
                        "conflict_event": ("BFA", "GTM"),
                        "poverty_rate": (
                            "AFG",
                            "BFA",
                        ),  # AFG has two timepoints, BFA has one
                    }
                    pipelines = Pipelines(
                        configuration,
                        session,
                        today,
                        themes_to_run=themes_to_run,
                        errors_on_exit=errors_on_exit,
                        use_live=False,
                    )
                    logger.info("Running pipelines")
                    pipelines.run()
                    logger.info("Writing to database")
                    pipelines.output()
                    logger.info("Writing debug output")
                    pipelines.debug(temp_folder)

                    count = session.scalar(
                        select(func.count(DBResource.hdx_id))
                    )
                    check.equal(count, 36)
                    count = session.scalar(
                        select(func.count(DBDataset.hdx_id))
                    )
                    check.equal(count, 23)
                    count = session.scalar(select(func.count(DBLocation.id)))
                    check.equal(count, 249)
                    count = session.scalar(select(func.count(DBAdmin1.id)))
                    check.equal(count, 703)
                    count = session.scalar(select(func.count(DBAdmin2.id)))
                    check.equal(count, 6160)
                    count = session.scalar(select(func.count(DBOrg.acronym)))
                    check.equal(count, 565)
                    count = session.scalar(select(func.count(DBOrgType.code)))
                    check.equal(count, 18)
                    count = session.scalar(select(func.count(DBSector.code)))
                    check.equal(count, 19)
                    count = session.scalar(select(func.count(DBCurrency.code)))
                    check.equal(count, 127)
                    count = session.scalar(
                        select(func.count(DBWFPCommodity.code))
                    )
                    check.equal(count, 1077)
                    count = session.scalar(
                        select(func.count(DBWFPMarket.code))
                    )
                    check.equal(count, 4100)
                    count = session.scalar(
                        select(func.count(DBPopulation.resource_hdx_id))
                    )
                    check.equal(count, 54123)
                    count = session.scalar(
                        select(
                            func.count(DBOperationalPresence.resource_hdx_id)
                        )
                    )
                    check.equal(count, 13478)
                    count = session.scalar(
                        select(func.count(DBFoodSecurity.resource_hdx_id))
                    )
                    check.equal(count, 100961)
                    count = session.scalar(
                        select(func.count(DBHumanitarianNeeds.resource_hdx_id))
                    )
                    check.equal(count, 139085)
                    count = session.scalar(
                        select(func.count(DBNationalRisk.resource_hdx_id))
                    )
                    check.equal(count, 25)
                    count = session.scalar(
                        select(func.count(DBRefugees.resource_hdx_id))
                    )
                    check.equal(count, 102726)
                    count = session.scalar(
                        select(func.count(DBFunding.resource_hdx_id))
                    )
                    check.equal(count, 56)
                    count = session.scalar(
                        select(func.count(DBConflictEvent.resource_hdx_id))
                    )
                    check.equal(count, 44646)
                    count = session.scalar(
                        select(func.count(DBPovertyRate.resource_hdx_id))
                    )
                    check.equal(count, 29)
                    count = session.scalar(
                        select(func.count(DBFoodPrice.resource_hdx_id))
                    )
                    check.equal(count, 31615)
                    org_map = pipelines.org._org_map
                    iom = OrgInfo(
                        "International Organization for Migration",
                        "international organization for migration",
                        "IOM",
                        "iom",
                        "447",
                        True,
                        True,
                    )
                    assert org_map[(None, "IOM")] == iom
                    assert org_map[(None, "iom")] == iom
                    assert (
                        org_map[
                            (
                                None,
                                "Organisation Internationale pour les Migrations",
                            )
                        ]
                        == iom
                    )
                    assert (
                        org_map[
                            (
                                None,
                                "organisation internationale pour les migrations",
                            )
                        ]
                        == iom
                    )

                    iom = OrgInfo(
                        "International Organization for Migration",
                        "international organization for migration",
                        "IOM",
                        "iom",
                        "447",
                        False,
                        False,
                    )
                    assert (
                        org_map[
                            (None, "International Organisation for Migrations")
                        ]
                        == iom
                    )
                    assert (
                        org_map[
                            (None, "international organisation for migrations")
                        ]
                        == iom
                    )
                    assert (
                        org_map[
                            (None, "INTERNATIONALE ORGANISATION FOR MIGRATION")
                        ]
                        == iom
                    )
                    assert (
                        org_map[
                            (None, "internationale organisation for migration")
                        ]
                        == iom
                    )
                    assert (
                        org_map[
                            (
                                None,
                                "Organisation Internationale des Migrations",
                            )
                        ]
                        == iom
                    )
                    assert (
                        org_map[
                            (
                                None,
                                "organisation internationale des migrations",
                            )
                        ]
                        == iom
                    )
                    assert (
                        org_map[
                            (
                                None,
                                "OIM - International Organization for Migration",
                            )
                        ]
                        == iom
                    )
                    assert (
                        org_map[
                            (
                                None,
                                "oim international organization for migration",
                            )
                        ]
                        == iom
                    )

                    unicef = OrgInfo(
                        "United Nations Children's Fund",
                        "united nations childrens fund",
                        "UNICEF",
                        "unicef",
                        "447",
                        True,
                        True,
                    )
                    assert (
                        org_map[(None, "United Nations Children's Fund")]
                        == unicef
                    )
                    assert (
                        org_map[(None, "united nations childrens fund")]
                        == unicef
                    )
                    assert org_map[(None, "UNICEF")] == unicef
                    assert org_map[(None, "unicef")] == unicef
                    assert (
                        org_map[
                            (None, "Fonds des Nations Unies pour l'Enfance")
                        ]
                        == unicef
                    )
                    assert (
                        org_map[
                            (None, "fonds des nations unies pour lenfance")
                        ]
                        == unicef
                    )
                    assert (
                        org_map[
                            (
                                None,
                                "UNICEF - Fondo de las Naciones Unidas para la Infancia",
                            )
                        ]
                        == unicef
                    )
                    assert (
                        org_map[
                            (
                                None,
                                "unicef fondo de las naciones unidas para la infancia",
                            )
                        ]
                        == unicef
                    )

                    unicef = OrgInfo(
                        "United Nations Children's Fund",
                        "united nations childrens fund",
                        "UNICEF",
                        "unicef",
                        "447",
                        False,
                        False,
                    )
                    assert (
                        org_map[
                            (None, "United Nations Children's Emergency Fund")
                        ]
                        == unicef
                    )
                    assert (
                        org_map[
                            (None, "united nations childrens emergency fund")
                        ]
                        == unicef
                    )
                    assert (
                        org_map[
                            (None, "Fond des Nations Unies pour l'Enfance")
                        ]
                        == unicef
                    )
                    assert (
                        org_map[(None, "fond des nations unies pour lenfance")]
                        == unicef
                    )
                    assert (
                        org_map[
                            (
                                None,
                                "United Nations International Childrens Emergency Fund",
                            )
                        ]
                        == unicef
                    )
                    assert (
                        org_map[
                            (
                                None,
                                "united nations international childrens emergency fund",
                            )
                        ]
                        == unicef
                    )

                    assert org_map[("AFG", "WEWORLD")] == OrgInfo(
                        "WEWORLD",
                        "weworld",
                        "WEWORLD",
                        "weworld",
                        None,
                        True,
                        False,
                    )

                    assert org_map[("NGA", "HECADF")] == OrgInfo(
                        "HECADF",
                        "hecadf",
                        "HECADF",
                        "hecadf",
                        "441",
                        True,
                        True,
                    )
