import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import engine, Base, get_db
from models.customer import Customer
from services.ingestion import fetch_all_customers, upsert_customers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # create tables on startup so we don't need a separate migration step
    Base.metadata.create_all(bind=engine)
    log.info("Database tables ensured.")
    yield


app = FastAPI(
    title="Customer Data Pipeline",
    version="1.0.0",
    lifespan=lifespan,
)


# ---- endpoints ---- #

@app.get("/api/health")
def health():
    return {"status": "healthy", "service": "pipeline"}


@app.post("/api/ingest")
def ingest(db: Session = Depends(get_db)):
    """Pull every customer from the mock server and upsert into Postgres."""
    try:
        records = fetch_all_customers()
    except Exception as exc:
        log.exception("Failed to fetch from mock server")
        raise HTTPException(status_code=502, detail=f"Mock server error: {exc}")

    try:
        count = upsert_customers(db, records)
    except Exception as exc:
        log.exception("Database upsert failed")
        raise HTTPException(status_code=500, detail=f"DB error: {exc}")

    return {"status": "success", "records_processed": count}


@app.get("/api/customers")
def list_customers(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    total = db.query(Customer).count()
    offset = (page - 1) * limit
    rows = (
        db.query(Customer)
        .order_by(Customer.customer_id)
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "data": [r.to_dict() for r in rows],
        "total": total,
        "page": page,
        "limit": limit,
    }


@app.get("/api/customers/{customer_id}")
def get_customer(customer_id: str, db: Session = Depends(get_db)):
    row = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return {"data": row.to_dict()}
