from fastapi import FastAPI

app = FastAPI(title="Remi Agent Service")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "remi-agent"}
