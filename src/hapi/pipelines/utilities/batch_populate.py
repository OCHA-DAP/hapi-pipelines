from typing import Dict, List

from sqlalchemy import insert
from sqlalchemy.orm import Session

_BATCH_SIZE = 1000


def batch_populate(rows: List[Dict], session: Session, DBTable):
    batches = range(len(rows) // _BATCH_SIZE + 1)
    for batch in batches:
        start_row = batch * _BATCH_SIZE
        end_row = start_row + _BATCH_SIZE
        batch_rows = rows[start_row:end_row]
        session.execute(insert(DBTable), batch_rows)
    session.commit()
