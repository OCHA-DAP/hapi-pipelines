"""Functions specific to the refugees theme."""

from logging import getLogger
from typing import Dict

from hapi_schema.db_idps import DBIDPs
from sqlalchemy.orm import Session

from . import admins
from .base_uploader import BaseUploader
from .metadata import Metadata

logger = getLogger(__name__)


class IDPs(BaseUploader):
    def __init__(
        self,
        session: Session,
        metadata: Metadata,
        admins: admins.Admins,
        results: Dict,
    ):
        super().__init__(session)
        self._metadata = metadata
        self._admins = admins
        self._results = results

    def populate(self) -> None:
        logger.info("Populating IDPs table")
        # self._results is a dictionary where the keys are the HDX dataset ID and the
        # values are a dictionary with keys containing HDX metadata plus a "results" key
        # containing the results, stored in a dictionary with admin levels as keys.
        # There is only one dataset for now in the results dictionary, take first value
        # (popitem returns a tuple with (key, value) so take the value)
        dataset = self._results.popitem()[1]
        for admin_level, admin_results in dataset["results"].items():
            # admin_results contains the keys "headers", "values", and "hapi_resource_metadata".
            # admin_results["values"] is a list of dictionaries of the format:
            # [{AFG: [1, 2], BFA: [3, 4]}, {AFG: [A, B], BFA: [C, D]} etc
            # So the way to get info from it is values[i_hdx_key][pcode][i] where
            # i is just an iterator for the number of rows for that particular p-code
            resource_id = admin_results["hapi_resource_metadata"]["hdx_id"]
            hxl_tags = admin_results["headers"][1]
            values = admin_results["values"]
            admin_codes = values[0].keys()
            for admin_code in admin_codes:
                admin2_code = admins.get_admin2_code_based_on_level(
                    admin_code=admin_code, admin_level=admin_level
                )
                for row in zip(
                    *[
                        values[hxl_tags.index(tag)][admin_code]
                        for tag in hxl_tags
                    ]
                ):
                    # Keeping these defined outside of the row for now
                    # as we may need to check for duplicates in the future
                    admin2_ref = self._admins.admin2_data[admin2_code]
                    assessment_type = row[hxl_tags.index("#assessment+type")]
                    date_reported = row[hxl_tags.index("#date+reported")]
                    reporting_round = row[hxl_tags.index("#round+code")]
                    operation = row[hxl_tags.index("#operation+name")]
                    idps_row = DBIDPs(
                        resource_hdx_id=resource_id,
                        admin2_ref=admin2_ref,
                        assessment_type=assessment_type,
                        reporting_round=reporting_round,
                        operation=operation,
                        population=row[hxl_tags.index("#affected+idps")],
                        reference_period_start=date_reported,
                        reference_period_end=date_reported,
                    )
                    self._session.add(idps_row)
        self._session.commit()
