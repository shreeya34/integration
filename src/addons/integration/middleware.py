

# from fastapi import Request, HTTPException
# from fastapi.exceptions import RequestValidationError
# from starlette.middleware.base import BaseHTTPMiddleware
# from starlette.responses import JSONResponse
# # from api.utils.logger import logger


# class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
#     async def dispatch(self, request: Request, call_next):
#         try:
#             response = await call_next(request)
#             return response

#         except RequestValidationError as val_err:
#             # logger.warning(f"Validation Error: {val_err.errors()}")
#             return JSONResponse(
#                 status_code=422,
#                 content={"detail": val_err.errors()},
#             )

#         except Exception as exc:
#             # logger.error(f"Internal Server Error: {str(exc)}", exc_info=True)/
#             return JSONResponse(
#                 status_code=500, content={"detail": "An unexcepted error occurred."}
#             )