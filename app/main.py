from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import models  # noqa: F401  (importing registers the tables)
from .database import Base, engine
from .routes import router
from .services import ConflictError, NotFoundError


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Annotation Quality API",
    version="1.0.0",
    description=(
        "Tracks data-annotation tasks, submissions and reviews, and reports quality "
        "metrics (approval rate, rework rate, average score) per annotator and project."
    ),
    lifespan=lifespan,
)
app.include_router(router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


@app.exception_handler(NotFoundError)
async def not_found_handler(_: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
async def conflict_handler(_: Request, exc: ConflictError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})
