"""Lightweight lexical retrieval over curated Bangladesh guideline passages. No network required."""
from __future__ import annotations
import json, math, re
from pathlib import Path
from collections import Counter

DATA = Path(__file__).with_name("guideline_chunks.json")

def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+|[\u0980-\u09ff]+", (text or "").lower())

def load_chunks():
    return json.loads(DATA.read_text(encoding="utf-8"))

def retrieve(query: str, top_k: int = 3) -> list[dict]:
    """Return ranked source passages using a simple BM25-style lexical score."""
    q = Counter(_tokens(query))
    if not q: return []
    docs = load_chunks(); scored=[]
    for doc in docs:
        terms = Counter(_tokens(doc.get("topic", "") + " " + doc.get("text", "")))
        score = 0.0
        for term, qf in q.items():
            tf = terms.get(term, 0)
            if tf:
                score += qf * (tf * 2.2 / (tf + 1.2))
        if score > 0: scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [dict(item, score=round(score, 3)) for score, item in scored[:top_k]]

def build_query(gaps=None, excesses=None, meal="") -> str:
    keys = list(gaps or []) + list(excesses or [])
    aliases = {
      "fiber_g":"vegetables fruits whole grains pulses dietary diversity",
      "protein_g":"Annex 8 protein requirement pulses fish meat eggs milk food groups",
      "fat_g":"Annex 8 total fat energy percentage fat oils fried foods cooking methods",
      "sodium_mg":"salt sodium condiments iodized salt",
      "carb_g":"carbohydrate cereals rice whole grains sugar",
      "energy_kcal":"balanced diet food groups portion",
      "vitamin_a_rae_mcg":"Annex 8 vitamin A requirements vegetables fruits dietary diversity",
      "vitamin_c_mg":"Annex 8 vitamin C requirements fruits vegetables dietary diversity",
      "calcium_mg":"Annex 8 calcium requirement milk milk products food groups",
      "iron_mg":"pulses fish meat eggs dietary diversity",
      "folate_mcg":"Annex 8 vitamins folate dietary folate equivalents",
      "iron_mg":"Annex 8 iron dietary bioavailability recommended nutrient intake",
      "calcium_mg":"Annex 8 calcium macromineral requirements",
      "fiber_g":"Annex 8 fibre protein fat age sex requirements dietary fibre vegetables fruits whole-grain pulses vegetables fruits whole-grain pulses",
    }
    return " ".join([meal, " ".join(aliases.get(k, k.replace("_", " ")) for k in keys)])
