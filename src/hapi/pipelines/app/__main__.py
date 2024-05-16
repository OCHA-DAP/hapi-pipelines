"""Entry point to start HAPI pipelines"""

import argparse
import logging
from os import getenv
from typing import Dict, Optional

from hapi_schema.views import prepare_hapi_views
from hdx.api.configuration import Configuration
from hdx.database import Database
from hdx.database.dburi import (
    get_params_from_connection_uri,
)
from hdx.facades.keyword_arguments import facade
from hdx.scraper.utilities.reader import Read
from hdx.utilities.dateparse import now_utc
from hdx.utilities.dictandlist import args_to_dict
from hdx.utilities.easy_logging import setup_logging
from hdx.utilities.errors_onexit import ErrorsOnExit
from hdx.utilities.path import temp_dir
from hdx.utilities.typehint import ListTuple

from hapi.pipelines._version import __version__
from hapi.pipelines.app import load_yamls
from hapi.pipelines.app.pipelines import Pipelines
from hapi.pipelines.utilities.process_config_defaults import add_defaults

setup_logging(
    console_log_level="INFO",
    log_file="warnings_errors.log",
    file_log_level="WARNING",
)
logger = logging.getLogger(__name__)


lookup = "hapi-pipelines"


def parse_args():
    parser = argparse.ArgumentParser(description="HAPI pipelines")
    parser.add_argument("-hk", "--hdx-key", default=None, help="HDX api key")
    parser.add_argument("-ua", "--user-agent", default=None, help="user agent")
    parser.add_argument("-pp", "--preprefix", default=None, help="preprefix")
    parser.add_argument(
        "-hs", "--hdx-site", default=None, help="HDX site to use"
    )
    parser.add_argument(
        "-db", "--db-uri", default=None, help="Database connection string"
    )
    parser.add_argument(
        "-dp",
        "--db-params",
        default=None,
        help="Database connection parameters. Overrides --db-uri.",
    )
    parser.add_argument("-th", "--themes", default=None, help="Themes to run")
    parser.add_argument(
        "-sc", "--scrapers", default=None, help="Scrapers to run"
    )
    parser.add_argument(
        "-s",
        "--save",
        default=False,
        action="store_true",
        help="Save data for testing",
    )
    parser.add_argument(
        "-usv",
        "--use-saved",
        default=False,
        action="store_true",
        help="Use saved data",
    )
    return parser.parse_args()


def main(
    db_uri: Optional[str] = None,
    db_params: Optional[str] = None,
    themes_to_run: Optional[Dict] = None,
    scrapers_to_run: Optional[ListTuple[str]] = None,
    save: bool = False,
    use_saved: bool = False,
    **ignore,
) -> None:
    """Run HAPI. Either a database connection string (db_uri) or database
    connection parameters (db_params) can be supplied. If neither is supplied, a local
    SQLite database with filename "hapi.db" is assumed.

    Args:
        db_uri (Optional[str]): Database connection URI. Defaults to None.
        db_params (Optional[str]): Database connection parameters. Defaults to None.
        themes_to_run (Optional[Dict[str]]): Themes to run. Defaults to None (all themes).
        scrapers_to_run (Optional[ListTuple[str]]): Scrapers to run. Defaults to None (all scrapers).
        save (bool): Whether to save state for testing. Defaults to False.
        use_saved (bool): Whether to use saved state for testing. Defaults to False.

    Returns:
        None
    """
    logger.info(f"##### {lookup} version {__version__} ####")
    if db_params:
        params = args_to_dict(db_params)
    else:
        if not db_uri:
            db_uri = (
                "postgresql+psycopg://postgres:postgres@localhost:5432/hapi"
            )
        params = get_params_from_connection_uri(db_uri)
    if "recreate_schema" not in params:
        params["recreate_schema"] = True
    if "prepare_fn" not in params:
        params["prepare_fn"] = prepare_hapi_views
    logger.info(f"> Database parameters: {params}")
    configuration = Configuration.read()
    with ErrorsOnExit() as errors_on_exit:
        with temp_dir() as temp_folder:
            with Database(**params) as database:
                session = database.get_session()
                today = now_utc()
                Read.create_readers(
                    temp_folder,
                    "saved_data",
                    temp_folder,
                    save,
                    use_saved,
                    hdx_auth=configuration.get_api_key(),
                    today=today,
                )
                if scrapers_to_run:
                    logger.info(f"Updating only scrapers: {scrapers_to_run}")
                pipelines = Pipelines(
                    configuration,
                    session,
                    today,
                    themes_to_run,
                    scrapers_to_run,
                    errors_on_exit,
                )
                pipelines.run()
                pipelines.output()
    logger.info("HAPI pipelines completed!")


if __name__ == "__main__":
    args = parse_args()
    hdx_key = args.hdx_key
    if hdx_key is None:
        hdx_key = getenv("HDX_KEY")
    user_agent = args.user_agent
    if user_agent is None:
        user_agent = getenv("USER_AGENT")
        if user_agent is None:
            user_agent = "hapi-pipelines"
    preprefix = args.preprefix
    if preprefix is None:
        preprefix = getenv("PREPREFIX")
    hdx_site = args.hdx_site
    if hdx_site is None:
        hdx_site = getenv("HDX_SITE", "prod")
    db_uri = args.db_uri
    if db_uri is None:
        db_uri = getenv("DB_URI")
    if db_uri and "://" not in db_uri:
        db_uri = f"postgresql://{db_uri}"
    if args.themes:
        themes_to_run = {}
        for theme in args.themes.split(","):
            theme_strs = theme.split(":")
            if len(theme_strs) == 1:
                themes_to_run[theme_strs[0]] = None
            else:
                themes_to_run[theme_strs[0]] = theme_strs[1]
    else:
        themes_to_run = None
    if args.scrapers:
        scrapers_to_run = args.scrapers.split(",")
    else:
        scrapers_to_run = None
    project_configs = [
        "core.yaml",
        "food_security.yaml",
        "funding.yaml",
        "national_risk.yaml",
        "operational_presence.yaml",
        "population.yaml",
        "refugees.yaml",
    ]
    project_config_dict = load_yamls(project_configs)
    project_config_dict = add_defaults(project_config_dict)
    facade(
        main,
        hdx_key=hdx_key,
        user_agent=user_agent,
        preprefix=preprefix,
        hdx_site=hdx_site,
        project_config_dict=project_config_dict,
        db_uri=db_uri,
        db_params=args.db_params,
        themes_to_run=themes_to_run,
        scrapers_to_run=scrapers_to_run,
        save=args.save,
        use_saved=args.use_saved,
    )
