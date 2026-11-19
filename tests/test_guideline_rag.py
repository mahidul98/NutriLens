from backend.app.rag.retrieve import retrieve, build_query

def test_sodium_query_retrieves_salt_guidance():
    hits = retrieve("salt sodium condiments", top_k=3)
    assert hits and hits[0]["id"] == "BD2025-SALT-20"

def test_fiber_gap_retrieves_food_diversity_guidance():
    q = build_query(["fiber_g"], [], "lunch")
    hits = retrieve(q, top_k=3)
    assert hits
    assert any("vegetables" in h["text"].lower() or "whole-grain" in h["text"].lower() for h in hits)


def test_annex8_protein_reference_is_retrievable():
    hits = retrieve("Bangladesh Annex 8 protein requirements adults", top_k=3)
    assert any(h["id"] == "BD2025-ANNEX8-PROTEIN-FAT-FIBRE" for h in hits)


def test_annex8_iron_bioavailability_is_retrievable():
    hits = retrieve("Annex 8 iron dietary bioavailability 10 percent", top_k=3)
    assert any(h["id"] == "BD2025-ANNEX8-IRON" for h in hits)
