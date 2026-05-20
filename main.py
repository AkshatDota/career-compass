import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.database import init_db
from app.limiter import limiter
from app.routers import session, question, answer, results

BASE_DIR = Path(__file__).parent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initialising SQLite database…")
    init_db()
    logger.info("Database ready.")
    yield


app = FastAPI(
    title="Career Discovery API",
    version="1.0.0",
    description="Adaptive career quiz backend for BCA students, powered by Claude AI.",
    lifespan=lifespan,
)

# ── Rate limiting ──────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
# allow_origin_regex handles wildcard subdomains (e.g. any GitHub Pages domain)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=r"https://.*\.github\.io",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(session.router, prefix="/api", tags=["session"])
app.include_router(question.router, prefix="/api", tags=["question"])
app.include_router(answer.router, prefix="/api", tags=["answer"])
app.include_router(results.router, prefix="/api", tags=["results"])


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


# ── Frontend ──────────────────────────────────────────────────────────────────
# Serve career-compass.js as a static file
app.mount("/static", StaticFiles(directory=str(BASE_DIR)), name="static")


@app.get("/", include_in_schema=False)
def serve_frontend():
    return FileResponse(str(BASE_DIR / "Career Compass.html"))
