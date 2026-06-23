# Python Example

Run the CoinGlass Footprint History Actor from Python and read the JSON result from the default Apify dataset.

## Search symbols

```python
from apify_client import ApifyClient

client = ApifyClient("apify_api_your_token_here")

run_input = {
    "mode": "search_symbols",
    "keyword": "btc",
}

run = client.actor("api_merge/coinglass-footprint-history").call(run_input=run_input)
dataset_id = run.default_dataset_id
items = list(client.dataset(dataset_id).iterate_items())

print(items[0])
```

## Fetch footprint history

```python
from apify_client import ApifyClient

client = ApifyClient("apify_api_your_token_here")

run_input = {
    "mode": "footprint_history",
    "symbol": "Binance_BTCUSDT",
    "interval": "30m",
}

run = client.actor("api_merge/coinglass-footprint-history").call(run_input=run_input)
dataset_id = run.default_dataset_id
items = list(client.dataset(dataset_id).iterate_items())

print(items[0])
```

For a ready-to-run version with `.env` support, use [`run_footprint.py`](./run_footprint.py).

