import pandas as pd
import pytest

from backend.app.nutrition.engine import TRACKED, compute_meal
from backend.app.optimizer.catalog import load_catalog
from backend.app.optimizer.optimizer import plan_addons
from backend.app.personalization.models import UserProfile
from backend.app.personalization.report import MEAL_SHARE, build_report
from backend.app.personalization.targets import daily_targets
from backend.app.schemas import MealItem, MealTotals

ROWS = """fct_code,name_en,price_bdt,unit_grams,store,price_date,in_stock,note
02_0008,lentil,130,1000,A,2026-10-20,yes,
03_0007,cabbage,40,1000,A,2026-10-20,yes,
04_0007,beet greens,40,1000,A,2026-10-20,yes,
04_0028,sweet potato leaves,30,1000,A,2026-10-20,yes,
05_0005,potato,50,1000,A,2026-10-20,yes,
09_0068,tilapia,10,1000,A,2026-10-20,yes,
11_0001,egg,140,660,A,2026-10-20,yes,
03_0008,carrot,60,0,A,2026-10-20,yes,
08_0017,jackfruit,60,1000,A,2026-10-20,no,
02_0008,lentil dear,300,1000,B,2026-10-20,yes,
"""


def _setup(tmp_path, **profile_kw):
    p = tmp_path / "test_prices.csv"
    p.write_text(ROWS, encoding="utf-8")
    catalog, _ = load_catalog(p)
    base = dict(age=21, sex="male", weight_kg=68, height_cm=172, activity="light", goal="maintain")
    base.update(profile_kw)
    profile = UserProfile(**base)
    totals = compute_meal([MealItem(fct_code="01_0024", grams=150)])  # a plain rice meal
    targets = daily_targets(profile)
    report = build_report(totals, targets, "lunch")
    return catalog, profile, totals, targets, report


def test_loader_filters_and_keeps_cheapest(tmp_path):
    p = tmp_path / "test_prices.csv"
    p.write_text(ROWS, encoding="utf-8")
    cat, is_sample = load_catalog(p)
    codes = set(cat["fct_code"])
    assert "03_0008" not in codes      # unit_grams = 0
    assert "08_0017" not in codes      # out of stock
    assert cat[cat["fct_code"] == "02_0008"].iloc[0]["store"] == "A"   # cheaper offer kept
    assert not is_sample


def test_plan_improves_gaps(tmp_path):
    catalog, profile, totals, targets, report = _setup(tmp_path)
    res = plan_addons(totals, targets, report, profile, "lunch", catalog=catalog)
    assert res.status == "ok" and res.items and res.total_cost_bdt > 0
    assert any(res.after[g] > res.before[g] for g in report.gaps if g in res.after)
    assert set(res.remaining_gaps) <= set(report.gaps)


def test_vegetarian_gets_no_fish(tmp_path):
    catalog, profile, totals, targets, report = _setup(tmp_path, diet="vegetarian")
    res = plan_addons(totals, targets, report, profile, "lunch", catalog=catalog)
    assert all(not it.fct_code.startswith(("09_", "10_")) for it in res.items)


def test_avoid_keyword_respected(tmp_path):
    catalog, profile, totals, targets, report = _setup(tmp_path, avoid=["egg"])
    res = plan_addons(totals, targets, report, profile, "lunch", catalog=catalog)
    assert all(it.fct_code != "11_0001" for it in res.items)


def test_budget_respected(tmp_path):
    catalog, profile, totals, targets, report = _setup(tmp_path, budget_bdt_per_day=60)
    res = plan_addons(totals, targets, report, profile, "lunch", catalog=catalog)
    assert res.total_cost_bdt <= 60 * MEAL_SHARE["lunch"] * 0.5 + 0.5


def test_energy_cap_respected(tmp_path):
    catalog, profile, totals, targets, report = _setup(tmp_path, goal="lose")
    res = plan_addons(totals, targets, report, profile, "lunch", catalog=catalog)
    cap = max(80.0,
              1.10 * targets.targets["energy_kcal"].value * MEAL_SHARE["lunch"]
              - totals.totals["energy_kcal"])
    assert res.after["energy_kcal"] - res.before["energy_kcal"] <= cap + 1


def test_nothing_needed_when_meal_is_full(tmp_path):
    catalog, profile, _, targets, _ = _setup(tmp_path)
    full = MealTotals(lines=[], totals={n: 10000.0 for n in TRACKED}, unknown_by_nutrient={})
    report = build_report(full, targets, "lunch")
    res = plan_addons(full, targets, report, profile, "lunch", catalog=catalog)
    assert res.status == "nothing_needed"


def test_empty_catalog_reported(tmp_path):
    _, profile, totals, targets, report = _setup(tmp_path)
    res = plan_addons(totals, targets, report, profile, "lunch", catalog=pd.DataFrame())
    assert res.status == "no_catalog"


def test_sample_flag_adds_warning(tmp_path):
    catalog, profile, totals, targets, report = _setup(tmp_path)
    res = plan_addons(totals, targets, report, profile, "lunch",
                      catalog=catalog, catalog_is_sample=True)
    assert any("DEVELOPMENT SAMPLE" in n for n in res.notes)

def test_catalog_adds_provenance_defaults_for_legacy_price_files(tmp_path):
    p = tmp_path / "legacy_prices.csv"
    p.write_text(ROWS, encoding="utf-8")
    cat, is_sample = load_catalog(p)
    assert not is_sample
    assert set(cat["source_type"]) == {"manual_unverified"}
    assert "market" in cat.columns and "name_bn" in cat.columns


def test_catalog_keeps_provenance_and_bangla_names(tmp_path):
    p = tmp_path / "prices.csv"
    p.write_text(
        "fct_code,price_bdt,unit_grams,store,price_date,in_stock,market,source_type,last_updated\n"
        "02_0008,140,1000,Local shop,2026-11-17,yes,Dhaka,manual_verified,2026-11-17\n",
        encoding="utf-8",
    )
    cat, is_sample = load_catalog(p)
    row = cat.iloc[0]
    assert not is_sample
    assert row["market"] == "Dhaka"
    assert row["source_type"] == "manual_verified"
    assert row["name_bn"]


def test_catalog_rejects_unknown_price_source(tmp_path):
    p = tmp_path / "prices.csv"
    p.write_text(
        "fct_code,price_bdt,unit_grams,store,price_date,in_stock,source_type\n"
        "02_0008,140,1000,Shop,2026-11-17,yes,random_blog\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Unsupported source_type"):
        load_catalog(p)


def test_bundled_demo_catalog_is_explicitly_illustrative():
    from backend.app.optimizer.catalog import SAMPLE

    cat, is_sample = load_catalog(SAMPLE)
    assert is_sample
    assert not cat.empty
    assert set(cat["source_type"]) == {"illustrative"}
    assert cat["market"].str.contains("not a real market").all()


def test_real_offer_replaces_illustrative_offer_for_same_food(tmp_path):
    p = tmp_path / "prices.csv"
    p.write_text(
        "fct_code,price_bdt,unit_grams,store,price_date,in_stock,market,source_type\n"
        "02_0008,80,1000,Demo,2026-10-20,yes,Demo,illustrative\n"
        "02_0008,140,1000,Local shop,2026-11-17,yes,Dhaka,manual_verified\n",
        encoding="utf-8",
    )
    cat, is_sample = load_catalog(p)
    assert not is_sample
    assert len(cat) == 1
    assert cat.iloc[0]["store"] == "Local shop"
    assert cat.iloc[0]["source_type"] == "manual_verified"


def test_market_selector_filters_catalog(tmp_path):
    from backend.app.optimizer.catalog import load_catalog, available_markets
    import pandas as pd
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    foods = pd.read_csv(root / "data" / "processed" / "foods.csv", dtype={"code": str})
    code = str(foods.iloc[0]["code"])
    rows = []
    for market, price in [("Area A", 50), ("Area B", 70)]:
        rows.append({"fct_code": code, "price_bdt": price, "unit_grams": 1000,
                     "store": "Test shop", "price_date": "2026-11-17", "in_stock": "yes",
                     "market": market, "source_type": "manual_verified"})
    path = tmp_path / "prices.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    assert available_markets(path) == ["Area A", "Area B"]
    a, _ = load_catalog(path, market="Area A")
    b, _ = load_catalog(path, market="Area B")
    assert set(a["market"]) == {"Area A"}
    assert set(b["market"]) == {"Area B"}
    assert float(a.iloc[0]["price_bdt"]) == 50
    assert float(b.iloc[0]["price_bdt"]) == 70
