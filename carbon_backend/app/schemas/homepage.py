from pydantic import BaseModel


class HomePageSummary(BaseModel):
    user_id: int
    balance_credits: int
    credits_this_week: int
    co2_saved_kg: float
    distance_km: float
