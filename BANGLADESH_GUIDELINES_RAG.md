# Bangladesh Dietary Guidelines + RAG integration

## What is integrated
- Local lexical retrieval over curated passages from the National Dietary Guidelines for Bangladesh 2025 (National Nutrition Services; WHO-hosted official PDF).
- Source title, printed page number and official PDF link are shown with each retrieved passage.
- The Streamlit nutrition report shows one Bangladesh dietary-guidance expander after the report notes.
- English/Bangla labels are translated through the existing language dictionary.
- Retrieval is offline. Meal/profile data is not sent to a retrieval service.
- The deterministic nutrient engine remains separate from retrieval. Adult daily targets now use applicable Bangladesh 2025 Annex 8 reference values; retrieval supports explanations and does not calculate clinical requirements.

## Current scope and safety
This is a curated general-guidance retrieval layer, not a full-document vector database. It indexes selected general guidance, food groups, water, food safety, cooking, healthy plate and population nutrient-intake context. It does not yet retrieve the complete age-specific and disease-specific sections as individualized clinical advice. Do not use the population intake ranges as personal prescriptions. Pregnancy, lactation, child feeding and disease-specific diets require appropriate professional guidance.

## Source
National Nutrition Services. *National Dietary Guidelines for Bangladesh* (August 2025). WHO-hosted official PDF: https://cdn.who.int/media/docs/default-source/searo/bangladesh/national-dietary-guidelines-for-bangladesh.pdf

Curated passages retain printed page references in `backend/app/rag/guideline_chunks.json`.

## Tests
Run `pytest -q`.


## Daily target localization
For generally healthy adults aged 18–80, targets use Bangladesh 2025 Annex 8 (tables 8.1–8.3, pages 107–109) for protein, fat range, fibre, vitamin A, vitamin C, folate, calcium and iron where a table value is available. Iron uses the 10% dietary bioavailability column and is omitted for males aged 65+ because no value is listed. Vitamin A REq and folate DFE are approximate matches to the app's food-database fields. Energy is still equation-based; carbohydrate is derived as remaining energy; sodium uses the general guideline's salt limit.

No pregnancy, lactation, child or disease-specific therapeutic targets are generated. People with clinical conditions must obtain individualized advice from a qualified clinician or dietitian.
