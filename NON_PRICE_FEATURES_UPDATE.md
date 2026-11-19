# Non-price feature update

This update adds improvements that do not depend on the real-market-price dataset.

## 1. Food identification and portion review

- The vision prompt now prefers a matching prepared-dish entry when the Bangladesh food table has one.
- It asks Gemini to decompose a dish only into visually identifiable ingredients and avoid inventing hidden ingredients.
- It no longer automatically adds oil/ghee merely because a dish looks glossy or fried.
- It asks for rounded portion estimates and makes clear that photo-derived grams are approximate.
- The UI explains that model confidence is not a calibrated probability. Users can still change the food match and grams before calculation.

## 2. Food ideas for nutrient gaps

- New module: `backend/app/personalization/alternatives.py`.
- It ranks foods from the Bangladesh food-composition table against nutrients flagged low in the meal report.
- It applies vegetarian/pescatarian filters and the user's avoid list.
- It uses example serving sizes and excludes spices, oils, beverages, and miscellaneous items as default meal swaps.
- It does not read prices or inventory. It is separate from the budget-aware optimizer.
- Suggestions are educational examples, not prescribed portions or medical advice.

## 3. Meal history and progress

- New meal entries store an ISO timestamp in session state.
- The History page summarizes logged meals from the last seven days with calorie and protein trend charts.
- Users can export the session history as CSV.
- History remains session-only and keeps up to 30 recent analyses. It is not a permanent account-level food diary, and averages only represent meals entered in the session.

## Validation

- `python -m compileall -q app.py backend tests` passes.
- 43 tests pass across alternatives, guideline RAG, personalization, nutrition engine, and optimizer modules.
- The full test suite could not be collected in this build environment because `google-genai` is not installed here; perception/service tests import that package. It is listed in the project's requirements and should be installed in the user's project environment.
