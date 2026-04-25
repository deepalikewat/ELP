import json
import os
import logging
from flask import Flask, jsonify, request, abort

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

app = Flask(__name__)

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "customers.json")


def _load_customers():
    """Read the JSON file once per import — keeps things simple for a mock."""
    try:
        with open(DATA_PATH, "r") as fh:
            data = json.load(fh)
        log.info("Loaded %d customers from %s", len(data), DATA_PATH)
        return data
    except FileNotFoundError:
        log.error("Customer data file not found at %s", DATA_PATH)
        return []
    except json.JSONDecodeError as exc:
        log.error("Malformed JSON in %s: %s", DATA_PATH, exc)
        return []


CUSTOMERS = _load_customers()
# build a quick lookup dict keyed by customer_id
_CUSTOMER_MAP = {c["customer_id"]: c for c in CUSTOMERS}


# ---------- endpoints ---------- #

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "records": len(CUSTOMERS)})


@app.route("/api/customers", methods=["GET"])
def list_customers():
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 10))
    except (ValueError, TypeError):
        abort(400, description="page and limit must be integers")

    if page < 1 or limit < 1:
        abort(400, description="page and limit must be >= 1")

    start = (page - 1) * limit
    end = start + limit
    subset = CUSTOMERS[start:end]

    return jsonify({
        "data": subset,
        "total": len(CUSTOMERS),
        "page": page,
        "limit": limit,
    })


@app.route("/api/customers/<string:customer_id>", methods=["GET"])
def get_customer(customer_id):
    customer = _CUSTOMER_MAP.get(customer_id)
    if customer is None:
        abort(404, description=f"Customer {customer_id} not found")
    return jsonify({"data": customer})


# ---------- error handlers ---------- #

@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": str(error.description)}), 400


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": str(error.description)}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
