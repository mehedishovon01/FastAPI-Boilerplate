from fastapi import FastAPI
from src.routers import auth, users
from src.core.config import settings
from src.core.database import engine
from src.models.user import Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])