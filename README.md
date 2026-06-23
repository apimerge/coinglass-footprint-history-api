# CoinGlass Footprint History API

Run a tiny REST API for CoinGlass futures footprint history data, powered by the Apify Actor:

https://apify.com/api_merge/coinglass-footprint-history

This project is for developers who want simple endpoints like:

```text
GET /symbols?keyword=btc
GET /footprint-history?symbol=Binance_BTCUSDT&interval=30m
```

Use it to search supported futures instruments and fetch footprint history with price-level taker buy/sell volume as clean JSON.

## Run the API

Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Start FastAPI:

```bash
uvicorn app.main:app --reload
```

Open the interactive docs:

```text
http://127.0.0.1:8000/docs
```

## Search symbols

Find the exact CoinGlass futures symbol first:

```bash
curl "http://127.0.0.1:8000/symbols?keyword=btc" \
  -H "Authorization: Bearer apify_api_your_token_here"
```

Response shape:

```json
{
  "success": true,
  "actor": "api_merge/coinglass-footprint-history",
  "runId": "abc123",
  "datasetId": "def456",
  "input": {
    "mode": "search_symbols",
    "keyword": "btc"
  },
  "data": {
    "success": true,
    "message": "Futures symbols fetched successfully.",
    "mode": "search_symbols",
    "data": [
      {
        "base_asset": "BTC",
        "quote_asset": "USDT",
        "exchange": "Binance",
        "symbol": "Binance_BTCUSDT"
      }
    ]
  }
}
```

## Fetch footprint history

Use a `symbol` returned by `/symbols`:

```bash
curl "http://127.0.0.1:8000/footprint-history?symbol=Binance_BTCUSDT&interval=30m" \
  -H "Authorization: Bearer apify_api_your_token_here"
```

With optional timestamps:

```bash
curl "http://127.0.0.1:8000/footprint-history?symbol=Binance_BTCUSDT&interval=30m&startTime=1757808000&endTime=1757894400" \
  -H "Authorization: Bearer apify_api_your_token_here"
```

Response shape:

```json
{
  "success": true,
  "actor": "api_merge/coinglass-footprint-history",
  "runId": "abc123",
  "datasetId": "def456",
  "input": {
    "mode": "footprint_history",
    "symbol": "Binance_BTCUSDT",
    "interval": "30m"
  },
  "data": {
    "success": true,
    "message": "Footprint history data fetched successfully.",
    "mode": "footprint_history",
    "data": [
      [
        1757808000,
        [
          [
            115765,
            115770,
            3.223,
            9.906,
            373118.1958,
            1146773.5391,
            373118.1958,
            1146773.5391,
            193,
            153
          ]
        ]
      ]
    ]
  }
}
```

## Optional: use .env

If you do not want to send the token in every request:

```bash
cp .env.example .env
```

Edit `.env`:

```env
APIFY_TOKEN=apify_api_your_real_token_here
KEYWORD=btc
SYMBOL=Binance_BTCUSDT
INTERVAL=30m
START_TIME=
END_TIME=
```

Then call the API without the `Authorization` header:

```bash
curl "http://127.0.0.1:8000/symbols?keyword=eth"
```

Keep `.env` private. It is ignored by Git.

## POST examples

Search symbols:

```bash
curl -X POST "http://127.0.0.1:8000/symbols" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer apify_api_your_token_here" \
  -d '{"keyword":"btc"}'
```

Fetch footprint history:

```bash
curl -X POST "http://127.0.0.1:8000/footprint-history" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer apify_api_your_token_here" \
  -d '{"symbol":"Binance_BTCUSDT","interval":"30m"}'
```

## Input

| Field | Required | Example | Description |
| --- | --- | --- | --- |
| `keyword` | No | `btc` | Search keyword for `/symbols`. Leave empty to return the default futures symbol list. |
| `symbol` | Yes | `Binance_BTCUSDT` | Symbol value returned by `/symbols`. |
| `interval` | Yes | `30m` | Time interval for footprint aggregation. |
| `startTime` | No | `1757808000` | Optional 10-digit Unix timestamp in seconds. |
| `endTime` | No | `1757894400` | Optional 10-digit Unix timestamp in seconds. Must be greater than or equal to `startTime`. |

Supported intervals:

```text
1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 1w
```

## Python script

You can also run the Actor directly from a Python script.

Search symbols:

```bash
python examples/run_footprint.py --mode search_symbols --keyword btc
```

Fetch footprint history:

```bash
python examples/run_footprint.py --mode footprint_history --symbol Binance_BTCUSDT --interval 30m
```

With timestamps:

```bash
python examples/run_footprint.py --mode footprint_history --symbol Binance_BTCUSDT --interval 30m --startTime 1757808000 --endTime 1757894400
```

The script asks for your Apify token in a hidden prompt, starts the Actor, prints the dataset result, and saves it to `result.json`.

## Get an Apify token

1. Open Apify Console.
2. Go to **API & Integrations**.
3. Copy or create an API token.
4. Use it in the `Authorization` header, paste it into the script prompt, or save it in `.env` as `APIFY_TOKEN`.

## What you can build

- Futures footprint dashboards
- Order-flow research notebooks
- Buy/sell volume monitoring tools
- Symbol discovery workflows
- Scheduled footprint snapshots through Apify

## Deployment note

If you deploy this API publicly with your own `APIFY_TOKEN` in `.env`, protect the service with your own auth, rate limits, or billing. Otherwise, public users can consume your Apify account.

## Official Apify Actor

Use the hosted Actor here:

https://apify.com/api_merge/coinglass-footprint-history

## Files

```text
.
├── .env.example
├── README.md
├── requirements.txt
├── app
│   ├── __init__.py
│   └── main.py
└── examples
    ├── fastapi.md
    ├── python.md
    └── run_footprint.py
```

