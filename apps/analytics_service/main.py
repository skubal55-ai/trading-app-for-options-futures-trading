from fastapi import FastAPI

app = FastAPI(title="Analytics Service", version="0.1.0")


@app.get("/health")
async def health() -> dict:
    return {"service": "analytics_service", "status": "ok"}


@app.get("/metrics/sample")
async def metrics_sample() -> dict:
    return {
        "hit_rate": 0.56,
        "expectancy": 0.07,
        "max_drawdown_pct": 10.8,
        "profit_factor": 1.29,
    }
