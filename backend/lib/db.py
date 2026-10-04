"""Shared Mongo handle — import `client`/`db` from here (server.py, routers, seed.py)."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, IndexModel

load_dotenv(Path(__file__).parent.parent / ".env")

# Platform ortam değişkeni farklı isimle gelebilir; ilk dolu olan kullanılır.
mongo_url = next(
    (
        os.environ[key]
        for key in ("MONGO_URL", "MONGODB_URI", "MONGO_URI", "DATABASE_URL")
        if os.environ.get(key)
    ),
    "",
)
if not mongo_url:
    raise RuntimeError("MONGO_URL ortam değişkeni tanımlı değil")
DB_NAME = os.environ.get("DB_NAME") or os.environ.get("MONGO_DB_NAME") or "app"

# Motor istemcisi import sırasında DEĞİL, ilk kullanımda (servis eden event loop içinde)
# oluşturulur. Aksi halde --reload olmayan üretim ortamında istemci farklı bir event
# loop'a bağlanır ve her sorgu "attached to a different loop" hatası verir.
_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)
    return _client


def get_db():
    return get_client()[DB_NAME]


class _DBProxy:
    """`from lib.db import db` çağrı yerleri bozulmadan tembel bağlanmayı sağlar."""

    def __getattr__(self, name):
        return getattr(get_db(), name)

    def __getitem__(self, key):
        return get_db()[key]


class _ClientProxy:
    def __getattr__(self, name):
        return getattr(get_client(), name)


client = _ClientProxy()
db = _DBProxy()
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
    "login_attempts": [
        IndexModel([("key", ASCENDING)], name="key"),
        IndexModel([("email", ASCENDING)], name="email"),
        IndexModel([("created_at", ASCENDING)], name="ttl", expireAfterSeconds=60 * 60),
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
