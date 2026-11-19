# Bangladesh Dietary Guidelines retrieval

This module implements a small local retrieval-augmented guidance layer using lexical/BM25-style retrieval over curated passages from the **National Dietary Guidelines for Bangladesh 2025**. It runs offline and does not send profile or meal data to an external service.

Primary source: WHO-hosted official PDF, published by National Nutrition Services (NNS), August 2025: https://cdn.who.int/media/docs/default-source/searo/bangladesh/national-dietary-guidelines-for-bangladesh.pdf

Passages retain page references in `guideline_chunks.json`. The retrieval layer supplies source passages for user-facing explanations; it does not replace the deterministic nutrient engine or calculate clinical nutrient requirements. The table of population nutrient intake ranges on page 5 is population-level guidance, not a personalized prescription.

Scope: this initial prototype indexes selected general guidance and the healthy plate/food pyramid. It does not implement age-specific or disease-specific clinical recommendations.


## Annex 8 target localization (healthy adults only)
The adult target calculator reads Bangladesh 2025 Annex 8 tables 8.1–8.3 for protein, fat range, fibre, vitamins, calcium and iron. It uses an explicit 10% dietary-iron-bioavailability reference; Annex 8 provides several bioavailability columns, so this must not be interpreted as a universal or clinical iron prescription. Male iron is omitted at age 65+ because Annex 8 does not list a value for that group.

Energy remains a Mifflin–St Jeor/activity/goal estimate because Annex 8 does not provide an adult individualized energy equation. Carbohydrate is the residual after protein and fat. Sodium uses the general guideline's salt limit, not Annex 8. Disease-specific recommendations, pregnancy, lactation and child requirements are not automated. The profile model is restricted to adults aged 18–80.
