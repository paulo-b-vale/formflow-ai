# app/agents/form_searcher_node.py
import logging
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from app.utils.observability import ObservabilityMixin
from app.utils.langchain_utils import get_gemini_llm
from app.config.settings import settings
from app.agents.state import FormState
from app.utils.confidence_system import ConfidenceManager, ConfidenceResult
import json

logger = logging.getLogger(__name__)

def _state_get(state, key, default=None):
    """Safely get a value from LangGraph state"""
    if isinstance(state, dict):
        return state.get(key, default)
    getter = getattr(state, "get", None)
    if callable(getter):
        try:
            return getter(key, default)
        except TypeError:
            pass
    return getattr(state, key, default)


class FormSearcherNode(ObservabilityMixin):
    """Enhanced form search and query handler with interactive features"""
    
    def __init__(self, base_url: str = None):
        self.llm = get_gemini_llm()
        self.confidence_manager = ConfidenceManager()
        self.base_url = base_url or getattr(settings, 'API_BASE_URL', 'http://localhost:8000')
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
    async def run(self, state: FormState):
        """Main entry point for form searching"""
        user_message = _state_get(state, "user_message")
        user_id = _state_get(state, "user_id")
        session_id = _state_get(state, "session_id")
        
        self.log_info(f"FormSearcherNode processing: {user_message}")
        
        try:
            # Parse the search intent and extract parameters
            search_params = await self._parse_search_intent(user_message, user_id)
            
            if search_params.get("needs_clarification"):
                return await self._handle_search_clarification(search_params, user_message)
            
            # Execute the search using API endpoints
            search_results = await self._execute_search(search_params, user_id)
            
            # Format and present results interactively
            response_message = await self._format_search_results(
                search_results, search_params, user_message
            )
            
            return {
                "final_response": response_message,
                "is_complete": False,  # Allow for follow-up questions
                "search_results": search_results,
                "search_params": search_params
            }
            
        except Exception as e:
            self.log_error(f"Error in FormSearcherNode: {e}")
            return {
                "final_response": f"I encountered an error while searching for forms: {str(e)}. Please try rephrasing your request.",
                "is_complete": False
            }
    
    async def _parse_search_intent(self, user_message: str, user_id: str) -> Dict[str, Any]:
        """Parse user message to extract search parameters using LLM"""
        
        prompt = f"""You are an expert at parsing form search requests. Extract search parameters from the user's message.

User message: "{user_message}"

Extract the following information and respond in JSON format:
{{
    "search_type": "recent|by_date|by_person|by_form_type|by_keyword|general",
    "date_range": {{
        "start_date": "YYYY-MM-DD or null",
        "end_date": "YYYY-MM-DD or null",
        "relative": "today|yesterday|this_week|last_week|this_month|last_month or null"
    }},
    "person_name": "extracted name or null",
    "form_type": "extracted form type/category or null",
    "keywords": ["list", "of", "keywords"],
    "limit": "number of results requested or 10",
    "confidence_score": 0.0-1.0,
    "confidence_reasoning": "explanation of how confident you are in this parsing"
}}

Examples:
- "show me yesterday's reports" → search_type: "recent", relative: "yesterday", confidence_score: 0.9
- "find John's safety forms" → search_type: "by_person", person_name: "John", form_type: "safety", confidence_score: 0.85
- "forms submitted this week" → search_type: "by_date", relative: "this_week", confidence_score: 0.9
"""

        try:
            response = await self.llm.ainvoke(prompt)
            search_params = json.loads(response.content.strip())
            
            # Add current date context for relative dates
            if search_params.get("date_range", {}).get("relative"):
                search_params["date_range"] = self._resolve_relative_dates(
                    search_params["date_range"]["relative"]
                )
            
            # Use ConfidenceManager to evaluate the parsing result
            context = {
                "alternatives": [],  # No alternatives for parsing, but include for consistency
                "reasoning": search_params.get("confidence_reasoning", "")
            }
            confidence_result: ConfidenceResult = self.confidence_manager.evaluate_confidence(
                search_params.get("confidence_score", 0.0), context
            )
            
            # Add confidence system results to the search params
            search_params["confidence_level"] = confidence_result.level.value
            if confidence_result.requires_clarification and confidence_result.clarification_message:
                search_params["needs_clarification"] = True
                search_params["clarification_message"] = confidence_result.clarification_message
            else:
                search_params["needs_clarification"] = False
                search_params["clarification_message"] = None
            
            return search_params
            
        except (json.JSONDecodeError, Exception) as e:
            self.log_error(f"Error parsing search intent: {e}")
            # Return a low-confidence result that requires clarification
            context = {
                "alternatives": [],
                "reasoning": f"Error parsing search intent: {str(e)}"
            }
            confidence_result: ConfidenceResult = self.confidence_manager.evaluate_confidence(0.0, context)
            
            return {
                "search_type": "general",
                "needs_clarification": True,
                "clarification_message": confidence_result.clarification_message,
                "confidence_score": 0.0,
                "confidence_level": confidence_result.level.value
            }
    
    def _resolve_relative_dates(self, relative_period: str) -> Dict[str, str]:
        """Convert relative date periods to actual dates"""
        today = datetime.now().date()
        
        date_mappings = {
            "today": {
                "start_date": today.isoformat(),
                "end_date": today.isoformat()
            },
            "yesterday": {
                "start_date": (today - timedelta(days=1)).isoformat(),
                "end_date": (today - timedelta(days=1)).isoformat()
            },
            "this_week": {
                "start_date": (today - timedelta(days=today.weekday())).isoformat(),
                "end_date": today.isoformat()
            },
            "last_week": {
                "start_date": (today - timedelta(days=today.weekday() + 7)).isoformat(),
                "end_date": (today - timedelta(days=today.weekday() + 1)).isoformat()
            },
            "this_month": {
                "start_date": today.replace(day=1).isoformat(),
                "end_date": today.isoformat()
            }
        }
        
        return date_mappings.get(relative_period, {"start_date": None, "end_date": None})
    
    async def _handle_search_clarification(self, search_params: Dict[str, Any], original_message: str) -> Dict[str, Any]:
        """Handle cases where search intent needs clarification using ConfidenceManager"""
        
        # If we have a clarification message from the confidence system, use it
        if search_params.get("clarification_message"):
            clarification_message = search_params["clarification_message"]
        else:
            # Fallback to our own message
            reason = search_params.get("clarification_reason", "I couldn't understand your search request clearly")
            
            clarification_message = f"""I want to help you search for forms, but I need a bit more information about "{original_message}".

{reason}

I can help you search for forms in these ways:

📅 **By Date**: "show me forms from last week", "yesterday's submissions"
👤 **By Person**: "find John's forms", "forms submitted by Sarah"  
📋 **By Form Type**: "safety reports", "incident forms", "daily checklists"
🔍 **By Keywords**: "equipment", "maintenance", "urgent"
📊 **Recent Activity**: "latest forms", "recent submissions"

Could you be more specific about what you're looking for? For example:
- What type of forms?
- From what time period?
- From specific people?
- Any particular keywords?"""

        return {
            "final_response": clarification_message,
            "is_complete": False,
            "search_params": search_params
        }
    
    async def _execute_search(self, search_params: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Execute the search using API endpoints"""
        
        # Build query parameters
        query_params = {
            "user_id": user_id,
            "limit": search_params.get("limit", 10)
        }
        
        # Add date filters
        date_range = search_params.get("date_range", {})
        if date_range.get("start_date"):
            query_params["start_date"] = date_range["start_date"]
        if date_range.get("end_date"):
            query_params["end_date"] = date_range["end_date"]
        
        # Add other filters
        if search_params.get("person_name"):
            query_params["submitted_by"] = search_params["person_name"]
        if search_params.get("form_type"):
            query_params["form_type"] = search_params["form_type"]
        if search_params.get("keywords"):
            query_params["keywords"] = ",".join(search_params["keywords"])
        
        try:
            # Call the search API endpoint
            async with self.http_client as client:
                response = await client.get(
                    f"{self.base_url}/api/forms/search",
                    params=query_params,
                    headers={"Authorization": f"Bearer {await self._get_auth_token(user_id)}"}
                )
                response.raise_for_status()
                
                search_results = response.json()
                
                # Also get form templates for better context
                templates_response = await client.get(
                    f"{self.base_url}/api/forms/templates",
                    headers={"Authorization": f"Bearer {await self._get_auth_token(user_id)}"}
                )
                
                templates = templates_response.json() if templates_response.status_code == 200 else []
                
                return {
                    "forms": search_results.get("forms", []),
                    "total_count": search_results.get("total_count", 0),
                    "templates": templates,
                    "query_params": query_params
                }
                
        except httpx.HTTPError as e:
            self.log_error(f"HTTP error in form search: {e}")
            # Fallback to mock results for development
            return await self._get_mock_search_results(search_params)
    
    async def _get_mock_search_results(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """Mock search results for development/testing"""
        mock_forms = [
            {
                "id": "form_1",
                "template_id": "safety_report",
                "template_name": "Safety Incident Report",
                "submitted_by": "John Doe",
                "submitted_at": "2025-09-26T14:30:00Z",
                "status": "completed",
                "responses": {"incident_type": "Equipment", "severity": "Medium"}
            },
            {
                "id": "form_2", 
                "template_id": "daily_checklist",
                "template_name": "Daily Equipment Checklist",
                "submitted_by": "Jane Smith",
                "submitted_at": "2025-09-26T09:15:00Z",
                "status": "completed",
                "responses": {"equipment_status": "Good", "issues": "None"}
            }
        ]
        
        return {
            "forms": mock_forms[:search_params.get("limit", 10)],
            "total_count": len(mock_forms),
            "templates": [],
            "query_params": search_params
        }
    
    async def _format_search_results(self, results: Dict[str, Any], search_params: Dict[str, Any], original_query: str) -> str:
        """Format search results into an interactive response"""
        
        forms = results.get("forms", [])
        total_count = results.get("total_count", 0)
        
        if total_count == 0:
            return f"""I couldn't find any forms matching your search: "{original_query}"

This might be because:
• No forms have been submitted matching your criteria
• The forms might be in a different date range
• The person's name might be spelled differently
• The form type might have a different name

Would you like to try a different search? I can help you:
🔍 Search by different keywords
📅 Try a different date range  
👥 Search for forms by other people
📋 Browse all available form types"""

        # Format results
        response = f"Found **{total_count}** form{'s' if total_count != 1 else ''} matching your search: \"{original_query}\"\n\n"
        
        for i, form in enumerate(forms[:5], 1):  # Show first 5 results
            submitted_date = self._format_date(form.get("submitted_at", ""))
            status_emoji = "✅" if form.get("status") == "completed" else "⏳"
            
            response += f"**{i}. {form.get('template_name', 'Unknown Form')}** {status_emoji}\n"
            response += f"   👤 Submitted by: {form.get('submitted_by', 'Unknown')}\n"
            response += f"   📅 Date: {submitted_date}\n"
            response += f"   🔗 ID: `{form.get('id', 'N/A')}`\n\n"
        
        if total_count > 5:
            response += f"... and {total_count - 5} more forms.\n\n"
        
        # Add interactive options
        response += "**What would you like to do next?**\n"
        response += "📖 View details of a specific form (tell me the number)\n"
        response += "📊 Generate a report from these forms\n"
        response += "🔍 Refine your search with different criteria\n"
        response += "📋 Search for different forms\n"
        
        return response
    
    def _format_date(self, date_string: str) -> str:
        """Format date string for display"""
        try:
            if date_string:
                dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
                return dt.strftime("%Y-%m-%d %H:%M")
            return "Unknown date"
        except Exception:
            return "Unknown date"
    
    async def _get_auth_token(self, user_id: str) -> str:
        """Get authentication token for API calls"""
        # This should integrate with your auth system
        return "mock_token_for_development"