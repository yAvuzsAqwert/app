import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
from lib.db import client, db, ensure_indexes
from lib.catalog import ensure_catalog_defaults
from lib.permissions import ensure_role_defaults
from routers.auth import router as auth_router
from routers.catalogs import router as catalogs_router
from routers.dealers import router as dealers_router
from routers.documents import router as documents_router
from routers.labels import router as labels_router
from routers.admin import router as admin_router
from routers.branding import router as branding_router
from routers.portal import router as portal_router
from routers.audit import router as audit_router
from routers.printouts import router as printouts_router
from routers.proforma import router as proforma_router
from routers.projects import router as projects_router
from routers.reports import router as reports_router
from routers.revisions import router as revisions_router


# Startup runs before the yield, shutdown after it. Add your own setup/teardown here.
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.index_task = asyncio.create_task(ensure_indexes())  # background: a big index build must not block boot
    app.state.catalog_task = asyncio.create_task(ensure_catalog_defaults())  # tanım listelerini tohumla
    app.state.role_task = asyncio.create_task(ensure_role_defaults())  # rol/yetki tohumlama
    yield
    client.close()


# Create the main app without a prefix
app = FastAPI(lifespan=lifespan, title="Pergola & Tente Proje Takip API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"message": "Pergola & Tente Proje Takip API", "ok": True}


api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(catalogs_router)
api_router.include_router(dealers_router)
api_router.include_router(documents_router)
api_router.include_router(revisions_router)
api_router.include_router(labels_router)
api_router.include_router(portal_router)
api_router.include_router(admin_router)
api_router.include_router(branding_router)
api_router.include_router(printouts_router)
api_router.include_router(audit_router)
api_router.include_router(proforma_router)
api_router.include_router(reports_router)

@api_router.get("/health")
async def health():
    """Dağıtım teşhisi: veritabanı erişimi çalışıyor mu? (gizli bilgi sızdırmaz)"""
    try:
        await db.command("ping")
        kullanici = await db.users.count_documents({})
        proje = await db.projects.count_documents({})
        return {"ok": True, "db": "up", "kullanici": kullanici, "proje": proje}
    except Exception as exc:  # pragma: no cover - teşhis amaçlı
        return {"ok": False, "db": "down", "hata": type(exc).__name__}


# Include the router in the main app — must stay the last registration
app.include_router(api_router)

_cors_env = [o.strip() for o in os.environ.get('CORS_ORIGINS', '').split(',') if o.strip()]
# Kimlik bilgisi (cookie) ile "*" kullanılamaz — tarayıcı reddeder. Wildcard gelirse atılır.
_cors_origins = [o for o in _cors_env if o != '*']

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=_cors_origins,
    # Preview, emergent.host ve bağlanan özel alan adı (ör. siparis.diagonalventure.com)
    allow_origin_regex=os.environ.get(
        'CORS_ORIGIN_REGEX',
        r'https://([a-z0-9-]+\.)*(emergentagent\.com|emergent\.host|diagonalventure\.com)',
    ),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
