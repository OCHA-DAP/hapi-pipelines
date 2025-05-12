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
from hapi_schema.db_operational_presence import (
    DBOperationalPresence,
)
from hapi_schema.db_org import DBOrg
from hapi_schema.db_org_type import DBOrgType
from hapi_schema.db_population import DBPopulation
from hapi_schema.db_poverty_rate import DBPovertyRate
from hapi_schema.db_rainfall import DBRainfall
from hapi_schema.db_refugees import DBRefugees
from hapi_schema.db_resource import DBResource
from hapi_schema.db_returnees import DBReturnees
from hapi_schema.db_sector import DBSector
from hapi_schema.db_wfp_commodity import DBWFPCommodity
from hapi_schema.db_wfp_market import DBWFPMarket
from hapi_schema.views import prepare_hapi_views
from hdx.api.configuration import Configuration
from hdx.api.utilities.hdx_error_handler import HDXErrorHandler
from hdx.database import Database
from hdx.scraper.framework.utilities.reader import Read
from hdx.utilities.dateparse import parse_date
from hdx.utilities.path import temp_dir
from hdx.utilities.useragent import UserAgent
from pytest_check import check
from sqlalchemy import func, select

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
            "national_risk.yaml",
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
        with HDXErrorHandler() as error_handler:
            with temp_dir(
                "TestHAPIPipelines",
                delete_on_success=True,
                delete_on_failure=False,
            ) as temp_folder:
                db_uri = (
                    "postgresql+psycopg://postgres:postgres@localhost:5432/hapitest"
                )
                logger.info(f"Connecting to database {db_uri}")
                with Database(
                    db_uri=db_uri,
                    recreate_schema=True,
                    prepare_fn=prepare_hapi_views,
                ) as database:
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
                        database,
                        today,
                        themes_to_run=themes_to_run,
                        error_handler=error_handler,
                        use_live=False,
                    )
                    logger.info("Running pipelines")
                    pipelines.run()
                    logger.info("Writing to database")
                    pipelines.output()
                    yield pipelines

    @pytest.mark.parametrize("themes_to_run", [{"nothing": None}])
    def test_admin(self, configuration, folder, pipelines):
        session = pipelines._database.get_session()
        count = session.scalar(select(func.count(DBLocation.id)))
        check.equal(count, 249)
        count = session.scalar(select(func.count(DBAdmin1.id)))
        check.equal(count, 2704)
        count = session.scalar(select(func.count(DBAdmin2.id)))
        check.equal(count, 33391)
        admins = pipelines._admins
        max_admin_level = admins.get_max_admin_from_hxltags(
            [
                "#A",
                "#B",
                "adm1+name",
                "#c",
                "#lala5+name",
                "#adm3+name",
                "#e",
                "#adm2+name",
            ]
        )
        check.equal(max_admin_level, 3)
        row = {"a": 1, "Country ISO3": "AFG"}
        hxltag_to_header = {
            "#lala": "a",
            "#country+code": "Country ISO3",
            "#adm1+name": "",
            "#adm2+name": "",
            "#adm3+name": "",
        }
        admin_level = admins.get_admin_level_from_row(
            hxltag_to_header, row, max_admin_level
        )
        check.equal(admin_level, 0)
        hxltag_to_header["#adm1+name"] = "Admin 1 Name"
        row = {"a": 1, "Country ISO3": "AFG", "Admin 1 Name": "ABC"}
        admin_level = admins.get_admin_level_from_row(
            hxltag_to_header, row, max_admin_level
        )
        check.equal(admin_level, 1)
        hxltag_to_header["#adm2+name"] = "Admin 2 Name"
        hxltag_to_header["#adm3+name"] = "Admin 3 Name"
        row = {
            "a": 1,
            "Country ISO3": "AFG",
            "Admin 3 Name": "ABC",
            "Admin 2 Name": "ABC",
        }
        admin_level = admins.get_admin_level_from_row(
            hxltag_to_header, row, max_admin_level
        )
        check.equal(admin_level, 3)
        hxltag_to_header["#adm1+code"] = "Admin 1 PCode"
        hxltag_to_header["#adm2+code"] = "Admin 2 PCode"
        hxltag_to_header["#adm3+code"] = "Admin 3 PCode"
        row = {
            "a": 1,
            "Country ISO3": "AFG",
            "Admin 1 PCode": "",
            "Admin 2 PCode": "",
            "Admin 3 PCode": "",
        }
        admin2_ref = admins.get_admin2_ref_from_row(
            hxltag_to_header, row, "Test", "Test", 3
        )
        check.equal(admin2_ref, None)
        admin2_ref = admins.get_admin2_ref_from_row(
            hxltag_to_header, row, "Test", "Test", 2
        )
        code = session.scalar(select(DBAdmin2.code).where(DBAdmin2.id == admin2_ref))
        assert code == "AFG-XXX-XXX"
        row["Admin 1 Name"] = "ABC"
        admin2_ref = admins.get_admin2_ref_from_row(
            hxltag_to_header, row, "Test", "Test", 2
        )
        code = session.scalar(select(DBAdmin2.code).where(DBAdmin2.id == admin2_ref))
        assert code == "AFG-XXX-XXX"
        del row["Admin 1 Name"]
        row["Admin 1 PCode"] = "AF01"
        admin2_ref = admins.get_admin2_ref_from_row(
            hxltag_to_header, row, "Test", "Test", 2
        )
        code = session.scalar(select(DBAdmin2.code).where(DBAdmin2.id == admin2_ref))
        assert code == "AF01-XXX"
        row["Admin 1 Name"] = "ABC"
        admin2_ref = admins.get_admin2_ref_from_row(
            hxltag_to_header, row, "Test", "Test", 2
        )
        code = session.scalar(select(DBAdmin2.code).where(DBAdmin2.id == admin2_ref))
        assert code == "AF01-XXX"
        row["Admin 2 Name"] = "ABC"
        admin2_ref = admins.get_admin2_ref_from_row(
            hxltag_to_header, row, "Test", "Test", 2
        )
        code = session.scalar(select(DBAdmin2.code).where(DBAdmin2.id == admin2_ref))
        assert code == "AF01-XXX"
        del row["Admin 1 Name"]
        del row["Admin 2 Name"]
        row["Admin 2 PCode"] = "AF0101"
        admin2_ref = admins.get_admin2_ref_from_row(
            hxltag_to_header, row, "Test", "Test", 2
        )
        code = session.scalar(select(DBAdmin2.code).where(DBAdmin2.id == admin2_ref))
        assert code == "AF0101"
        row["Admin 1 Name"] = "ABC"
        admin2_ref = admins.get_admin2_ref_from_row(
            hxltag_to_header, row, "Test", "Test", 2
        )
        code = session.scalar(select(DBAdmin2.code).where(DBAdmin2.id == admin2_ref))
        assert code == "AF0101"
        row["Admin 2 Name"] = "ABC"
        admin2_ref = admins.get_admin2_ref_from_row(
            hxltag_to_header, row, "Test", "Test", 2
        )
        code = session.scalar(select(DBAdmin2.code).where(DBAdmin2.id == admin2_ref))
        assert code == "AF0101"

    @pytest.mark.parametrize("themes_to_run", [{"nothing": None}])
    def test_sector(self, configuration, folder, pipelines):
        session = pipelines._database.get_session()
        count = session.scalar(select(func.count(DBSector.code)))
        check.equal(count, 19)

    @pytest.mark.parametrize("themes_to_run", [{"population": None}])
    def test_population(self, configuration, folder, pipelines):
        session = pipelines._database.get_session()
        count = session.scalar(select(func.count(DBDataset.hdx_id)))
        check.equal(count, 2)
        count = session.scalar(select(func.count(DBResource.hdx_id)))
        check.equal(count, 6)
        count = session.scalar(select(func.count(DBPopulation.resource_hdx_id)))
        check.equal(count, 12906)

    @pytest.mark.parametrize("themes_to_run", [{"operational_presence": None}])
    def test_operational_presence(self, configuration, folder, pipelines):
        session = pipelines._database.get_session()
        count = session.scalar(select(func.count(DBDataset.hdx_id)))
        check.equal(count, 26)
        count = session.scalar(select(func.count(DBResource.hdx_id)))
        check.equal(count, 25)
        count = session.scalar(select(func.count(DBOrg.acronym)))
        check.equal(count, 2585)
        count = session.scalar(select(func.count(DBOrgType.code)))
        check.equal(count, 18)
        count = session.scalar(
            select(func.count(DBOperationalPresence.resource_hdx_id))
        )
        check.equal(count, 43524)

    @pytest.mark.parametrize("themes_to_run", [{"food_security": None}])
    def test_food_security(self, configuration, folder, pipelines):
        session = pipelines._database.get_session()
        count = session.scalar(select(func.count(DBDataset.hdx_id)))
        check.equal(count, 1)
        count = session.scalar(select(func.count(DBResource.hdx_id)))
        check.equal(count, 3)
        count = session.scalar(select(func.count(DBFoodSecurity.resource_hdx_id)))
        check.equal(count, 19768)

    @pytest.mark.parametrize("themes_to_run", [{"humanitarian_needs": None}])
    def test_humanitarian_needs(self, configuration, folder, pipelines):
        session = pipelines._database.get_session()
        count = session.scalar(select(func.count(DBDataset.hdx_id)))
        check.equal(count, 1)
        count = session.scalar(select(func.count(DBResource.hdx_id)))
        check.equal(count, 2)
        count = session.scalar(select(func.count(DBHumanitarianNeeds.resource_hdx_id)))
        # This test uses a cut down test file
        check.equal(count, 16122)

    @pytest.mark.parametrize("themes_to_run", [{"national_risk": None}])
    def test_national_risk(self, configuration, folder, pipelines):
        session = pipelines._database.get_session()
        count = session.scalar(select(func.count(DBDataset.hdx_id)))
        check.equal(count, 1)
        count = session.scalar(select(func.count(DBResource.hdx_id)))
        check.equal(count, 1)
        count = session.scalar(select(func.count(DBNationalRisk.resource_hdx_id)))
        check.equal(count, 191)

    @pytest.mark.parametrize("themes_to_run", [{"refugees": None}])
    def test_refugees(self, configuration, folder, pipelines):
        session = pipelines._database.get_session()
        count = session.scalar(select(func.count(DBDataset.hdx_id)))
        check.equal(count, 1)
        count = session.scalar(select(func.count(DBResource.hdx_id)))
        check.equal(count, 1)
        count = session.scalar(select(func.count(DBRefugees.resource_hdx_id)))
        check.equal(count, 43888)

    @pytest.mark.parametrize("themes_to_run", [{"returnees": None}])
    def test_returnees(self, configuration, folder, pipelines):
        session = pipelines._database.get_session()
        count = session.scalar(select(func.count(DBDataset.hdx_id)))
        check.equal(count, 1)
        count = session.scalar(select(func.count(DBResource.hdx_id)))
        check.equal(count, 1)
        count = session.scalar(select(func.count(DBReturnees.resource_hdx_id)))
        check.equal(count, 13988)

    @pytest.mark.parametrize("themes_to_run", [{"idps": None}])
    def test_idps(self, configuration, folder, pipelines):
        session = pipelines._database.get_session()
        count = session.scalar(select(func.count(DBResource.hdx_id)))
        check.equal(count, 1)
        count = session.scalar(select(func.count(DBDataset.hdx_id)))
        check.equal(count, 1)
        count = session.scalar(select(func.count(DBIDPs.resource_hdx_id)))
        check.equal(count, 19383)

    @pytest.mark.parametrize("themes_to_run", [{"funding": None}])
    def test_funding(self, configuration, folder, pipelines):
        session = pipelines._database.get_session()
        count = session.scalar(select(func.count(DBDataset.hdx_id)))
        check.equal(count, 3)
        count = session.scalar(select(func.count(DBResource.hdx_id)))
        check.equal(count, 3)
        count = session.scalar(select(func.count(DBFunding.resource_hdx_id)))
        check.equal(count, 152)

    @pytest.mark.parametrize("themes_to_run", [{"conflict_event": None}])
    def test_conflict_event(self, configuration, folder, pipelines):
        session = pipelines._database.get_session()
        count = session.scalar(select(func.count(DBDataset.hdx_id)))
        check.equal(count, 3)
        count = session.scalar(select(func.count(DBResource.hdx_id)))
        check.equal(count, 3)
        count = session.scalar(select(func.count(DBConflictEvent.resource_hdx_id)))
        check.equal(count, 28740)

    @pytest.mark.parametrize("themes_to_run", [{"poverty_rate": None}])
    def test_poverty_rate(self, configuration, folder, pipelines):
        # AFG has two timepoints, BFA has one
        session = pipelines._database.get_session()
        count = session.scalar(select(func.count(DBDataset.hdx_id)))
        check.equal(count, 1)
        count = session.scalar(select(func.count(DBResource.hdx_id)))
        check.equal(count, 2)
        count = session.scalar(select(func.count(DBPovertyRate.resource_hdx_id)))
        check.equal(count, 3166)

    @pytest.mark.parametrize("themes_to_run", [{"food_prices": None}])
    def test_food_prices(self, configuration, folder, pipelines):
        session = pipelines._database.get_session()
        count = session.scalar(select(func.count(DBDataset.hdx_id)))
        check.equal(count, 1)
        count = session.scalar(select(func.count(DBResource.hdx_id)))
        check.equal(count, 1)
        count = session.scalar(select(func.count(DBCurrency.code)))
        check.equal(count, 127)
        count = session.scalar(select(func.count(DBWFPCommodity.code)))
        check.equal(count, 1135)
        count = session.scalar(select(func.count(DBWFPMarket.code)))
        check.equal(count, 9739)
        count = session.scalar(select(func.count(DBFoodPrice.resource_hdx_id)))
        check.equal(count, 6713)

    @pytest.mark.parametrize("themes_to_run", [{"rainfall": None}])
    def test_rainfall(self, configuration, folder, pipelines):
        session = pipelines._database.get_session()
        count = session.scalar(select(func.count(DBDataset.hdx_id)))
        check.equal(count, 1)
        count = session.scalar(select(func.count(DBResource.hdx_id)))
        check.equal(count, 1)
        count = session.scalar(select(func.count(DBRainfall.resource_hdx_id)))
        check.equal(count, 3192)
