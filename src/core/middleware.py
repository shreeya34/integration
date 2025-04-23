from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response

        except RequestValidationError as val_err:
            return JSONResponse(
                status_code=422,
                content={"detail": val_err.errors()},
            )

        except Exception as exc:
            return JSONResponse(
                status_code=500, content={"detail": "An unexcepted error occurred."}
            )
