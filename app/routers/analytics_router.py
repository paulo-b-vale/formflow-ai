# app/routers/analytics_router.py
from fastapi import APIRouter, Depends
from app.services.analytics_service import analytics_service
from app.dependencies.auth import require_admin
from app.schemas.analytics import AnalyticsDashboardData

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
    dependencies=[Depends(require_admin)]
)

@router.get("/dashboard", response_model=AnalyticsDashboardData)
async def get_dashboard_analytics():
    """
    Provides aggregated data for the admin analytics dashboard.
    """
    return await analytics_service.get_dashboard_data()