from backend.app.nutrition.engine import compute_meal
from backend.app.schemas import MealItem
from backend.app.personalization.alternatives import suggest_food_alternatives
from backend.app.personalization.models import MealReport, ReportLine, UserProfile


def profile(diet="omnivore", avoid=None):
    return UserProfile(age=25, sex="male", weight_kg=70, height_cm=170,
                       diet=diet, avoid=avoid or [])


def test_alternatives_are_price_independent_and_exclude_current_foods():
    foods = compute_meal([MealItem(fct_code="01_0001", grams=100)])
    report = MealReport(meal="lunch", lines=[
        ReportLine(nutrient="protein_g", amount=1, meal_target=20, kind="min",
                   percent=5, status="low")
    ], gaps=["protein_g"], excesses=[], notes=[])
    suggestions = suggest_food_alternatives(foods, report, profile())
    assert suggestions
    assert all(item["fct_code"] != "01_0001" for item in suggestions)
    assert all(1 <= item["portion_g"] <= 200 for item in suggestions)
    assert all("price" not in item for item in suggestions)


def test_no_suggestions_when_no_gaps():
    foods = compute_meal([MealItem(fct_code="01_0001", grams=100)])
    report = MealReport(meal="lunch", lines=[], gaps=[], excesses=[], notes=[])
    assert suggest_food_alternatives(foods, report, profile()) == []


def test_vegetarian_alternatives_exclude_fish_and_meat():
    from backend.app.nutrition.foods import get_food

    foods = compute_meal([MealItem(fct_code="01_0001", grams=100)])
    report = MealReport(meal="lunch", lines=[
        ReportLine(nutrient="protein_g", amount=1, meal_target=20, kind="min",
                   percent=5, status="low")
    ], gaps=["protein_g"], excesses=[], notes=[])
    suggestions = suggest_food_alternatives(foods, report, profile("vegetarian"))
    assert suggestions
    assert all(str(get_food(item["fct_code"])["food_group_code"]).zfill(2) not in {"09", "10"}
               for item in suggestions)
