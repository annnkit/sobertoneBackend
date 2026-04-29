from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import engine, Base
from app.routers import auth, checkins, chat, dashboard, insights, memory, community, assessment
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Sobertone API...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created.")
    yield
    logger.info("Shutting down Sobertone API...")


app = FastAPI(
    title="Sobertone API",
    description="Calm and trustworthy AI support for addiction prevention and relapse support.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8081",   # Expo web
        "http://127.0.0.1:8081",
        "https://*.vercel.app",
        "https://*.expo.dev",
        "*",                       # Allow all origins for mobile dev; restrict in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(checkins.router, prefix="/checkins", tags=["checkins"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(insights.router, prefix="/insights", tags=["insights"])
app.include_router(memory.router, prefix="/memory", tags=["memory"])
app.include_router(community.router, prefix="/community", tags=["community"])
app.include_router(assessment.router, prefix="/assessment", tags=["assessment"])


@app.get("/")
async def root():
    return {"message": "Sobertone API is running", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
