from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routers import core

# Create FastAPI app
app = FastAPI(
    title="Document Search API",
    description="API for processing documents from S3 and searching with Elasticsearch",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(core.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Document Search API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
