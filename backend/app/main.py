from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import APP_NAME, get_settings
from app.db.database import Database
from app.services.jobs import JobStore
from app.services.transcription import ProviderRegistry


settings = get_settings()
database = Database(settings.database_path)
jobs = JobStore()
providers = ProviderRegistry()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    database.initialize()

    with database.connect() as connection:
        connection.execute(
            """
            INSERT INTO app_settings (key, value)
            VALUES ('transcription_provider', ?)
            ON CONFLICT(key) DO NOTHING
            """,
            (providers.default_provider,),
        )

    yield


app = FastAPI(title=APP_NAME, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.state.settings = settings
app.state.database = database
app.state.jobs = jobs
app.state.providers = providers
app.include_router(router)
