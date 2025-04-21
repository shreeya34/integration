# main.py

from contextlib import asynccontextmanager
from fastapi import FastAPI

from api.entrypoints import routes
from api.entrypoints.routes import router as callback_router 

from config.settings import AppSettings
from addons.integration.hookspec import get_plugin_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up...")

    app.state.settings = AppSettings()
    app.state.plugin_manager = get_plugin_manager()

    print("Settings loaded:", app.state.settings)
    yield

    print("Shutting down...")


def init_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    app.include_router(routes.router)
    app.include_router(callback_router)     

    return app


app = init_app()