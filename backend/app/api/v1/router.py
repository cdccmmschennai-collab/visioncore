from fastapi import APIRouter

from app.api.v1 import admin, auth, batches, config, history, tags

api_router = APIRouter()
api_router.include_router(config.router)
api_router.include_router(auth.router)
api_router.include_router(batches.router)
api_router.include_router(tags.router)
api_router.include_router(history.router)
api_router.include_router(admin.router)
