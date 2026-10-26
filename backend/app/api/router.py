from fastapi import APIRouter

from app.api.routes import admin, public, system, tasks

api_router = APIRouter()
api_router.include_router(system.router)
api_router.include_router(public.router)
api_router.include_router(tasks.router)
api_router.include_router(admin.admin_auth)
api_router.include_router(admin.admin)
