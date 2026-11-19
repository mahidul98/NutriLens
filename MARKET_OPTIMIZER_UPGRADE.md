# Market optimizer upgrade — November 17, 2026

## What changed

- Grocery offers now carry market, source type, last-updated date, optional source URL, and note metadata.
- Catalog loading remains backward-compatible with the older price CSV format.
- Bangla names and authoritative display names from the Bangladesh food-composition table are included in optimizer results.
- The optimizer ignores an illustrative offer when a non-illustrative offer exists for the same food.
- Shopping recommendations now display market/source/date provenance and normalized BDT/kg, alongside the estimated cost for the recommended quantity.
- Demo pricing warning now explicitly says the inventory is not from real shops and is not live.
- `data/prices/README.md` documents how to prepare a real price file and how source labels must be used.

## Important limitation

The bundled `sample_prices.csv` still contains illustrative values. This update does not connect to a retailer, verify current market prices, or provide live inventory. Do not present these values as actual market prices. Until a market selector is added, keep a real `prices.csv` scoped to one intended market/area.

## Run locally

```powershell
.\venv\Scripts\Activate.ps1
python -m streamlit run app.py
```

## Tests

Passed in the available inspection environment:

```text
30 passed
```

These were optimizer, nutrition engine, and personalization tests. The service/API tests could not be collected in this inspection environment because `google-genai` was not installed there; it is listed in the project's `requirements.txt`.
