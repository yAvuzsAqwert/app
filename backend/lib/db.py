"""Shared Mongo handle — import `client`/`db` from here (server.py, routers, seed.py)."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, IndexModel

load_dotenv(Path(__file__).parent.parent / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

logger = logging.getLogger(__name__)

# One entry per collection: every field a route filters, sorts, or dedupes on. Applied by ensure_indexes() at startup.
INDEXES: dict[str, list[IndexModel]] = {
    "status_checks": [IndexModel([("timestamp", DESCENDING)], name="timestamp_desc")],
    "users": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("email", ASCENDING)], name="email", unique=True),
    ],
    "sessions": [
        IndexModel([("token", ASCENDING)], name="token", unique=True),
        IndexModel([("created_at", ASCENDING)], name="ttl", expireAfterSeconds=60 * 60 * 24 * 30),
    ],
    "dealer_accounts": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("email", ASCENDING)], name="email", unique=True),
    ],
    "dealer_sessions": [
        IndexModel([("token", ASCENDING)], name="token", unique=True),
        IndexModel([("created_at", ASCENDING)], name="ttl", expireAfterSeconds=60 * 60 * 24 * 14),
    ],
    "roles": [IndexModel([("kod", ASCENDING)], name="kod", unique=True)],
    "rates": [IndexModel([("para_birimi", ASCENDING)], name="para_birimi", unique=True)],
    "settings": [IndexModel([("key", ASCENDING)], name="key", unique=True)],
    "projects": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("proje_kodu", ASCENDING)], name="proje_kodu", unique=True),
        IndexModel([("arsiv", ASCENDING), ("proje_tarihi", DESCENDING)], name="arsiv_tarih"),
        IndexModel([("durum", ASCENDING), ("proje_tarihi", DESCENDING)], name="durum_tarih"),
    ],
    "project_items": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("proje_id", ASCENDING), ("created_at", ASCENDING)], name="proje_created"),
    ],
    "project_crates": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("proje_id", ASCENDING), ("created_at", ASCENDING)], name="proje_created"),
    ],
    "catalogs": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("tip", ASCENDING), ("deger", ASCENDING)], name="tip_deger", unique=True),
        IndexModel([("tip", ASCENDING), ("sira", ASCENDING)], name="tip_sira"),
    ],
    "proforma_versions": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("proje_id", ASCENDING), ("versiyon", DESCENDING)], name="proje_versiyon"),
    ],
    "documents": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("proje_id", ASCENDING), ("created_at", DESCENDING)], name="proje_created_desc"),
    ],
    "activities": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("proje_id", ASCENDING), ("created_at", DESCENDING)], name="proje_created_desc"),
        IndexModel([("gun", ASCENDING), ("created_at", DESCENDING)], name="gun_created_desc"),
    ],
}


async def ensure_indexes() -> None:
    for collection, models in INDEXES.items():
        for model in models:  # one at a time so a bad spec skips only itself
            try:
                await db[collection].create_indexes([model])
            except Exception as exc:  # never block boot on an index; the log line names what to fix
                logger.error("ensure_indexes(%s.%s): %s", collection, model.document["name"], exc)
