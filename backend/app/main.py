from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import assistant, boards, snapshots

app = FastAPI(title="SmartStudy API", version="0.1.0")


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    code = "ERROR"
    if exc.status_code == 401:
        code = "UNAUTHORIZED"
    elif exc.status_code == 404:
        code = "NOT_FOUND"
    elif exc.status_code == 403:
        code = "FORBIDDEN"
    elif exc.status_code == 503:
        code = "AI_UNAVAILABLE"
    elif exc.status_code == 429:
        code = "RATE_LIMITED"

    if isinstance(exc.detail, dict):
        content = {
            "code": exc.detail.get("code", code),
            "service": exc.detail.get("service", _request.url.path),
            **exc.detail,
        }
        if "message" not in content and "detail" in content:
            content["message"] = content.pop("detail")
        return JSONResponse(status_code=exc.status_code, content=content)

    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": detail, "code": code, "service": _request.url.path},
    )

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(boards.router)
app.include_router(snapshots.router)
app.include_router(assistant.router)


@app.get("/health")
async def health():
    return {"ok": True}


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    service = f"{request.method} {request.url.path}"
    return JSONResponse(
        status_code=500,
        content={
            "message": f"Internal error: {exc}",
            "code": "INTERNAL_ERROR",
            "service": service,
        },
    )
