# Grocery price and inventory data

The optimizer reads `data/prices/prices.csv` when that file exists. If it does not, it falls back to `sample_prices.csv`. The bundled sample is deliberately illustrative and must not be described as live or verified market data.

## Preparing a real `prices.csv`

1. Copy `price_template.csv` to `prices.csv`.
2. Keep only foods for which you have a price observation. `fct_code` must match a code in `data/processed/foods.csv`.
3. Fill in the price and the exact package/quantity weight. For example, a 500 g packet priced at ৳75 uses `price_bdt=75` and `unit_grams=500`.
4. Set `store`, `market`, `price_date`, `last_updated`, and `in_stock`.
5. Set `source_type` honestly:
   - `manual_unverified`: entered manually but not checked against a current source.
   - `manual_verified`: manually checked against the named shop/source on the recorded date.
   - `retailer_feed`: supplied by an authorized retailer feed.
   - `api`: supplied by an authorized API.
   - `illustrative`: fabricated/demo values only; never use for real-world price claims.
6. Optionally provide `source_url` and a short `note`.

The app filters out invalid prices, non-positive weights, and out-of-stock offers. It matches each offer to the food-composition table, calculates price per edible gram using the food's edible coefficient, and selects the cheapest eligible offer per food. If a real offer exists for a food, an illustrative offer for that same food is ignored.

## Data limitations

- No retailer API or live inventory integration is included.
- `manual_verified` means checked by the project team; it is not a guarantee that the price remains current.
- A price observation is only as current as its `price_date` / `last_updated` values.
- The UI now provides a market selector. The optimizer filters strictly to the selected market before comparing offers, so it does not silently mix prices from different areas. Add separate market labels (for example, `Mirpur, Dhaka` and `Dhanmondi, Dhaka`) only when you have observations for those areas. These labels are examples, not supplied price data.
- Do not enter personal customer data in this file.

## Full Bangladesh food catalog template

`price_template.csv` now contains one row for every food in the project's food-composition dataset (381 rows in this project version), including the English display name and Bengali name. Price, package weight, store, market, and date fields are intentionally blank. This is a data-entry template, **not evidence that all 381 foods are available in shops**. Enter only observed products and prices, and set `in_stock=no` when unavailable.

The market selector lists only market labels that actually exist in the active price file. The bundled sample therefore shows only its demo-market label. To demonstrate two real areas, add verified observations for both areas to `prices.csv`; do not invent prices or stock status.
