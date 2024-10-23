"""Entry point to start HAPI pipelines"""

import argparse
import logging
from os import getenv
from os.path import expanduser, join
from typing import Dict, Optional

from hapi_schema.views import prepare_hapi_views
from hdx.api.configuration import Configuration
from hdx.database import Database
from hdx.database.dburi import (
    get_params_from_connection_uri,
)
from hdx.facades.keyword_arguments import facade
from hdx.scraper.framework.utilities import string_params_to_dict
from hdx.scraper.framework.utilities.reader import Read
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
    parser.add_argument(
        "-db", "--db-uri", default=None, help="Database connection string"
    )
    parser.add_argument(
        "-dp",
        "--db-params",
        default=None,
        help="Database connection parameters. Overrides --db-uri.",
    )
    th_help = (
        "Themes to run. Can pass a single theme or multiple themes "
        "separated by commas. You can also append a colon to the "
        "theme name and pass ISO3s separated by a pipe. For example: "
        "population:AFG|COD,poverty_rate:BFA,funding"
    )
    parser.add_argument("-th", "--themes", default=None, help=th_help)
    parser.add_argument(
        "-sc", "--scrapers", default=None, help="Scrapers to run"
    )
    parser.add_argument(
        "-ba",
        "--basic_auths",
        default=None,
        help="Basic Auth Credentials for accessing scraper APIs",
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
    parser.add_argument(
        "-dbg",
        "--debug",
        default=False,
        action="store_true",
        help="Debug",
    )
    parser.add_argument(
        "-flg",
        "--flag-to-hdx",
        default=False,
        action="store_true",
        help="Flag any found errors in HDX metadata",
    )
    return parser.parse_args()


def main(
    db_uri: Optional[str] = None,
    db_params: Optional[str] = None,
    themes_to_run: Optional[Dict] = None,
    scrapers_to_run: Optional[ListTuple[str]] = None,
    basic_auths: Optional[Dict[str, str]] = None,
    save: bool = False,
    use_saved: bool = False,
    debug: bool = False,
    flag_to_hdx: bool = False,
    **ignore,
) -> None:
    """Run HAPI. Either a database connection string (db_uri) or database
    connection parameters (db_params) can be supplied. If neither is supplied, a local
    SQLite database with filename "hapi.db" is assumed. basic_auths is a
    dictionary of form {"scraper name": "auth", ...}.

    Args:
        db_uri (Optional[str]): Database connection URI. Defaults to None.
        db_params (Optional[str]): Database connection parameters. Defaults to None.
        themes_to_run (Optional[Dict]): Themes to run. Defaults to None (all themes).
        scrapers_to_run (Optional[ListTuple[str]]): Scrapers to run. Defaults to None (all scrapers).
        basic_auths (Optional[Dict[str, str]]): Basic authorisations
        save (bool): Whether to save state for testing. Defaults to False.
        use_saved (bool): Whether to use saved state for testing. Defaults to False.
        debug (bool): Whether to output debug info. Defaults to False.
        flag_to_hdx (bool): Whether to flag any errors in HDX metadata. Defaults to False.

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
                    basic_auths=basic_auths,
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
                pipelines.output_errors(flag_to_hdx)
                if debug:
                    pipelines.debug("debug")
    logger.info("HAPI pipelines completed!")


if __name__ == "__main__":
    args = parse_args()
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
                # Split values by pipe for multiple countries
                values = theme_strs[1].split("|")
                themes_to_run[theme_strs[0]] = (
                    values if len(values) > 1 else values[0]
                )
    else:
        themes_to_run = None
    if args.scrapers:
        scrapers_to_run = args.scrapers.split(",")
    else:
        scrapers_to_run = None
    ba = args.basic_auths
    if ba is None:
        ba = getenv("BASIC_AUTHS")
    if ba:
        basic_auths = string_params_to_dict(ba)
    else:
        basic_auths = None
    project_configs = [
        "conflict_event.yaml",
        "core.yaml",
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
    facade(
        main,
        user_agent_config_yaml=join(expanduser("~"), ".useragents.yaml"),
        user_agent_lookup=lookup,
        project_config_dict=project_config_dict,
        db_uri=db_uri,
        db_params=args.db_params,
        themes_to_run=themes_to_run,
        scrapers_to_run=scrapers_to_run,
        basic_auths=basic_auths,
        save=args.save,
        use_saved=args.use_saved,
        debug=args.debug,
        flag_to_hdx=args.flag_to_hdx,
    )
