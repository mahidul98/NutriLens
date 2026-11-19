from typing import Literal

from pydantic import BaseModel, Field

from .optimizer.models import PivotResult
from .personalization.models import (
    DailyTargets, MealCompleteness, MealReport, UserProfile,
)
from .schemas import MealItem, MealTotals


class DietConflict(BaseModel):
    fct_code: str
    name_en: str
    reason: str


class ReportRequest(BaseModel):
    items: list[MealItem] = Field(min_length=1, max_length=40)
    profile: UserProfile
    meal: Literal["breakfast", "lunch", "dinner", "snack"] = "lunch"
    out_of_stock: list[str] = []
    market: str | None = None


class ReportResponse(BaseModel):
    totals: MealTotals
    targets: DailyTargets
    report: MealReport
    diet_conflicts: list[DietConflict]
    pivot: PivotResult
    meal_completeness: MealCompleteness
