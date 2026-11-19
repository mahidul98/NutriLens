from pathlib import Path

import pandas as pd

from ..nutrition.foods import load_foods

ROOT = Path(__file__).resolve().parents[3]
REAL = ROOT / "data" / "prices" / "prices.csv"
SAMPLE = ROOT / "data" / "prices" / "sample_prices.csv"
REQUIRED = ["fct_code", "price_bdt", "unit_grams", "store", "price_date", "in_stock"]
OPTIONAL_DEFAULTS = {
    "market": "Unspecified market",
    "source_type": "manual_unverified",
    "last_updated": "",
    "unit_label": "",
    "source_url": "",
    "note": "",
}
VALID_SOURCE_TYPES = {"illustrative", "manual_unverified", "manual_verified", "retailer_feed", "api"}


def available_markets(path: Path | None = None) -> list[str]:
    """Return distinct market labels from the active price file."""
    if path is None:
        path = REAL if REAL.exists() else SAMPLE
    path = Path(path)
    if not path.exists():
        return []
    try:
        df = pd.read_csv(path, encoding="utf-8-sig", usecols=lambda c: c == "market")
    except (ValueError, pd.errors.EmptyDataError):
        return []
    if "market" not in df.columns:
        return ["Unspecified market"]
    values = sorted({str(v).strip() for v in df["market"].dropna() if str(v).strip()})
    return values or ["Unspecified market"]


def load_catalog(path: Path | None = None, market: str | None = None) -> tuple[pd.DataFrame, bool]:
    """Load grocery offers and join them to the Bangladesh food-composition table.

    Old price files remain supported. Optional provenance fields are added with
    conservative defaults so an unverified price is never presented as verified.
    The cheapest eligible in-stock offer is retained for each FCT food.
    """
    if path is None:
        path = REAL if REAL.exists() else SAMPLE
    path = Path(path)
    is_sample = path.name.startswith("sample")

    df = pd.read_csv(path, encoding="utf-8-sig", dtype={"fct_code": str})
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing columns: {missing}")

    for column, default in OPTIONAL_DEFAULTS.items():
        if column not in df.columns:
            df[column] = default
        df[column] = df[column].fillna(default).astype(str).str.strip()

    df = df[REQUIRED + list(OPTIONAL_DEFAULTS)].copy()
    # A selected market is a strict filter: never silently mix prices across areas.
    if market and market != "All available markets":
        df = df[df["market"].astype(str).str.strip() == market].copy()
    df["price_bdt"] = pd.to_numeric(df["price_bdt"], errors="coerce")
    df["unit_grams"] = pd.to_numeric(df["unit_grams"], errors="coerce")
    df["store"] = df["store"].fillna("").astype(str).str.strip()
    df["in_stock"] = df["in_stock"].astype(str).str.strip().str.lower()
    df["source_type"] = df["source_type"].str.lower().replace("", "manual_unverified")
    unknown_sources = sorted(set(df["source_type"]) - VALID_SOURCE_TYPES)
    if unknown_sources:
        raise ValueError(
            "Unsupported source_type value(s): " + ", ".join(unknown_sources)
            + ". Use: " + ", ".join(sorted(VALID_SOURCE_TYPES))
        )

    df = df[(df["price_bdt"] > 0) & (df["unit_grams"] > 0)]
    df = df[df["in_stock"].isin(["yes", "y", "true", "1", "in stock"])]
    if df.empty:
        return df, is_sample

    foods = load_foods().reset_index(drop=True)
    # Keep all nutrient columns and authoritative food names from the
    # Bangladesh food-composition table.
    food_columns = [c for c in foods.columns if c != "code"]
    df = df.merge(foods[["code", *food_columns]], left_on="fct_code", right_on="code", how="inner")
    if df.empty:
        return df, is_sample

    # If real offers exist for a food, never let a cheap demo placeholder
    # displace them. Illustrative rows remain usable only as a fallback.
    real_codes = set(df.loc[df["source_type"] != "illustrative", "fct_code"])
    df = df[~((df["source_type"] == "illustrative") & df["fct_code"].isin(real_codes))].copy()
    coeff = pd.to_numeric(df["edible_coeff"], errors="coerce").fillna(1.0).clip(0.1, 1.0)
    df["cost_per_edible_g"] = df["price_bdt"] / (df["unit_grams"] * coeff)
    df["price_per_kg_bdt"] = df["price_bdt"] / df["unit_grams"] * 1000.0
    # Prefer verified/current data when prices tie; never upgrade an unverified
    # source merely because it appears first in the CSV.
    source_rank = {"api": 0, "retailer_feed": 1, "manual_verified": 2,
                   "manual_unverified": 3, "illustrative": 4}
    df["_source_rank"] = df["source_type"].map(source_rank).fillna(9)
    df = df.sort_values(["cost_per_edible_g", "_source_rank", "store"])
    df = df.drop_duplicates("fct_code", keep="first").drop(columns="_source_rank")
    is_sample = is_sample or bool(df["source_type"].eq("illustrative").any())
    return df.reset_index(drop=True), is_sample
