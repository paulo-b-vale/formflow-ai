# app/services/analytics_service.py
import logging
import asyncio
from typing import List, Dict, Any
from app.services.base_service import BaseService
from app.schemas.analytics import AnalyticsDashboardData, GeneralStat, CostAnalytics, TokenAnalytics, CostDataPoint, TokenDataPoint

logger = logging.getLogger(__name__)

class AnalyticsService(BaseService):
    
    async def get_dashboard_data(self) -> AnalyticsDashboardData:
        """Aggregates all necessary data for the analytics dashboard."""
        
        results = await asyncio.gather(
            self.db.users.count_documents({}),
            self.db.form_responses.count_documents({}),
            self._aggregate_session_costs(),
            self._aggregate_node_costs(),
            self._aggregate_user_costs(),
            self._get_active_users_today()
        )
        
        total_users, total_forms_filled, session_agg, node_agg, user_agg, active_users_today = results
        
        general_stats = GeneralStat(
            total_chats=0,  # TODO: Implement chat counting if needed
            total_forms_filled=total_forms_filled,
            total_users=total_users,
            active_users_today=active_users_today
        )
        
        cost_analytics = CostAnalytics(
            total_cost=session_agg.get('total_cost', 0.0),
            cost_by_model={},  # Placeholder - populate with actual model cost data if available
            daily_costs=[],    # Placeholder - populate with daily cost data if available
        )
        
        token_analytics = TokenAnalytics(
            total_tokens=session_agg.get('total_tokens', 0),
            tokens_by_model={},  # Placeholder - populate with actual model token data if available
            daily_tokens=[],     # Placeholder - populate with daily token data if available
        )

        return AnalyticsDashboardData(
            general_stats=general_stats,
            cost_analytics=cost_analytics,
            token_analytics=token_analytics,
            most_expensive_node=node_agg[0]['_id'] if node_agg else "N/A",
            most_active_user=user_agg[0]['_id'] if user_agg else "N/A"
        )
        
    async def _aggregate_session_costs(self) -> Dict[str, Any]:
        pipeline = [
            {'$group': {
                '_id': None,
                'total_sessions': {'$sum': 1},
                'total_cost': {'$sum': '$total_session_cost'},
                'total_tokens': {'$sum': '$total_session_tokens'},
                'avg_cost_per_session': {'$avg': '$total_session_cost'},
                'avg_tokens_per_session': {'$avg': '$total_session_tokens'}
            }}
        ]
        result = await self.db.session_costs.aggregate(pipeline).to_list(1)
        return result[0] if result else {}

    async def _aggregate_node_costs(self) -> List[Dict[str, Any]]:
        pipeline = [
            {'$group': {
                '_id': '$node_name',
                'total_cost': {'$sum': '$total_cost'},
                'total_tokens': {'$sum': '$total_tokens'},
            }},
            {'$sort': {'total_cost': -1}},
            {'$limit': 10}
        ]
        return await self.db.node_costs.aggregate(pipeline).to_list(None)

    async def _aggregate_user_costs(self) -> List[Dict[str, Any]]:
        pipeline = [
            {'$group': {
                '_id': '$user_id',
                'total_cost': {'$sum': '$total_session_cost'},
                'total_tokens': {'$sum': '$total_session_tokens'},
            }},
            {'$sort': {'total_cost': -1}},
            {'$limit': 10}
        ]
        return await self.db.session_costs.aggregate(pipeline).to_list(None)

    async def _get_active_users_today(self) -> int:
        """Get count of users who had activity today"""
        from datetime import datetime
        from datetime import timezone
        
        # Get today's date in UTC
        today = datetime.now(timezone.utc).date()
        
        # Calculate start and end of today in UTC
        start_of_day = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_of_day = datetime.combine(today, datetime.max.time()).replace(tzinfo=timezone.utc)
        
        # Query for activities today - we'll use form responses as a proxy for active users
        pipeline = [
            {
                "$match": {
                    "created_at": {
                        "$gte": start_of_day,
                        "$lt": end_of_day
                    }
                }
            },
            {
                "$group": {
                    "_id": "$respondent_id"
                }
            }
        ]
        
        # Count distinct users who submitted forms today
        try:
            result = await self.db.form_responses.aggregate(pipeline).to_list(None)
            return len(result)
        except Exception:
            # Fallback: return 0 if there's an error
            return 0

analytics_service = AnalyticsService()