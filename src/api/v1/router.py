"""Aggregates every v1 sub-router into a single router that the
application factory mounts under ``/api/v1``.
"""
from fastapi import APIRouter

from src.apps.auth.router import router as auth_router
from src.apps.rbac.router import router as rbac_router
from src.apps.users.router import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(rbac_router)
