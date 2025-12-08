from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv

from webhooks.routers.askai import router as AskAIRouter
from utils.queued_logger import QueuedLogger
from utils.jsonl_logger import JsonlLogger

load_dotenv(dotenv_path=".env")

logger = QueuedLogger()
training_logger = JsonlLogger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await training_logger.startup()
    await logger.startup()
    yield
    await logger.shutdown()
    await training_logger.shutdown()

app = FastAPI(
    title="bot-assistant",
    version="1.0.0",
    root_path="/api/v1",
    lifespan=lifespan
)

app.include_router(AskAIRouter)
