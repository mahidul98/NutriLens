from backend.app.nutrition.engine import compute_meal
from backend.app.schemas import MealItem
from backend.app.personalization.meal_completeness import assess_meal_completeness
from backend.app.personalization.models import UserProfile


def profile(diet="omnivore", avoid=None):
    return UserProfile(age=25, sex="male", weight_kg=70, height_cm=170,
                       diet=diet, avoid=avoid or [])


def assess(code, grams, meal="breakfast", diet="omnivore", avoid=None):
    items = [MealItem(fct_code=code, grams=grams)]
    totals = compute_meal(items)
    return assess_meal_completeness(items, totals, profile(diet, avoid), meal)


def test_tea_only_breakfast_gets_food_additions_even_without_gap_report():
    result = assess("14_0008", 200, "breakfast")
    assert result.status == "incomplete"
    assert {"staple", "protein"}.issubset(set(result.missing_components))
    assert result.suggestions


def test_beverage_only_snack_gets_optional_suggestions():
    result = assess("14_0008", 150, "snack")
    assert result.status == "partially_balanced"
    assert result.suggestions


def test_vegetarian_suggestions_exclude_fish_and_meat():
    result = assess("14_0008", 150, "breakfast", diet="vegetarian")
    from backend.app.nutrition.foods import get_food
    assert result.suggestions
    assert all(str(get_food(x.fct_code)["food_group_code"]).zfill(2) not in {"09", "10"}
               for x in result.suggestions)


def test_avoid_list_is_respected():
    result = assess("14_0008", 150, "breakfast", avoid=["banana"])
    assert all("banana" not in x.name_en.lower() for x in result.suggestions)


def test_balanced_full_meal_does_not_force_additions():
    items = [
        MealItem(fct_code="01_0037", grams=180),
        MealItem(fct_code="09_0015", grams=80),
        MealItem(fct_code="03_0007", grams=100),
    ]
    totals = compute_meal(items)
    result = assess_meal_completeness(items, totals, profile(), "lunch")
    assert result.status == "balanced"
    assert result.suggestions == []


def test_report_service_includes_independent_meal_completeness():
    from backend.app.api_models import ReportRequest
    from backend.app.service import run_report

    request = ReportRequest(
        items=[{"fct_code": "14_0008", "grams": 200}],
        profile=profile(),
        meal="breakfast",
    )
    response = run_report(request)
    assert response.meal_completeness.status == "incomplete"
    assert response.meal_completeness.suggestions
    assert "meal_completeness" in response.model_dump()
