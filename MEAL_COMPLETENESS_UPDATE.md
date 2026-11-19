# Meal Completeness Update

## What changed

- Added a separate rule-based meal-composition checker using the existing Bangladesh food-composition table.
- Added `meal_completeness` to the report API response.
- Connected the checker in `backend/app/service.py`.
- Added a Streamlit section called **Meal balance and food additions**.
- Kept nutrient-gap alternatives and the budget optimizer separate and unchanged.
- Recommendations respect vegetarian/pescatarian settings and the user's avoid list.
- The checker uses edible weights from the nutrition engine where available.

## Meal rules

- Breakfast: staple and protein are core components; fruit is an optional complementary idea.
- Lunch/dinner: staple, protein and vegetables are core components.
- Snack: protein is the only core component; fruit is optional. Snacks are not assessed as full meals.

## Important limitations

- Food-group and portion thresholds are transparent heuristics, not clinical nutrition standards.
- Suggested portions are examples and are not individualized prescriptions.
- Suggestions are not price-ranked; the existing budget optimizer remains a separate feature.
- The current food table does not contain a dedicated samosa entry. If photo recognition maps samosa to a different food-table code, the completeness check will use that selected code. Review/correct the food match before relying on the result.
- The checker assesses broad food-group composition; it does not prove that a meal is nutritionally adequate.

## Validation

The focused non-vision test set passed in the build environment. Full test collection requires the project's `google-genai` dependency, which was not installed in the build environment.
