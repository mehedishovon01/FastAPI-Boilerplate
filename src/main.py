"""ASGI entry point: ``uvicorn src.main:app``."""
from src.core.app import create_app
from src.core.config import settings

app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
