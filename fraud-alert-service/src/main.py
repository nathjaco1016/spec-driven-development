from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.database import init_db
from src.routes.alerts import router as alerts_router
from src.routes.transactions import router as transactions_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Fraud Alert Validation Service", lifespan=lifespan)

app.include_router(transactions_router)
app.include_router(alerts_router)
