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
from routers.auth import router as auth_router
from routers.catalogs import router as catalogs_router
from routers.dealers import router as dealers_router
from routers.documents import router as documents_router
from routers.labels import router as labels_router
from routers.proforma import router as proforma_router
from routers.projects import router as projects_router
from routers.reports import router as reports_router
from routers.revisions import router as revisions_router


# Startup runs before the yield, shutdown after it. Add your own setup/teardown here.
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.index_task = asyncio.create_task(ensure_indexes())  # background: a big index build must not block boot
    app.state.catalog_task = asyncio.create_task(ensure_catalog_defaults())  # tanım listelerini tohumla
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
api_router.include_router(proforma_router)
api_router.include_router(reports_router)

# Include the router in the main app — must stay the last registration
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
