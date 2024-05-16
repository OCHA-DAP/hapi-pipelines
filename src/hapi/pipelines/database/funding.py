"""Functions specific to the funding theme."""

from logging import getLogger
from typing import Dict

from hapi_schema.db_funding import DBFunding
from hdx.utilities.dateparse import parse_date
from sqlalchemy.orm import Session

from . import locations
from .base_uploader import BaseUploader
from .metadata import Metadata

logger = getLogger(__name__)


class Funding(BaseUploader):
    def __init__(
        self,
        session: Session,
        metadata: Metadata,
        locations: locations,
        results: Dict,
    ):
        super().__init__(session)
        self._metadata = metadata
        self._locations = locations
        self._results = results

    def populate(self):
        logger.info("Populating funding table")
        for dataset in self._results.values():
            for admin_level, admin_results in dataset["results"].items():
                resource_id = admin_results["hapi_resource_metadata"]["hdx_id"]
                hxl_tags = admin_results["headers"][1]
                values = admin_results["values"]
                appeal_code_i = hxl_tags.index("#activity+appeal+id+external")
                appeal_name_i = hxl_tags.index("#activity+appeal+name")
                appeal_type_i = hxl_tags.index("#activity+appeal+type+name")
                requirements_usd_i = hxl_tags.index(
                    "#value+funding+required+usd"
                )
                funding_usd_i = hxl_tags.index("#value+funding+total+usd")
                funding_pct_i = hxl_tags.index("#value+funding+pct")
                reference_period_start_i = hxl_tags.index("#date+start")
                reference_period_end_i = hxl_tags.index("#date+end")

                for admin_code in values[0].keys():
                    for irow in range(len(values[0][admin_code])):
                        appeal_code = values[appeal_code_i][admin_code][irow]
                        reference_period_start = parse_date(
                            values[reference_period_start_i][admin_code][irow]
                        )
                        reference_period_end = parse_date(
                            values[reference_period_end_i][admin_code][irow]
                        )
                        if reference_period_start > reference_period_end:
                            logger.error(
                                f"Date misalignment in funding data for {appeal_code} in {admin_code}"
                            )
                            continue
                        funding_row = DBFunding(
                            resource_hdx_id=resource_id,
                            location_ref=self._locations.data[admin_code],
                            appeal_code=appeal_code,
                            appeal_name=values[appeal_name_i][admin_code][
                                irow
                            ],
                            appeal_type=values[appeal_type_i][admin_code][
                                irow
                            ],
                            requirements_usd=values[requirements_usd_i][
                                admin_code
                            ][irow],
                            funding_usd=values[funding_usd_i][admin_code][
                                irow
                            ],
                            funding_pct=values[funding_pct_i][admin_code][
                                irow
                            ],
                            reference_period_start=reference_period_start,
                            reference_period_end=reference_period_end,
                        )

                        self._session.add(funding_row)
        self._session.commit()
