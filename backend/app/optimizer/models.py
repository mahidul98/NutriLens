from typing import Literal

from pydantic import BaseModel, Field


class ShoppingItem(BaseModel):
    fct_code: str
    name_en: str
    name_bn: str = ""
    store: str = ""
    market: str = "Unspecified market"
    source_type: str = "manual_unverified"
    price_date: str = ""
    last_updated: str = ""
    unit_grams: float = 0.0
    price_bdt: float = 0.0
    eat_grams: float
    buy_grams: float
    cost_bdt: float
    helps: list[str] = Field(default_factory=list)


class PivotResult(BaseModel):
    status: Literal["ok", "nothing_needed", "no_catalog", "no_solution"]
    items: list[ShoppingItem] = Field(default_factory=list)
    total_cost_bdt: float = 0.0
    before: dict[str, float] = Field(default_factory=dict)
    after: dict[str, float] = Field(default_factory=dict)
    remaining_gaps: list[str] = Field(default_factory=list)
    catalog_is_sample: bool = False
    notes: list[str] = Field(default_factory=list)
