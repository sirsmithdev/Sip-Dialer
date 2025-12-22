"""
API v1 router that combines all endpoint routers.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, settings, audio, contacts, campaigns, ivr, ws

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(settings.router, prefix="/settings", tags=["Settings"])
api_router.include_router(audio.router, prefix="/audio", tags=["Audio Files"])
api_router.include_router(contacts.router, prefix="/contacts", tags=["Contacts"])
api_router.include_router(campaigns.router, prefix="/campaigns", tags=["Campaigns"])
api_router.include_router(ivr.router, prefix="/ivr-flows", tags=["IVR Flows"])
api_router.include_router(ws.router, tags=["WebSocket"])
