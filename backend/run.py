"""Nexus 2.0 backend entrypoint — uvicorn."""
import uvicorn

from app.config import NEXUS_HOST, NEXUS_PORT

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=NEXUS_PORT, reload=False)