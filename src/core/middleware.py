from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from api.utils.logger import get_logger

logger = get_logger()


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response

        except RequestValidationError as val_err:
            logger.warning(f"Validation error: {val_err.errors()}")
            return JSONResponse(
                status_code=422,
                content={"detail": val_err.errors()},
            )

        except ValueError as val_err:
            logger.warning(f"Value error: {str(val_err)}")
            return JSONResponse(
                status_code=404,
                content={"detail": str(val_err)},
            )

        except Exception as exc:
            logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
            return JSONResponse(
                status_code=500, content={"detail": "An unexpected error occurred."}
            )
