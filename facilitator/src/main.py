import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

load_dotenv()

from src.routes import verify, settle  # noqa: E402 — nach load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("x402 Facilitator gestartet")
    yield
    logger.info("x402 Facilitator beendet")


app = FastAPI(
    title="x402 Facilitator",
    version="0.1.0",
    description="Payment Facilitator für das x402-Protokoll (Base L2 / USDC)",
    lifespan=lifespan,
)

app.include_router(verify.router)
app.include_router(settle.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unbehandelter Fehler: %s", exc)
    return JSONResponse(status_code=500, content={"error": "Interner Serverfehler"})


@app.get("/health")
async def health():
    return {"status": "ok"}
