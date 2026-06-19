from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.db.client import ping_database
from src.agent.runtime import initialize_agent
from src.routes.chat import router as chat_router
from src.routes.jobs import router as jobs_router
from src.routes.pdf_upload import router as pdf_router
from src.routes.voice import router as voice_router
from src.services.llm.warmup import warmup_models
from src.logging_config import configure_runtime_logs


configure_runtime_logs()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting server...")

    await warmup_models()
    await ping_database()
    await initialize_agent()

    yield

    print("Shutting down server...")


app = FastAPI(
    title="Chat API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pdf_router)
app.include_router(chat_router)
app.include_router(jobs_router)
app.include_router(voice_router)
