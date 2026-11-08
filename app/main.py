from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import DB_PATH, init_db
from app.routes import router


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db(DB_PATH)
    yield


app = FastAPI(title="Tasks API", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
