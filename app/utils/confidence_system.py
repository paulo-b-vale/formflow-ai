# app/utils/confidence_system.py
"""
Confidence handling system for form prediction and user interactions
"""
from typing import Dict, Any, List, Tuple, Optional
from enum import Enum
import logging
from dataclasses import dataclass
from app.utils.observability import ObservabilityMixin

logger = logging.getLogger(__name__)

class ConfidenceLevel(Enum):
    """Confidence level categories"""
    HIGH = "high"        # > 0.8
    MEDIUM = "medium"    # 0.5 - 0.8  
    LOW = "low"         # < 0.5

@dataclass
class ConfidenceResult:
    """Structured confidence result"""
    score: float
    level: ConfidenceLevel
    reasoning: str
    alternatives: List[Dict[str, Any]]
    requires_clarification: bool
    clarification_message: Optional[str] = None

class ConfidenceManager(ObservabilityMixin):
    """Manages confidence scoring and clarification logic"""
    
    def __init__(self):
        self.high_threshold = 0.8
        self.medium_threshold = 0.5
    
    def evaluate_confidence(self, score: float, context: Dict[str, Any]) -> ConfidenceResult:
        """Evaluate confidence score and determine if clarification is needed"""
        
        level = self._get_confidence_level(score)
        requires_clarification = score < self.high_threshold
        
        alternatives = context.get('alternatives', [])
        reasoning = context.get('reasoning', '')
        
        clarification_message = None
        if requires_clarification:
            clarification_message = self._generate_clarification_message(
                score, level, alternatives, reasoning
            )
        
        return ConfidenceResult(
            score=score,
            level=level,
            reasoning=reasoning,
            alternatives=alternatives,
            requires_clarification=requires_clarification,
            clarification_message=clarification_message
        )
    
    def _get_confidence_level(self, score: float) -> ConfidenceLevel:
        """Convert numeric score to confidence level"""
        if score >= self.high_threshold:
            return ConfidenceLevel.HIGH
        elif score >= self.medium_threshold:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
    
    def _generate_clarification_message(self, score: float, level: ConfidenceLevel, 
                                       alternatives: List[Dict], reasoning: str) -> str:
        """Generate appropriate clarification message based on confidence"""
        
        if level == ConfidenceLevel.MEDIUM and alternatives:
            return f"""I'm {score:.1%} confident about what you need, but I want to make sure I help you correctly.

{reasoning}

Here are the options I'm considering:
""" + "\n".join([f"• {alt.get('name', alt.get('id', 'Unknown'))}: {alt.get('description', '')}" for alt in alternatives[:3]])

        elif level == ConfidenceLevel.LOW:
            return f"""I'm only {score:.1%} confident about understanding your request.

{reasoning}

Could you please provide more specific details about what you're looking for?"""
        
        else:
            return f"I need clarification to better assist you. {reasoning}"


# app/api/endpoints/forms_api.py (Suggested API endpoints)
"""
Suggested API endpoints to support the enhanced form system
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/forms", tags=["forms"])

# Request/Response Models
class FormSearchRequest(BaseModel):
    user_id: str
    keywords: Optional[List[str]] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    submitted_by: Optional[str] = None
    form_type: Optional[str] = None
    status: Optional[str] = None
    limit: int = 10
    offset: int = 0

class FormSearchResponse(BaseModel):
    forms: List[Dict[str, Any]]
    total_count: int
    page_info: Dict[str, Any]

class AnalyticsRequest(BaseModel):
    user_id: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    form_types: Optional[List[str]] = None
    metrics: List[str] = ["completion_rate", "response_time", "user_activity"]

class AnalyticsResponse(BaseModel):
    total_submissions: int
    completion_rate: float
    average_completion_time: int
    form_type_distribution: Dict[str, int]
    user_activity: Dict[str, Any]
    trends: Dict[str, Any]

# API Endpoints
@router.get("/search", response_model=FormSearchResponse)
async def search_forms(
    user_id: str = Query(...),
    keywords: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    submitted_by: Optional[str] = Query(None),
    form_type: Optional[str] = Query(None),
    limit: int = Query(10, le=100),
    offset: int = Query(0, ge=0)
):
    """Search for form submissions with various filters"""
    try:
        # Parse keywords
        keyword_list = keywords.split(",") if keywords else []
        
        # Create search request
        search_request = FormSearchRequest(
            user_id=user_id,
            keywords=keyword_list,
            start_date=start_date,
            end_date=end_date,
            submitted_by=submitted_by,
            form_type=form_type,
            limit=limit,
            offset=offset
        )
        
        # Execute search (replace with your actual search logic)
        results = await execute_form_search(search_request)
        
        return FormSearchResponse(
            forms=results["forms"],
            total_count=results["total_count"],
            page_info={
                "limit": limit,
                "offset": offset,
                "has_more": results["total_count"] > offset + limit
            }
        )
        
    except Exception as e:
        logger.error(f"Error in form search: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/submissions")
async def get_form_submissions(
    user_id: str = Query(...),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    form_types: Optional[str] = Query(None)
):
    """Get form submissions for reporting"""
    try:
        form_type_list = form_types.split(",") if form_types else []
        
        # Execute query (replace with your actual logic)
        submissions = await get_submissions_data(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            form_types=form_type_list
        )
        
        return submissions
        
    except Exception as e:
        logger.error(f"Error getting submissions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/analytics", response_model=AnalyticsResponse) 
async def get_form_analytics(
    user_id: str = Query(...),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    form_types: Optional[str] = Query(None)
):
    """Get form analytics and metrics"""
    try:
        form_type_list = form_types.split(",") if form_types else []
        
        # Calculate analytics (replace with your actual logic)
        analytics = await calculate_form_analytics(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            form_types=form_type_list
        )
        
        return AnalyticsResponse(**analytics)
        
    except Exception as e:
        logger.error(f"Error calculating analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/templates")
async def get_form_templates(user_id: str = Query(...)):
    """Get available form templates"""
    try:
        templates = await get_available_templates(user_id)
        return templates
        
    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Implementation functions (replace with your actual database logic)
async def execute_form_search(request: FormSearchRequest) -> Dict[str, Any]:
    """Execute form search against database"""
    # Mock implementation - replace with your actual MongoDB queries
    mock_forms = [
        {
            "id": "form_1",
            "template_id": "safety_report",
            "template_name": "Safety Incident Report",
            "submitted_by": "John Doe",
            "submitted_at": "2025-09-26T14:30:00Z",
            "status": "completed",
            "responses": {"incident_type": "Equipment", "severity": "Medium"}
        }
    ]
    
    return {
        "forms": mock_forms,
        "total_count": len(mock_forms)
    }

async def get_submissions_data(user_id: str, start_date: Optional[date], 
                              end_date: Optional[date], form_types: List[str]) -> List[Dict]:
    """Get form submissions data"""
    # Mock implementation
    return [
        {
            "id": "form_1",
            "template_id": "safety_report", 
            "submitted_by": "John Doe",
            "submitted_at": "2025-09-26T14:30:00Z",
            "completion_time_seconds": 420,
            "status": "completed"
        }
    ]

async def calculate_form_analytics(user_id: str, start_date: Optional[date],
                                  end_date: Optional[date], form_types: List[str]) -> Dict[str, Any]:
    """Calculate form analytics"""
    # Mock implementation
    return {
        "total_submissions": 15,
        "completion_rate": 0.87,
        "average_completion_time": 300,
        "form_type_distribution": {"safety_report": 8, "daily_checklist": 7},
        "user_activity": {"John Doe": 5, "Jane Smith": 4},
        "trends": {"weekly_growth": 0.15}
    }

async def get_available_templates(user_id: str) -> List[Dict]:
    """Get available form templates"""
    # Mock implementation
    return [
        {"id": "safety_report", "name": "Safety Incident Report", "field_count": 12},
        {"id": "daily_checklist", "name": "Daily Equipment Checklist", "field_count": 8}
    ]


# app/agents/interactive_handler.py
"""
Interactive conversation handler for follow-up questions
"""

class InteractiveConversationHandler(ObservabilityMixin):
    """Handles interactive conversations and follow-up questions"""
    
    def __init__(self, llm):
        self.llm = llm
    
    async def should_continue_conversation(self, state: Dict[str, Any]) -> bool:
        """Determine if conversation should continue based on context"""
        
        is_complete = state.get("is_complete", True)
        user_message = state.get("user_message", "")
        final_response = state.get("final_response", "")
        
        # Check if response suggests interactivity
        interactive_indicators = [
            "What would you like",
            "choose from",
            "tell me the number",
            "would you like to do next",
            "ask questions about"
        ]
        
        has_interactive_content = any(indicator in final_response for indicator in interactive_indicators)
        
        return not is_complete or has_interactive_content
    
    async def parse_follow_up_intent(self, user_message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Parse follow-up messages in context of previous interaction"""
        
        previous_node = context.get("last_node", "")
        previous_results = context.get("search_results", {})
        
        prompt = f"""Parse this follow-up message in context of a previous {previous_node} interaction.

Previous context: {json.dumps(context, indent=2)[:500]}...
User's follow-up: "{user_message}"

Determine the user's intent:
- "view_details" - wants to see details of specific item (number, ID, etc.)
- "refine_search" - wants to modify search criteria  
- "generate_report" - wants to create report from previous results
- "new_request" - completely new request
- "clarification" - asking for clarification

Return JSON with:
{{
    "intent": "intent_type",
    "confidence": 0.0-1.0,
    "extracted_data": {{}},  // Any specific data extracted (IDs, numbers, etc.)
    "reasoning": "explanation"
}}"""

        try:
            response = await self.llm.ainvoke(prompt)
            return json.loads(response.content.strip())
        except Exception as e:
            return {
                "intent": "clarification",
                "confidence": 0.0,
                "extracted_data": {},
                "reasoning": f"Error parsing follow-up: {str(e)}"
            }


# app/agents/form_confidence_predictor.py
"""
Enhanced form prediction with confidence scoring and user interaction
"""
import json
from typing import Dict, Any, List, Optional, Tuple
from app.utils.observability import ObservabilityMixin
from app.utils.langchain_utils import get_gemini_llm
from app.utils.confidence_system import ConfidenceManager, ConfidenceResult
import logging

logger = logging.getLogger(__name__)

class FormConfidencePredictor(ObservabilityMixin):
    """Enhanced form predictor with confidence handling and user interaction"""
    
    def __init__(self, db):
        self.db = db
        self.llm = get_gemini_llm()
        self.confidence_manager = ConfidenceManager()
        
    async def predict_form_with_confidence(self, user_message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Predict form with confidence scoring and clarification handling"""
        
        try:
            # Get available forms
            available_forms = await self._get_available_forms(user_context.get("user_id"))
            
            if not available_forms:
                return {
                    "error_message": "No forms are currently available. Please contact your administrator.",
                    "confidence_score": 0.0
                }
            
            # Predict with confidence
            prediction_result = await self._predict_with_llm(user_message, available_forms)
            
            # Evaluate confidence
            confidence_result = self.confidence_manager.evaluate_confidence(
                prediction_result["confidence"],
                {
                    "alternatives": prediction_result.get("alternatives", []),
                    "reasoning": prediction_result.get("reasoning", "")
                }
            )
            
            # Handle based on confidence level
            if confidence_result.requires_clarification:
                return await self._handle_low_confidence_prediction(
                    prediction_result, confidence_result, available_forms
                )
            else:
                return await self._handle_high_confidence_prediction(
                    prediction_result, confidence_result
                )
                
        except Exception as e:
            self.log_error(f"Error in form prediction: {e}")
            return {
                "error_message": f"I encountered an error while trying to identify the form: {str(e)}",
                "confidence_score": 0.0
            }
    
    async def _predict_with_llm(self, user_message: str, available_forms: List[Dict]) -> Dict[str, Any]:
        """Use LLM to predict form with confidence scoring"""
        
        forms_context = "\n".join([
            f"- {form['id']}: {form['title']} ({form.get('context_title', 'General')})\n"
            f"  Description: {form.get('description', 'No description')}\n"
            f"  Fields: {', '.join(form.get('field_names', [])[:5])}{'...' if len(form.get('field_names', [])) > 5 else ''}"
            for form in available_forms
        ])
        
        prompt = f"""You are an expert at matching user requests to the most appropriate form.

User request: "{user_message}"

Available forms:
{forms_context}

Analyze the user's request and match it to the most appropriate form. Consider:
1. Keywords in the user's message that match form titles, descriptions, or field names
2. Context and intent behind the request
3. Domain-specific terminology

Provide your analysis in JSON format:
{{
    "predicted_form_id": "best_matching_form_id or null",
    "confidence": 0.0-1.0,
    "reasoning": "Detailed explanation of why this form was chosen",
    "matched_keywords": ["list", "of", "matched", "keywords"],
    "alternatives": [
        {{
            "form_id": "alternative_form_id",
            "name": "form_name", 
            "confidence": 0.0-1.0,
            "reason": "why this could also be a match"
        }}
    ]
}}

Guidelines for confidence scoring:
- 0.9-1.0: Very clear match with multiple keyword matches
- 0.7-0.8: Good match with some keyword matches  
- 0.5-0.6: Possible match but ambiguous
- 0.0-0.4: Poor match or very unclear
"""

        try:
            response = await self.llm.ainvoke(prompt)
            result = json.loads(response.content.strip())
            
            # Ensure confidence is within bounds
            result["confidence"] = max(0.0, min(1.0, result.get("confidence", 0.0)))
            
            # Ensure alternatives have valid confidence scores
            for alt in result.get("alternatives", []):
                alt["confidence"] = max(0.0, min(1.0, alt.get("confidence", 0.0)))
            
            return result
            
        except Exception as e:
            self.log_error(f"Error in LLM prediction: {e}")
            return {
                "predicted_form_id": None,
                "confidence": 0.0,
                "reasoning": f"Error in prediction: {str(e)}",
                "matched_keywords": [],
                "alternatives": []
            }
    
    async def _handle_high_confidence_prediction(self, prediction: Dict, confidence_result: ConfidenceResult) -> Dict[str, Any]:
        """Handle high confidence predictions"""
        
        form_id = prediction["predicted_form_id"]
        
        if not form_id:
            return {
                "error_message": "I couldn't identify which form you need. Could you be more specific?",
                "confidence_score": confidence_result.score
            }
        
        # Get form details
        form_details = await self._get_form_details(form_id)
        
        return {
            "form_template_id": form_id,
            "confidence_score": confidence_result.score,
            "reasoning": prediction["reasoning"],
            "form_details": form_details,
            "matched_keywords": prediction.get("matched_keywords", [])
        }
    
    async def _handle_low_confidence_prediction(self, prediction: Dict, confidence_result: ConfidenceResult, 
                                               available_forms: List[Dict]) -> Dict[str, Any]:
        """Handle low confidence predictions with user clarification"""
        
        alternatives = prediction.get("alternatives", [])
        
        # Generate interactive clarification message
        clarification_msg = await self._generate_form_clarification_message(
            prediction, confidence_result, alternatives, available_forms
        )
        
        return {
            "requires_clarification": True,
            "clarification_message": clarification_msg,
            "confidence_score": confidence_result.score,
            "reasoning": prediction["reasoning"],
            "alternatives": alternatives,
            "predicted_form": prediction.get("predicted_form_id")
        }
    
    async def _generate_form_clarification_message(self, prediction: Dict, confidence_result: ConfidenceResult,
                                                  alternatives: List[Dict], available_forms: List[Dict]) -> str:
        """Generate interactive clarification message for form selection"""
        
        user_friendly_alternatives = []
        
        # Get top alternatives with details
        for alt in alternatives[:3]:  # Show top 3 alternatives
            form_details = next((f for f in available_forms if f["id"] == alt["form_id"]), {})
            user_friendly_alternatives.append({
                "name": form_details.get("title", alt.get("name", alt["form_id"])),
                "description": form_details.get("description", ""),
                "context": form_details.get("context_title", "General"),
                "confidence": alt.get("confidence", 0.0)
            })
        
        if confidence_result.level.value == "medium" and user_friendly_alternatives:
            message = f"""I'm {confidence_result.score:.1%} confident about which form you need, but I want to make sure I get it right.

{confidence_result.reasoning}

Here are the forms I'm considering:

"""
            for i, alt in enumerate(user_friendly_alternatives, 1):
                confidence_bar = "🟩" * int(alt["confidence"] * 5) + "⬜" * (5 - int(alt["confidence"] * 5))
                message += f"**{i}. {alt['name']}** ({alt['context']})\n"
                message += f"   {alt['description']}\n"
                message += f"   Confidence: {confidence_bar} {alt['confidence']:.1%}\n\n"
            
            message += "Please tell me the **number** of the form you want to fill out, or describe your needs in more detail."
            
        else:
            # Low confidence - need more information
            message = f"""I'm only {confidence_result.score:.1%} confident about which form you're looking for.

{confidence_result.reasoning}

To help you better, I can show you:

🎯 **All available forms** - Browse the complete list
📋 **Forms by category** - Show forms grouped by type  
🔍 **Search forms** - Look for forms containing specific words

Or you could be more specific about:
• What type of report or form you need
• What situation or incident you're documenting  
• Which department or area this relates to

What would help you most?"""

        return message
    
    async def handle_clarification_response(self, user_response: str, clarification_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle user's response to clarification request"""
        
        try:
            # Check if user selected a number
            if user_response.strip().isdigit():
                selection = int(user_response.strip())
                alternatives = clarification_context.get("alternatives", [])
                
                if 1 <= selection <= len(alternatives):
                    selected_form = alternatives[selection - 1]
                    form_details = await self._get_form_details(selected_form["form_id"])
                    
                    return {
                        "form_template_id": selected_form["form_id"],
                        "confidence_score": 1.0,  # User explicitly selected
                        "reasoning": f"User selected option {selection}: {selected_form.get('name', selected_form['form_id'])}",
                        "form_details": form_details
                    }
            
            # Otherwise, re-analyze with the new information
            return await self.predict_form_with_confidence(
                user_response, 
                clarification_context.get("user_context", {})
            )
            
        except Exception as e:
            self.log_error(f"Error handling clarification response: {e}")
            return {
                "error_message": "I had trouble understanding your selection. Could you try again?",
                "confidence_score": 0.0
            }
    
    async def _get_available_forms(self, user_id: str) -> List[Dict[str, Any]]:
        """Get available forms for the user from database"""
        try:
            # Replace with your actual database query
            forms_collection = self.db.form_templates
            cursor = forms_collection.find({"status": "active"})
            
            forms = []
            async for form_doc in cursor:
                # Extract field names for context
                field_names = []
                for field in form_doc.get("fields", []):
                    if isinstance(field, dict):
                        field_names.append(field.get("name", field.get("id", "")))
                    else:
                        field_names.append(str(field))
                
                forms.append({
                    "id": str(form_doc["_id"]),
                    "title": form_doc.get("title", "Untitled Form"),
                    "description": form_doc.get("description", ""),
                    "context_title": form_doc.get("context", {}).get("title", "General"),
                    "field_names": field_names,
                    "created_at": form_doc.get("created_at"),
                    "updated_at": form_doc.get("updated_at")
                })
            
            self.log_info(f"Retrieved {len(forms)} available forms for user {user_id}")
            return forms
            
        except Exception as e:
            self.log_error(f"Error getting available forms: {e}")
            return []
    
    async def _get_form_details(self, form_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific form"""
        try:
            forms_collection = self.db.form_templates
            form_doc = await forms_collection.find_one({"_id": form_id})
            
            if form_doc:
                return {
                    "id": str(form_doc["_id"]),
                    "title": form_doc.get("title", "Untitled Form"),
                    "description": form_doc.get("description", ""),
                    "context_title": form_doc.get("context", {}).get("title", "General"),
                    "field_count": len(form_doc.get("fields", [])),
                    "estimated_time": form_doc.get("estimated_completion_time", "5 minutes")
                }
            else:
                return {"id": form_id, "title": "Unknown Form", "description": "Form details not available"}
                
        except Exception as e:
            self.log_error(f"Error getting form details: {e}")
            return {"id": form_id, "title": "Unknown Form", "description": "Error loading form details"}


# Additional utility classes and functions for interactive session management
# These are kept in the confidence system for completeness but can be moved to a separate module if needed

class InteractiveSessionManagerMixin:
    """
    Mixin class to add interactive session management capabilities to the base SessionManager.
    This can be used to extend SessionManager with interactive conversation support.
    """
    
    async def save_interaction_context(self, session_manager, session_id: str, context: Dict[str, Any]) -> None:
        """Save interaction context for follow-up questions"""
        try:
            session_data = await session_manager.get_session(session_id)
            if session_data:
                if not hasattr(session_data, 'interaction_context'):
                    session_data.interaction_context = {}
                
                session_data.interaction_context.update(context)
                await session_manager.save_session(session_data)
                
                logger.info(f"Saved interaction context for session {session_id}")
                
        except Exception as e:
            logger.error(f"Error saving interaction context: {e}")
    
    async def get_interaction_context(self, session_manager, session_id: str) -> Dict[str, Any]:
        """Get interaction context for processing follow-up questions"""
        try:
            session_data = await session_manager.get_session(session_id)
            if session_data and hasattr(session_data, 'interaction_context'):
                return session_data.interaction_context or {}
            return {}
            
        except Exception as e:
            logger.error(f"Error getting interaction context: {e}")
            return {}