# FastAPI Example

Run this project as a small local REST API.

## Start the API

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open the API docs:

```text
http://127.0.0.1:8000/docs
```

## Search symbols

```bash
curl "http://127.0.0.1:8000/symbols?keyword=btc" \
  -H "Authorization: Bearer apify_api_your_token_here"
```

## Fetch footprint history

```bash
curl "http://127.0.0.1:8000/footprint-history?symbol=Binance_BTCUSDT&interval=30m" \
  -H "Authorization: Bearer apify_api_your_token_here"
```

With optional timestamps:

```bash
curl "http://127.0.0.1:8000/footprint-history?symbol=Binance_BTCUSDT&interval=30m&startTime=1757808000&endTime=1757894400" \
  -H "Authorization: Bearer apify_api_your_token_here"
```

## Call with a local .env file

```bash
cp .env.example .env
```

Add your token:

```env
APIFY_TOKEN=apify_api_your_real_token_here
```

Start the API:

```bash
uvicorn app.main:app --reload
```

Then call it without sending the token in every request:

```bash
curl "http://127.0.0.1:8000/symbols?keyword=eth"
```

## POST body

```bash
curl -X POST "http://127.0.0.1:8000/footprint-history" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer apify_api_your_token_here" \
  -d '{"symbol":"Binance_BTCUSDT","interval":"30m"}'
```

