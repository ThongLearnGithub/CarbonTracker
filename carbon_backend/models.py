from enum import Enum
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class Role(str, Enum):
    user = "user"
    admin = "admin"
    merchant = "merchant"


class UserBase(BaseModel):
    id: int
    email: str
    full_name: str
    role: Role


class UserInDB(UserBase):
    password: str


class UserSignup(BaseModel):
    email: str
    full_name: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class FirebaseLoginRequest(BaseModel):
    id_token: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserBase


class Voucher(BaseModel):
    id: int
    title: str
    description: str
    credits: int
    status: str          
    category: Optional[str] = None
    rating: float
    availability: str    
    redeemed_at: Optional[str] = None   
    redeemed_by_user_id: Optional[int] = None

class RedeemRequest(BaseModel):
    user_id: int



class Trip(BaseModel):
    id: int
    user_id: int
    date: str            
    distance_km: float
    transport_modes: List[str]
    credits: int
    credits_earned: Optional[int] = None
    co2_emitted_kg: Optional[float] = None
    co2_saved_kg: Optional[float] = None


class SeriesPoint(BaseModel):
    label: str      
    credits: int
    trips: int


class TripStats(BaseModel):
    user_id: int
    total_trips: int          
    total_credits: int
    total_distance_km: float
    total_co2_kg: float
    daily: List[SeriesPoint]   
    weekly: List[SeriesPoint]  
    monthly: List[SeriesPoint] 


class GpsRoutePoint(BaseModel):
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    accuracy: float = Field(ge=0, allow_inf_nan=False)
    timestamp: datetime
    is_mocked: bool = False


class HomePageSummary(BaseModel):
    user_id: int
    balance_credits: int
    credits_this_week: int
    co2_saved_kg: float
    distance_km: float
    


class WalletHistoryItem(BaseModel):
    kind: str      
    date: str      
    title: str     
    amount: int    


class WalletSummary(BaseModel):
    user_id: int
    balance_credits: int
    credits_this_week: int
    credits_this_month: int
    history: List[WalletHistoryItem]



class TripCreate(BaseModel):
    user_id: int
    date: str
    distance_km: Optional[float] = Field(
        default=None,
        ge=0,
        allow_inf_nan=False,
    )
    transport_modes: List[str] = Field(min_length=1)
    credits: Optional[int] = None
    gps_points: Optional[List[GpsRoutePoint]] = None
