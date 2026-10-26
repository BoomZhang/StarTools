import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.router import api_router
from app.core.clients import create_engine, create_redis, create_session_factory
from app.core.config import settings
from app.db.models import Base
from app.db.seed import seed_database
from app.services.cleanup import cleanup_expired, cleanup_loop

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_engine()
    app.state.db_engine = engine
    app.state.db_session = create_session_factory(engine)
    app.state.redis = create_redis()

    settings.raw_path.mkdir(parents=True, exist_ok=True)
    settings.result_path.mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with app.state.db_session() as session:
        await seed_database(session)

    try:
        await cleanup_expired(app.state.db_session)
    except Exception:
        logger.exception("启动清理失败")

    cleanup_task = asyncio.create_task(cleanup_loop(app.state.db_session))
    try:
        yield
    finally:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        await app.state.redis.aclose()
        await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    docs_url=f"{settings.api_prefix}/docs",
    openapi_url=f"{settings.api_prefix}/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "version": __version__,
        "docs": f"{settings.api_prefix}/docs",
        "site": "/startools/",
    }
