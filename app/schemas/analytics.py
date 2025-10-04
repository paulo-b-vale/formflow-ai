from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from decimal import Decimal


class CostDataPoint(BaseModel):
    timestamp: datetime
    cost: Decimal
    model_name: Optional[str] = None


class TokenDataPoint(BaseModel):
    timestamp: datetime
    tokens_used: int
    model_name: Optional[str] = None


class GeneralStat(BaseModel):
    total_chats: int
    total_forms_filled: int
    total_users: int
    active_users_today: int


class CostAnalytics(BaseModel):
    total_cost: Decimal
    cost_by_model: dict
    daily_costs: List[CostDataPoint]


class TokenAnalytics(BaseModel):
    total_tokens: int
    tokens_by_model: dict
    daily_tokens: List[TokenDataPoint]


class AnalyticsDashboardData(BaseModel):
    general_stats: GeneralStat
    cost_analytics: CostAnalytics
    token_analytics: TokenAnalytics