from __future__ import annotations

import argparse
from getpass import getpass
import json
import os
import re
import sys
import time
from pathlib import Path

from apify_client import ApifyClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"
OUTPUT_FILE = PROJECT_ROOT / "result.json"
ACTOR_ID = "api_merge/coinglass-footprint-history"
SUPPORTED_MODES = {"search_symbols", "footprint_history"}
SUPPORTED_INTERVALS = {
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
}
MIN_TIMESTAMP_SECONDS = 1483228800
MAX_FUTURE_DRIFT_SECONDS = 300


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the CoinGlass Footprint History Apify Actor and print the dataset result.",
    )
    parser.add_argument(
        "--mode",
        default=os.getenv("MODE", "footprint_history"),
        choices=sorted(SUPPORTED_MODES),
    )
    parser.add_argument("--keyword", default=os.getenv("KEYWORD", "btc"))
    parser.add_argument("--symbol", default=os.getenv("SYMBOL", "Binance_BTCUSDT"))
    parser.add_argument(
        "--interval",
        default=os.getenv("INTERVAL", "30m"),
        choices=sorted(SUPPORTED_INTERVALS),
    )
    parser.add_argument("--startTime", default=os.getenv("START_TIME", ""))
    parser.add_argument("--endTime", default=os.getenv("END_TIME", ""))
    return parser.parse_args()


def get_apify_token() -> str:
    token = os.getenv("APIFY_TOKEN", "").strip()
    if token and not token.startswith("apify_api_your_"):
        return token

    try:
        return getpass("Apify API token: ").strip()
    except (EOFError, KeyboardInterrupt):
        return ""


def validate_timestamp(value: str, field_name: str) -> str:
    timestamp = value.strip()
    if not timestamp:
        return ""

    latest_allowed = int(time.time()) + MAX_FUTURE_DRIFT_SECONDS
    if not re.fullmatch(r"\d{10}", timestamp):
        raise ValueError(f"{field_name} must be a 10-digit Unix timestamp in seconds.")

    numeric_timestamp = int(timestamp)
    if numeric_timestamp < MIN_TIMESTAMP_SECONDS or numeric_timestamp > latest_allowed:
        raise ValueError(f"{field_name} must be between 2017-01-01 and now.")

    return timestamp


def build_run_input(args: argparse.Namespace) -> dict[str, object]:
    if args.mode == "search_symbols":
        return {
            "mode": "search_symbols",
            "keyword": args.keyword.strip(),
        }

    symbol = args.symbol.strip()
    if not symbol:
        raise ValueError("symbol is required for footprint_history mode.")

    start_time = validate_timestamp(args.startTime, "startTime")
    end_time = validate_timestamp(args.endTime, "endTime")
    if start_time and end_time and int(start_time) > int(end_time):
        raise ValueError("startTime must be less than or equal to endTime.")

    run_input: dict[str, object] = {
        "mode": "footprint_history",
        "symbol": symbol,
        "interval": args.interval,
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


def main() -> int:
    load_env_file(ENV_FILE)
    args = parse_args()

    token = get_apify_token()
    if not token:
        print(
            "Missing Apify token. Paste it at the prompt or set APIFY_TOKEN in .env.",
            file=sys.stderr,
        )
        return 1

    try:
        run_input = build_run_input(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Running {ACTOR_ID} with input:")
    print(json.dumps(run_input, indent=2))

    client = ApifyClient(token)
    run = client.actor(ACTOR_ID).call(run_input=run_input)

    status = get_run_value(run, "status")
    if status and status != "SUCCEEDED":
        print(f"Actor finished with status: {status}", file=sys.stderr)
        return 1

    dataset_id = get_run_value(run, "defaultDatasetId", "default_dataset_id")
    if not dataset_id:
        print("Actor run did not return a default dataset id.", file=sys.stderr)
        return 1

    items = list(client.dataset(str(dataset_id)).iterate_items())
    if not items:
        print("Actor finished, but the default dataset is empty.", file=sys.stderr)
        return 1

    result = items[0] if len(items) == 1 else items
    OUTPUT_FILE.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nSaved result to {OUTPUT_FILE.name}")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

