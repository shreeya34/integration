from contextlib import asynccontextmanager
from fastapi import FastAPI

# from core.middleware import ExceptionHandlerMiddleware
from api.entrypoints import routes
from api.entrypoints.routes import router as callback_router

from config.settings import AppSettings
from addons.integration.hookspec import get_plugin_manager
from config import settings


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

    # app.add_middleware(ExceptionHandlerMiddleware)
 

    app.include_router(routes.router)
    app.include_router(callback_router)

    return app


app = init_app()
