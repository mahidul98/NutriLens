"""Daily reference targets for healthy adults, localized to Bangladesh 2025 Annex 8.

Energy remains an equation-based estimate; Annex 8 does not provide an adult
energy equation. Disease-specific/therapeutic targets are intentionally not
implemented here.
"""
from .models import DailyTargets, Target, UserProfile

ACTIVITY = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "active": 1.725}
GOAL_ADJUST = {"maintain": 0.0, "lose": -0.15, "gain": 0.10}
CAL_FLOOR = {"female": 1200.0, "male": 1500.0}  # conservative app floor, not an Annex 8 value


def bmr(p: UserProfile) -> float:
    """Mifflin-St Jeor equation; used as an estimate, not a Bangladesh Annex 8 value."""
    return 10 * p.weight_kg + 6.25 * p.height_cm - 5 * p.age + (5 if p.sex == "male" else -161)


def _adult_iron_10pct(age: int, sex: str) -> float | None:
    """Annex 8.3 iron RNI using its 10% dietary bioavailability column.

    Annex 8 does not list a male iron value for age 65+, so return None rather
    than inventing or carrying forward a value.
    """
    if age >= 65 and sex == "male":
        return None
    if sex == "male":
        return 13.7  # age 18 and 19-65, 10% bioavailability
    return 29.4  # age 18 and 19-65, 10% bioavailability


def daily_targets(p: UserProfile) -> DailyTargets:
    """Return approximate healthy-adult daily targets using Bangladesh 2025 Annex 8.

    The profile model intentionally accepts adults only. Pregnancy, lactation,
    children and disease-specific therapeutic diets are outside this estimator.
    """
    kcal = bmr(p) * ACTIVITY[p.activity] * (1 + GOAL_ADJUST[p.goal])
    floor = CAL_FLOOR[p.sex]
    applied = kcal < floor
    kcal = max(kcal, floor)

    notes = [
        "Bangladesh reference source: National Dietary Guidelines 2025, Annex 8 (pages 107–110).",
        "Energy remains an equation-based estimate, not an Annex 8 value. Fat is set at 30% of estimated energy within the Annex 8 range; carbohydrate is the remaining energy. Sodium uses the general guideline's salt limit, not Annex 8.",
        "Iron uses the Annex 8.3 10% dietary-bioavailability column; actual needs vary. Vitamin A REq and folate DFE are approximate matches to the app's food-database fields.",
        "For generally healthy adults only. Pregnancy, breastfeeding, clinical conditions and therapeutic diets require individualized assessment by a qualified clinician or dietitian; the app does not generate disease-specific prescriptions.",
    ]

    # Annex 8.1 gives a specific value for age 18; adults 19+ are shown as
    # 33–66 g/day for reference body weights 45–75 kg. 0.8 g/kg is used as a
    # transparent midpoint approximation for the adult table, not a clinical dose.
    if p.age == 18:
        protein = 57.9 if p.sex == "male" else 47.4
        fiber = 28.0 if p.sex == "male" else 22.0
        fat_pct = 0.30  # within the 25–35% age-18 range
    else:
        protein = 0.8 * p.weight_kg
        fiber = 30.0 if p.sex == "male" else 25.0
        fat_pct = 0.30  # within the 20–35% adult range
        if not 45 <= p.weight_kg <= 75:
            notes.append("Protein is scaled at 0.8 g/kg outside Annex 8's 45–75 kg adult reference-weight range; treat this as an approximation.")

    fat = fat_pct * kcal / 9
    carb = max((kcal - protein * 4 - fat * 9) / 4, 0.0)

    # Annex 8.2 vitamin requirements, and 8.3 calcium requirements.
    vit_a = 600.0
    vit_c = 40.0 if p.age == 18 else 45.0
    folate = 400.0  # DFE
    if p.age == 18:
        calcium = 1300.0
    elif p.age >= 65:
        calcium = 1300.0
    elif p.sex == "female" and p.age >= 51:
        calcium = 1300.0
    else:
        calcium = 1000.0

    iron = _adult_iron_10pct(p.age, p.sex)

    targets = {
        "energy_kcal": Target(value=round(kcal), kind="goal"),
        "protein_g": Target(value=round(protein, 1), kind="min"),
        "fat_g": Target(value=round(fat, 1), kind="goal"),
        "carb_g": Target(value=round(carb, 1), kind="goal"),
        "fiber_g": Target(value=fiber, kind="min"),
        "sodium_mg": Target(value=2000.0, kind="max"),
        "calcium_mg": Target(value=calcium, kind="min"),
        "vitamin_a_rae_mcg": Target(value=vit_a, kind="min"),
        "vitamin_c_mg": Target(value=vit_c, kind="min"),
        "folate_mcg": Target(value=folate, kind="min"),
    }
    if iron is not None:
        targets["iron_mg"] = Target(value=iron, kind="min")

    return DailyTargets(kcal_floor_applied=applied, targets=targets, notes=notes)
