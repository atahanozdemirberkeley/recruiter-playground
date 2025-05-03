from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from utils.api_routes import router


def setup_api(app: FastAPI):
    """
    Configure API settings including CORS middleware and routes.

    Args:
        app: The FastAPI application instance
    """
    # Setup CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, replace with actual origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(router)

    return app
