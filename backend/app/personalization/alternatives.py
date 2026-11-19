"""Price-independent, food-composition-table alternatives for nutrient gaps."""
from __future__ import annotations

import pandas as pd

from ..nutrition.foods import load_foods
from ..schemas import MealTotals
from .models import MealReport, UserProfile

NUTRIENT_COLUMNS = {
    "protein_g": "protein_g",
    "fiber_g": "fiber_g",
    "calcium_mg": "calcium_mg",
    "iron_mg": "iron_mg",
    "vitamin_a_rae_mcg": "vitamin_a_rae_mcg",
    "vitamin_c_mg": "vitamin_c_mg",
    "folate_mcg": "folate_mcg",
}


def _suggested_portion(row: pd.Series) -> int:
    """Conservative example serving sizes; not a prescribed portion."""
    group = str(row.get("food_group_code", "")).zfill(2)
    name = str(row.get("name_en", "")).lower()
    if group == "06":
        return 20
    if group == "11":
        return 50
    if group == "12":
        if "powder" in name:
            return 20
        if any(term in name for term in ("cheese", "butter", "ghee")):
            return 30
        return 200
    if group in {"09", "10"}:
        return 25 if "dried" in name else 75
    if group == "02":
        return 50 if "raw" in name or "dry" in name else 100
    if group in {"03", "04", "05", "08"}:
        return 100
    return 75 if group == "01" else 100


def suggest_food_alternatives(
    totals: MealTotals,
    report: MealReport,
    profile: UserProfile,
    limit: int = 5,
) -> list[dict]:
    """Suggest foods rich in nutrients flagged low; never uses prices or inventory."""
    if not report.gaps or limit <= 0:
        return []

    foods = load_foods().copy()
    consumed = {line.fct_code for line in totals.lines}
    foods = foods[~foods["code"].astype(str).isin(consumed)]

    # Match the diet rules used by the main meal report.
    groups = foods["food_group_code"].astype(str).str.zfill(2)
    # Spices, fats, beverages and miscellaneous products are poor default meal swaps.
    foods = foods[~groups.isin({"07", "13", "14", "15"})]
    groups = foods["food_group_code"].astype(str).str.zfill(2)
    if profile.diet == "vegetarian":
        foods = foods[~groups.isin({"09", "10"})]
    elif profile.diet == "pescatarian":
        foods = foods[groups != "10"]
    foods = foods[~foods["name_en"].fillna("").str.lower().str.contains("condensed|sweetened", regex=True)]

    avoid_terms = [x.strip().lower() for x in profile.avoid if x.strip()]
    if avoid_terms:
        names = (foods["name_en"].fillna("").astype(str) + " " +
                 foods.get("name_bn_roman", pd.Series("", index=foods.index)).fillna("").astype(str)).str.lower()
        foods = foods[~names.apply(lambda name: any(term in name for term in avoid_terms))]

    if "is_recipe_calc" in foods:
        foods = foods[~foods["is_recipe_calc"].fillna(False).astype(bool)]

    result: list[dict] = []
    used_codes: set[str] = set()
    line_by_nutrient = {line.nutrient: line for line in report.lines}

    for nutrient in report.gaps:
        column = NUTRIENT_COLUMNS.get(nutrient)
        line = line_by_nutrient.get(nutrient)
        if not column or line is None or column not in foods.columns:
            continue
        values = pd.to_numeric(foods[column], errors="coerce")
        candidates = foods[values.notna() & (values > 0)].copy()
        candidates["_nutrient_value"] = values[values.notna() & (values > 0)]
        candidates = candidates[~candidates["code"].astype(str).isin(used_codes)]
        if candidates.empty:
            continue

        # Rank by contribution from a plausible example serving, not an arbitrary 100 g.
        candidates["_portion_g"] = candidates.apply(_suggested_portion, axis=1)
        candidates["_portion_value"] = candidates["_nutrient_value"] * candidates["_portion_g"] / 100.0
        candidates["_coverage"] = candidates["_portion_value"] / max(float(line.meal_target), 1e-9)
        candidates = candidates.sort_values(["_coverage", "_portion_value"], ascending=False)
        added_for_gap = 0
        for _, row in candidates.iterrows():
            code = str(row["code"])
            if code in used_codes:
                continue
            used_codes.add(code)
            result.append({
                "fct_code": code,
                "name_en": str(row["name_en"]),
                "name_bn": "" if pd.isna(row.get("name_bn")) else str(row.get("name_bn", "")),
                "nutrient": nutrient,
                "nutrient_per_100g": round(float(row["_nutrient_value"]), 1),
                "meal_target": round(float(line.meal_target), 1),
                "coverage_pct": round(float(row["_coverage"]) * 100, 1),
                "portion_g": int(row["_portion_g"]),
            })
            added_for_gap += 1
            if added_for_gap >= 3 or len(result) >= limit:
                break
        if len(result) >= limit:
            break

    return result
