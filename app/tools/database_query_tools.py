# app/tools/database_query_tools.py
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from bson import ObjectId
import json
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
import asyncio

from app.models.enums import UserRole, ResponseStatus

logger = logging.getLogger(__name__)

# === QUERY RESULT MODELS ===

class QueryFilter(BaseModel):
    """Structured filter for database queries"""
    person_name: Optional[str] = Field(None, description="Name of person to filter by")
    date_start: Optional[str] = Field(None, description="Start date in YYYY-MM-DD format")
    date_end: Optional[str] = Field(None, description="End date in YYYY-MM-DD format")
    form_type: Optional[str] = Field(None, description="Type or title of form to filter by")
    text_search: Optional[str] = Field(None, description="Text to search in responses")
    limit: int = Field(20, description="Maximum number of results to return")
    sort_by: str = Field("submitted_at", description="Field to sort by")
    sort_order: int = Field(-1, description="Sort order: -1 for descending, 1 for ascending")

class FormSummary(BaseModel):
    """Summary of a form response for reporting"""
    form_id: str
    form_title: str
    respondent_name: str
    submitted_at: str
    key_responses: Dict[str, Any]
    context_title: str

# === DATABASE QUERY BUILDER ===

class MongoQueryBuilder:
    """Builds MongoDB queries based on natural language filters"""
    
    def __init__(self, db):
        self.db = db
    
    async def build_form_search_query(self, filters: QueryFilter, user_id: str) -> Dict[str, Any]:
        """Build a MongoDB query for searching form responses"""
        query = {}
        
        # Security: Only forms user has access to
        context_filter = await self._get_user_context_filter(user_id)
        if context_filter:
            query.update(context_filter)
        
        # Person name filter
        if filters.person_name:
            person_regex = {"$regex": filters.person_name, "$options": "i"}
            query["$or"] = [
                {"respondent_name": person_regex},
                {"responses": {"$elemMatch": {"$regex": filters.person_name, "$options": "i"}}}
            ]
        
        # Date range filter
        if filters.date_start or filters.date_end:
            date_query = {}
            if filters.date_start:
                try:
                    start_date = datetime.fromisoformat(filters.date_start)
                    date_query["$gte"] = start_date
                except ValueError:
                    logger.warning(f"Invalid start date format: {filters.date_start}")
            
            if filters.date_end:
                try:
                    end_date = datetime.fromisoformat(filters.date_end)
                    end_date += timedelta(days=1) # Include the entire end date
                    date_query["$lt"] = end_date
                except ValueError:
                    logger.warning(f"Invalid end date format: {filters.date_end}")
            
            if date_query:
                query["submitted_at"] = date_query
        
        # Form type filter
        if filters.form_type:
            form_template_ids = await self._get_form_template_ids_by_title(filters.form_type)
            if form_template_ids:
                query["form_template_id"] = {"$in": form_template_ids}
        
        # Text search
        if filters.text_search:
            query["$text"] = {"$search": filters.text_search}
        
        # Only completed or reviewed forms are typically queried
        query["status"] = {"$in": [ResponseStatus.COMPLETE.value, "approved", "rejected"]}
        
        return query
    
    async def _get_user_context_filter(self, user_id: str) -> Optional[Dict[str, Any]]:
        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        
        if user and user.get("role") == UserRole.ADMIN.value:
            return None
        
        context_query = {
            "is_active": True,
            "$or": [
                {"assigned_professionals": user_id},
                {"assigned_users": user_id},
                {"created_by": user_id}
            ]
        }
        
        user_contexts = await self.db.contexts.find(context_query).to_list(length=None)
        context_ids = [str(ctx["_id"]) for ctx in user_contexts]
        
        if not context_ids:
            return {"context_id": {"$in": []}} # Return a query that finds nothing
        
        return {"context_id": {"$in": context_ids}}
    
    async def _get_form_template_ids_by_title(self, title_pattern: str) -> List[str]:
        title_regex = {"$regex": title_pattern, "$options": "i"}
        templates = await self.db.form_templates.find(
            {"title": title_regex},
            {"_id": 1}
        ).to_list(length=None)
        
        return [str(template["_id"]) for template in templates]

# === DATABASE TOOLS FOR LANGCHAIN ===

class FormSearchTool(BaseTool):
    """Tool for searching form responses"""
    # --- Corrected: Added explicit type annotations ---
    name: str = "search_forms"
    description: str = """Search for form responses based on filters.
    Input should be a JSON object with optional fields:
    - person_name: Name to search for
    - date_start: Start date (YYYY-MM-DD)
    - date_end: End date (YYYY-MM-DD) 
    - form_type: Form type/title to filter by
    - text_search: Text to search in responses
    - limit: Max results (default 20)
    """
    
    db: Any
    user_id: str
    query_builder: MongoQueryBuilder

    def __init__(self, db, user_id: str):
        # Initialize BaseTool (Pydantic) with declared fields so validation passes
        super().__init__(db=db, user_id=user_id, query_builder=MongoQueryBuilder(db))
    
    def _run(self, query: str) -> str:
        """Synchronous wrapper for the async execution."""
        return asyncio.run(self._arun(query))

    async def _arun(self, query: str) -> str:
        """Asynchronous execution of the form search."""
        try:
            query_data = json.loads(query)
            filters = QueryFilter(**query_data)
            
            mongo_query = await self.query_builder.build_form_search_query(filters, self.user_id)
            
            cursor = self.db.form_responses.find(mongo_query).sort(
                filters.sort_by, filters.sort_order
            ).limit(filters.limit)
            
            results = await cursor.to_list(length=None)
            
            enriched_results = []
            for result in results:
                template = await self.db.form_templates.find_one(
                    {"_id": ObjectId(result["form_template_id"])}
                )
                
                enriched_results.append({
                    "form_id": str(result["_id"]),
                    "form_title": template.get("title", "Unknown") if template else "Unknown",
                    "respondent_name": result.get("respondent_name", "Unknown"),
                    "submitted_at": result.get("submitted_at", "Unknown").isoformat(),
                    "responses": result.get("responses", {}),
                    "status": result.get("status", "unknown")
                })
            
            return json.dumps({
                "found_count": len(enriched_results),
                "forms": enriched_results
            })
            
        except Exception as e:
            logger.error(f"Form search failed: {e}", exc_info=True)
            return json.dumps({"error": str(e), "found_count": 0, "forms": []})

class FormAnalyticsTool(BaseTool):
    """Tool for analyzing form data"""
    # --- Corrected: Added explicit type annotations ---
    name: str = "analyze_forms"
    description: str = """Analyze form data to generate insights.
    Input should be a JSON object with:
    - form_ids: List of form IDs to analyze
    - analysis_type: Type of analysis (e.g., 'summary')
    """
    
    db: Any
    user_id: str

    def __init__(self, db, user_id: str):
        # Initialize BaseTool (Pydantic) with declared fields so validation passes
        super().__init__(db=db, user_id=user_id)
    
    def _run(self, query: str) -> str:
        return asyncio.run(self._arun(query))

    async def _arun(self, query: str) -> str:
        try:
            query_data = json.loads(query)
            form_ids = query_data.get("form_ids", [])
            analysis_type = query_data.get("analysis_type", "summary")
            
            if not form_ids:
                return json.dumps({"error": "No form IDs provided", "analysis": {}})
            
            object_ids = [ObjectId(fid) for fid in form_ids if ObjectId.is_valid(fid)]
            # Security check would be needed here to ensure user has access to these form_ids
            forms = await self.db.form_responses.find({"_id": {"$in": object_ids}}).to_list(length=None)
            
            if analysis_type == "summary":
                return self._generate_summary_analysis(forms)
            else:
                return json.dumps({"error": "Unknown analysis type", "analysis": {}})
                
        except Exception as e:
            logger.error(f"Form analysis failed: {e}", exc_info=True)
            return json.dumps({"error": str(e), "analysis": {}})
    
    def _generate_summary_analysis(self, forms: List[Dict[str, Any]]) -> str:
        if not forms:
            return json.dumps({"analysis": "No forms to analyze"})
        
        summary = {
            "total_forms": len(forms),
            "date_range": {
                "earliest": min(f.get("submitted_at", datetime.now()) for f in forms).isoformat(),
                "latest": max(f.get("submitted_at", datetime.now()) for f in forms).isoformat()
            },
            "respondents": list(set(f.get("respondent_name", "Unknown") for f in forms))
        }
        
        return json.dumps({"analysis": summary})


# === QUERY PROMPT TEMPLATES ===

class QueryPromptTemplates:
    """Templates for generating structured queries from natural language"""
    
    QUERY_ANALYSIS_PROMPT = """
    Analyze this user query for a form database search and extract structured filters.

    User query: "{user_query}"
    User ID: {user_id}
    Today is {today_date}
    Yesterday was {yesterday_date}

    Extract information for these filter categories:
    1. Person names (patients, users, respondents)
    2. Date/time references (convert relative dates to actual dates)
    3. Form types or categories mentioned
    4. Specific terms to search within form responses

    Return JSON matching this structure exactly:
    {{
        "person_name": "extracted name or null",
        "date_start": "YYYY-MM-DD or null", 
        "date_end": "YYYY-MM-DD or null",
        "form_type": "form type or null",
        "text_search": "search terms or null",
        "limit": 20,
        "sort_by": "submitted_at",
        "sort_order": -1
    }}

    Examples:
    - "How is patient John doing today?" -> {{"person_name": "John", "date_start": "{today_date}", "date_end": "{today_date}"}}
    - "Show me vehicle reports from yesterday" -> {{"form_type": "vehicle", "date_start": "{yesterday_date}", "date_end": "{yesterday_date}"}}
    - "Latest safety forms" -> {{"form_type": "safety", "limit": 10}}
    """
    
    REPORT_GENERATION_PROMPT = """
    Generate a comprehensive report based on the following form data.

    Original user query: "{user_query}"

    Form data found:
    {form_data}

    Create a professional report that:
    1. Directly answers the user's question.
    2. Summarizes key findings from the data.
    3. Identifies patterns or trends if multiple forms are present.
    4. Provides specific details when relevant.
    5. Notes any limitations or missing information.

    Structure the report with clear headings. Keep the tone professional but accessible.
    If no relevant data was found, explain what was searched for and why no results were returned.
    """

# === TOOL EXECUTOR FOR GRAPH NODES ===

class DatabaseToolExecutor:
    """Executes database operations for graph nodes"""
    
    def __init__(self, db, user_id: str):
        self.db = db
        self.user_id = user_id
        self.search_tool = FormSearchTool(db, user_id)
        self.analytics_tool = FormAnalyticsTool(db, user_id)
        self.query_builder = MongoQueryBuilder(db)
    
    async def execute_search(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a form search with the given filters"""
        try:
            query_json = json.dumps(filters)
            # Use the async run method of the tool
            result_json = await self.search_tool._arun(query_json)
            return json.loads(result_json)
        except Exception as e:
            logger.error(f"Search execution failed: {e}", exc_info=True)
            return {"error": str(e), "found_count": 0, "forms": []}
    
    async def execute_analysis(self, form_ids: List[str], analysis_type: str = "summary") -> Dict[str, Any]:
        """Execute form analysis"""
        try:
            query_data = {"form_ids": form_ids, "analysis_type": analysis_type}
            query_json = json.dumps(query_data)
            result_json = await self.analytics_tool._arun(query_json)
            return json.loads(result_json)
        except Exception as e:
            logger.error(f"Analysis execution failed: {e}", exc_info=True)
            return {"error": str(e), "analysis": {}}