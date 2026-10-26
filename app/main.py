from fastapi import FastAPI

app = FastAPI(
    title="WebOps Intelligence",
    description="Website monitoring and AI-assisted incident response",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "webops-intelligence",
    }