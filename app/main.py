from __future__ import annotations

from contextlib import asynccontextmanager
import os
from pathlib import Path
import re
import time
from typing import Any, Literal

from apify_client import ApifyClient
from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"
ACTOR_ID = "api_merge/coinglass-footprint-history"
MIN_TIMESTAMP_SECONDS = 1483228800
MAX_FUTURE_DRIFT_SECONDS = 300

Mode = Literal["search_symbols", "footprint_history"]
FootprintInterval = Literal[
    "1m",
    "3m",
    "5m",
    "15m",
    "30m",
    "1h",
    "2h",
    "4h",
    "6h",
    "8h",
    "12h",
    "1d",
    "1w",
]


class SymbolSearchRequest(BaseModel):
    keyword: str = Field(default="", examples=["btc"])


class FootprintHistoryRequest(BaseModel):
    symbol: str = Field(default="Binance_BTCUSDT", min_length=1, examples=["Binance_BTCUSDT"])
    interval: FootprintInterval = Field(default="30m", examples=["30m"])
    startTime: str | None = Field(default=None, examples=["1757808000"])
    endTime: str | None = Field(default=None, examples=["1757894400"])


class ActorRunRequest(BaseModel):
    mode: Mode = Field(default="footprint_history")
    keyword: str = Field(default="")
    symbol: str = Field(default="Binance_BTCUSDT")
    interval: FootprintInterval = Field(default="30m")
    startTime: str | None = None
    endTime: str | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    load_env_file(ENV_FILE)
    yield


app = FastAPI(
    title="CoinGlass Footprint History API",
    description="A tiny REST API wrapper around the Apify CoinGlass Footprint History Actor.",
    version="1.0.0",
    lifespan=lifespan,
)


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]

        os.environ.setdefault(key, value)


def is_real_token(token: str | None) -> bool:
    return bool(token and token.strip() and not token.strip().startswith("apify_api_your_"))


def get_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return None

    return token.strip()


def get_apify_token(authorization: str | None = Header(default=None)) -> str:
    env_token = os.getenv("APIFY_TOKEN", "").strip()
    if is_real_token(env_token):
        return env_token

    header_token = get_bearer_token(authorization)
    if is_real_token(header_token):
        return header_token

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Set APIFY_TOKEN in .env or send Authorization: Bearer <APIFY_TOKEN>.",
    )


def validate_timestamp(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None

    timestamp = value.strip()
    if not timestamp:
        return None

    latest_allowed = int(time.time()) + MAX_FUTURE_DRIFT_SECONDS
    if not re.fullmatch(r"\d{10}", timestamp):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} must be a 10-digit Unix timestamp in seconds.",
        )

    numeric_timestamp = int(timestamp)
    if numeric_timestamp < MIN_TIMESTAMP_SECONDS or numeric_timestamp > latest_allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} must be between 2017-01-01 and now.",
        )

    return timestamp


def build_footprint_input(request: FootprintHistoryRequest) -> dict[str, Any]:
    start_time = validate_timestamp(request.startTime, "startTime")
    end_time = validate_timestamp(request.endTime, "endTime")
    symbol = request.symbol.strip()

    if not symbol:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="symbol is required for footprint_history mode.",
        )

    if start_time and end_time and int(start_time) > int(end_time):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="startTime must be less than or equal to endTime.",
        )

    run_input: dict[str, Any] = {
        "mode": "footprint_history",
        "symbol": symbol,
        "interval": request.interval,
    }

    if start_time:
        run_input["startTime"] = start_time

    if end_time:
        run_input["endTime"] = end_time

    return run_input


def get_run_value(run: object, api_key: str, attr_name: str | None = None) -> object:
    if isinstance(run, dict):
        return run.get(api_key) or (run.get(attr_name) if attr_name else None)

    if attr_name and hasattr(run, attr_name):
        return getattr(run, attr_name)

    if hasattr(run, api_key):
        return getattr(run, api_key)

    if hasattr(run, "model_dump"):
        data = run.model_dump(by_alias=True)
        return data.get(api_key) or (data.get(attr_name) if attr_name else None)

    return None


def get_run_error_detail(
    client: ApifyClient,
    run: object,
    run_input: dict[str, Any],
) -> dict[str, Any]:
    dataset_id = get_run_value(run, "defaultDatasetId", "default_dataset_id")
    dataset_items: list[dict[str, Any]] = []

    if dataset_id:
        try:
            dataset_items = list(client.dataset(str(dataset_id)).iterate_items())
        except Exception:
            dataset_items = []

    detail: dict[str, Any] = {
        "message": "Actor run did not succeed.",
        "actor": ACTOR_ID,
        "runId": get_run_value(run, "id"),
        "status": get_run_value(run, "status"),
        "statusMessage": get_run_value(run, "statusMessage", "status_message"),
        "exitCode": get_run_value(run, "exitCode", "exit_code"),
        "datasetId": dataset_id,
        "input": run_input,
    }

    if dataset_items:
        detail["datasetItems"] = dataset_items

    return detail


def fetch_actor_result(token: str, run_input: dict[str, Any]) -> dict[str, Any]:
    client = ApifyClient(token)
    try:
        run = client.actor(ACTOR_ID).call(run_input=run_input)

        run_status = get_run_value(run, "status")
        if run_status and run_status != "SUCCEEDED":
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=get_run_error_detail(client, run, run_input),
            )

        dataset_id = get_run_value(run, "defaultDatasetId", "default_dataset_id")
        if not dataset_id:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Actor run did not return a default dataset id.",
            )

        items = list(client.dataset(str(dataset_id)).iterate_items())
        if not items:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Actor finished, but the default dataset is empty.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Apify request failed. Check your token, actor access, and input values.",
        ) from exc

    return {
        "success": True,
        "actor": ACTOR_ID,
        "runId": get_run_value(run, "id"),
        "datasetId": dataset_id,
        "input": run_input,
        "data": items[0] if len(items) == 1 else items,
    }


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "name": "CoinGlass Footprint History API",
        "endpoints": {
            "health": "/health",
            "symbols": "/symbols?keyword=btc",
            "footprintHistory": "/footprint-history?symbol=Binance_BTCUSDT&interval=30m",
            "docs": "/docs",
        },
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/symbols")
async def search_symbols(
    keyword: str = Query(default=""),
    token: str = Depends(get_apify_token),
) -> dict[str, Any]:
    run_input = {
        "mode": "search_symbols",
        "keyword": keyword.strip(),
    }
    return await run_in_threadpool(fetch_actor_result, token, run_input)


@app.get("/footprint-history")
async def get_footprint_history(
    symbol: str = Query(default="Binance_BTCUSDT", min_length=1),
    interval: FootprintInterval = Query(default="30m"),
    start_time: str | None = Query(default=None, alias="startTime"),
    end_time: str | None = Query(default=None, alias="endTime"),
    token: str = Depends(get_apify_token),
) -> dict[str, Any]:
    request = FootprintHistoryRequest(
        symbol=symbol,
        interval=interval,
        startTime=start_time,
        endTime=end_time,
    )
    run_input = build_footprint_input(request)
    return await run_in_threadpool(fetch_actor_result, token, run_input)


@app.post("/symbols")
async def post_symbols(
    request: SymbolSearchRequest,
    token: str = Depends(get_apify_token),
) -> dict[str, Any]:
    run_input = {
        "mode": "search_symbols",
        "keyword": request.keyword.strip(),
    }
    return await run_in_threadpool(fetch_actor_result, token, run_input)


@app.post("/footprint-history")
async def post_footprint_history(
    request: FootprintHistoryRequest,
    token: str = Depends(get_apify_token),
) -> dict[str, Any]:
    run_input = build_footprint_input(request)
    return await run_in_threadpool(fetch_actor_result, token, run_input)


@app.post("/run")
async def run_actor(
    request: ActorRunRequest,
    token: str = Depends(get_apify_token),
) -> dict[str, Any]:
    if request.mode == "search_symbols":
        run_input = {
            "mode": "search_symbols",
            "keyword": request.keyword.strip(),
        }
    else:
        run_input = build_footprint_input(
            FootprintHistoryRequest(
                symbol=request.symbol,
                interval=request.interval,
                startTime=request.startTime,
                endTime=request.endTime,
            )
        )

    return await run_in_threadpool(fetch_actor_result, token, run_input)
