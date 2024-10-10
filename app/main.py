from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, competitors
from app.database import init_db
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="FYC Product API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(competitors.router, prefix="/competitors", tags=["Competitors"])

@app.on_event("startup")
async def startup_event():
    logger.info(f"MongoDB URL: {settings.MONGODB_URL}")
    await init_db()

@app.get("/")
async def root():
    return {"message": "Welcome to FYC Product BackendAPI"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
