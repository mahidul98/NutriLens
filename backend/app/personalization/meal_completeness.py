"""Heuristic meal-composition suggestions using the Bangladesh food table.

This module is deliberately separate from nutrient-gap reporting and the
budget optimizer. It offers optional food ideas; it does not prescribe a diet.
"""
from __future__ import annotations

import math
import pandas as pd

from ..nutrition.foods import load_foods
from ..schemas import MealItem, MealTotals
from .models import MealCompleteness, MealSuggestion, UserProfile

STAPLES = {"01", "05"}
LEGUMES = {"02"}
VEGETABLES = {"03", "04"}
FRUITS = {"08"}
FISH = {"09"}
MEAT = {"10"}
EGGS = {"11"}
DAIRY = {"12"}
NUTS = {"06"}
PROTEIN_GROUPS = LEGUMES | FISH | MEAT | EGGS | DAIRY | NUTS

# Example serving sizes, in edible grams. These are ranking/display defaults,
# not individualized prescriptions.
PORTIONS = {
    "staple": 100, "protein": 75, "vegetables": 100, "fruit": 100,
}
MIN_PORTIONS = {
    "staple": 50, "protein": 35, "vegetables": 50, "fruit": 60,
}
CATEGORY_GROUPS = {
    "staple": STAPLES,
    "protein": PROTEIN_GROUPS,
    "vegetables": VEGETABLES,
    "fruit": FRUITS,
}
CATEGORY_LABELS = {
    "staple": "staple food",
    "protein": "protein-rich food",
    "vegetables": "vegetables",
    "fruit": "fruit",
}

def _group(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().zfill(2)

def _requirements(meal: str) -> tuple[set[str], list[str]]:
    """Return core components and optional components for this meal type."""
    if meal == "breakfast":
        return {"staple", "protein"}, ["fruit"]
    if meal in {"lunch", "dinner"}:
        return {"staple", "protein", "vegetables"}, []
    # A snack is not assessed as a full meal. Offer a protein option and fruit
    # as a complementary choice, without requiring a staple or vegetables.
    return {"protein"}, ["fruit"]

def _is_allowed(row: pd.Series, profile: UserProfile) -> bool:
    group = _group(row.get("food_group_code"))
    if profile.diet == "vegetarian" and group in FISH | MEAT:
        return False
    if profile.diet == "pescatarian" and group in MEAT:
        return False

    name = str(row.get("name_en", "")).lower()
    roman = str(row.get("name_bn_roman", "")).lower()
    bangla = str(row.get("name_bn", "")).lower()
    for term in profile.avoid:
        term = str(term).strip().lower()
        if term and (term in name or term in roman or term in bangla):
            return False

    # Prepared entries marked as recipe calculations (for example boiled
    # rice, boiled pulses and boiled eggs) remain eligible: they are useful
    # consumer-facing food choices in this dataset.
    return True

def _candidate_preference(row: pd.Series, category: str) -> tuple[int, int]:
    """Prefer familiar, practical foods over obscure/raw ingredient records."""
    group = _group(row.get("food_group_code"))
    name = str(row.get("name_en", "")).lower()
    roman = str(row.get("name_bn_roman", "")).lower()
    combined = f"{name} {roman}"

    # Avoid dried fish, raw meat/fish, bran/feed ingredients and obscure
    # experimental cultivar labels in consumer-facing default suggestions.
    if group == "09" and "dried" in name:
        return (9, 0)
    if group == "10" and "raw" in name:
        return (9, 0)
    if group == "11" and ("raw" in name or "yolk" in name):
        return (9, 0)
    if any(term in combined for term in ("rice bran", "feed grade", "sp7", "sp8")):
        return (9, 0)

    if category == "protein":
        group_rank = {"11": 0, "02": 1, "12": 2, "09": 3, "10": 4, "06": 5}.get(group, 8)
        preparation_rank = 0 if any(x in name for x in ("boiled", "cooked", "curd", "milk")) else 1
        if group == "09" and "raw" in name:
            preparation_rank = 3
        return (group_rank, preparation_rank)

    familiar_terms = {
        "staple": ("bread", "boiled", "rice flakes", "puffed rice", "roti", "khichuri"),
        "vegetables": ("cabbage", "carrot", "cauliflower", "brinjal", "pumpkin", "spinach", "amaranth", "gourd"),
        "fruit": ("banana", "guava", "papaya", "orange", "mango", "watermelon", "apple"),
    }.get(category, ())
    familiar_rank = 0 if any(term in combined for term in familiar_terms) else 1
    if category == "vegetables" and group == "04":
        familiar_rank += 1  # prefer familiar vegetable entries before leafy varieties
    raw_penalty = 1 if category == "staple" and any(x in name for x in ("raw", "dried", "flour", "bran")) else 0
    return (familiar_rank, raw_penalty)


def _candidate_score(row: pd.Series, category: str) -> float:
    """Rank plausible examples using the nutrient most relevant to category."""
    portion = PORTIONS[category]
    if category == "protein":
        key, weight = "protein_g", 1.0
    elif category == "vegetables":
        key, weight = "fiber_g", 1.0
    elif category == "fruit":
        key, weight = "vitamin_c_mg", 0.6
    else:
        key, weight = "energy_kcal", 0.35

    raw = row.get(key)
    try:
        value = float(raw)
        if not math.isfinite(value) or value < 0:
            value = 0.0
    except (TypeError, ValueError):
        value = 0.0

    score = value * portion / 100.0 * weight
    name = str(row.get("name_en", "")).lower()
    # Prefer ready-to-eat/cooked entries when available; raw fruit/vegetable
    # entries remain eligible because those are commonly eaten uncooked.
    if category == "protein" and any(x in name for x in ("raw", "dried")):
        score *= 0.65
    if any(x in name for x in ("powder", "condensed", "sweetened")):
        score *= 0.45
    return score

def _portion_for(category: str, row: pd.Series) -> int:
    group = _group(row.get("food_group_code"))
    if category == "protein":
        if group == "11":
            return 50
        if group == "12":
            return 150
        if group == "06":
            return 20
        return 75 if group in FISH | MEAT else 100
    return PORTIONS[category]

def _suggestions_for_category(
    foods: pd.DataFrame, category: str, profile: UserProfile, consumed: set[str],
    limit: int,
) -> list[MealSuggestion]:
    groups = CATEGORY_GROUPS[category]
    candidates = foods[foods["food_group_code"].map(_group).isin(groups)].copy()
    candidates = candidates[~candidates["code"].astype(str).isin(consumed)]
    if candidates.empty:
        return []
    candidates = candidates[candidates.apply(lambda r: _is_allowed(r, profile), axis=1)]
    if candidates.empty:
        return []
    candidates = candidates[~candidates.apply(
        lambda r: _candidate_preference(r, category)[0] >= 9, axis=1
    )]
    if candidates.empty:
        return []
    candidates["_preference"] = candidates.apply(
        lambda r: _candidate_preference(r, category), axis=1
    )
    candidates["_score"] = candidates.apply(lambda r: _candidate_score(r, category), axis=1)
    candidates = candidates.sort_values(["_preference", "_score", "name_en"], ascending=[True, False, True])

    result: list[MealSuggestion] = []
    seen_groups: set[str] = set()
    for _, row in candidates.iterrows():
        code = str(row["code"])
        candidate_group = _group(row.get("food_group_code"))
        # Avoid filling a short protein shortlist with several egg varieties;
        # offer a second source such as pulses or dairy where possible.
        if category == "protein" and candidate_group in seen_groups:
            continue
        seen_groups.add(candidate_group)
        bn = row.get("name_bn", "")
        name_bn = "" if pd.isna(bn) else str(bn)
        result.append(MealSuggestion(
            fct_code=code,
            name_en=str(row["name_en"]),
            name_bn=name_bn,
            reason=f"Adds a {CATEGORY_LABELS[category]} to complement this {category_label_meal(category)}.",
            portion_g=_portion_for(category, row),
            category=category,
        ))
        if len(result) >= limit:
            break
    return result

def category_label_meal(category: str) -> str:
    # Kept as a small helper so recommendation reasons remain readable.
    return "meal"

def assess_meal_completeness(
    items: list[MealItem], totals: MealTotals, profile: UserProfile,
    meal: str, limit: int = 5,
) -> MealCompleteness:
    """Assess food-group composition independently from nutrient gaps."""
    if limit <= 0:
        return MealCompleteness(status="incomplete")

    foods = load_foods()
    consumed_codes: set[str] = set()
    consumed_grams: dict[str, float] = {}

    # Use edible weights from the nutrition engine, so bones/peels marked as
    # as_purchased do not inflate the apparent food-group serving.
    edible_by_code = {line.fct_code: line.edible_grams for line in totals.lines}
    for item in items:
        code = str(item.fct_code)
        if code not in foods.index:
            continue
        consumed_codes.add(code)
        group = _group(foods.loc[code].get("food_group_code"))
        edible_grams = float(edible_by_code.get(code, item.grams))
        category = next((cat for cat, groups in CATEGORY_GROUPS.items() if group in groups), None)
        if category:
            consumed_grams[category] = consumed_grams.get(category, 0.0) + edible_grams

    required, optional = _requirements(meal)
    missing = {cat for cat in required if consumed_grams.get(cat, 0.0) < MIN_PORTIONS[cat]}
    optional_missing = [cat for cat in optional if consumed_grams.get(cat, 0.0) < MIN_PORTIONS[cat]]

    if not missing and not optional_missing:
        return MealCompleteness(
            status="balanced",
            notes=["No major food-group addition was identified by this basic check."],
        )

    ordered_categories = [c for c in ("protein", "staple", "vegetables", "fruit") if c in missing]
    # Optional components are lower priority and only fill remaining display slots.
    ordered_categories.extend(c for c in optional_missing if c not in missing)

    suggestions: list[MealSuggestion] = []
    per_category = 2 if len(ordered_categories) > 1 else limit
    for category in ordered_categories:
        remaining = limit - len(suggestions)
        if remaining <= 0:
            break
        suggestions.extend(_suggestions_for_category(
            foods, category, profile, consumed_codes, min(per_category, remaining)
        ))

    status = ("incomplete" if len(missing) >= 2 else
              "partially_balanced" if missing else "balanced")
    notes = [
        "Optional food ideas are based on food groups and example portions, not a medical assessment.",
        "Nutrient gaps and budget-based shopping suggestions are assessed separately.",
    ]
    if not suggestions:
        notes.append("No suitable food-table suggestions were found after applying your diet and avoid preferences.")

    return MealCompleteness(
        status=status,
        missing_components=ordered_categories,
        suggestions=suggestions[:limit],
        notes=notes,
    )
