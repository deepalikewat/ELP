import os
import logging
from datetime import date, datetime
from decimal import Decimal

import httpx
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from models.customer import Customer

log = logging.getLogger(__name__)

MOCK_SERVER_URL = os.getenv("MOCK_SERVER_URL", "http://localhost:5000")
PAGE_SIZE = 50  # fetch in chunks; keeps memory bounded for larger datasets


def fetch_all_customers() -> list[dict]:
    """
    Walk through every page of the Flask mock API and collect all records.
    Stops when an empty page is returned.
    """
    all_records: list[dict] = []
    page = 1

    with httpx.Client(timeout=30.0) as client:
        while True:
            url = f"{MOCK_SERVER_URL}/api/customers"
            resp = client.get(url, params={"page": page, "limit": PAGE_SIZE})
            resp.raise_for_status()

            body = resp.json()
            batch = body.get("data", [])
            if not batch:
                break

            all_records.extend(batch)
            log.info("Fetched page %d — got %d records", page, len(batch))

            # no more pages left
            if len(all_records) >= body.get("total", 0):
                break
            page += 1

    log.info("Total records fetched from mock server: %d", len(all_records))
    return all_records


def _coerce_row(raw: dict) -> dict:
    """Normalise types coming from JSON so they match our SQLAlchemy model."""
    row = dict(raw)  # shallow copy

    dob = row.get("date_of_birth")
    if isinstance(dob, str) and dob:
        row["date_of_birth"] = date.fromisoformat(dob)

    created = row.get("created_at")
    if isinstance(created, str) and created:
        row["created_at"] = datetime.fromisoformat(created)

    balance = row.get("account_balance")
    if balance is not None:
        row["account_balance"] = Decimal(str(balance))

    return row


def upsert_customers(db: Session, records: list[dict]) -> int:
    """
    Bulk upsert using PostgreSQL ON CONFLICT … DO UPDATE.
    Returns the number of rows affected.
    """
    if not records:
        return 0

    rows = [_coerce_row(r) for r in records]

    stmt = pg_insert(Customer).values(rows)

    # on conflict with the PK, update every non-key column
    update_cols = {
        col.name: stmt.excluded[col.name]
        for col in Customer.__table__.columns
        if col.name != "customer_id"
    }

    stmt = stmt.on_conflict_do_update(
        index_elements=["customer_id"],
        set_=update_cols,
    )

    db.execute(stmt)
    db.commit()
    log.info("Upserted %d customer records", len(rows))
    return len(rows)
