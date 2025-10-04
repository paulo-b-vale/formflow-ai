# app/agents/report_generator_node.py
import logging
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from app.utils.langchain_utils import get_gemini_llm
from app.config.settings import settings
from app.utils.confidence_system import ConfidenceManager, ConfidenceResult
from app.database import db_connections
import json

# Import BaseNode components
from .base import BaseNode, state_get
from .types import StateType, ResponseType, NodeResponse, NodeType

logger = logging.getLogger(__name__)



class ReportGeneratorNode(BaseNode):
    """Enhanced report generator with interactive analytics"""

    def __init__(self, base_url: str = None):
        super().__init__(NodeType.REPORT_GENERATOR, "report_generator")
        self.llm = get_gemini_llm()
        self.confidence_manager = ConfidenceManager()
        self.base_url = base_url or getattr(settings, 'API_BASE_URL', 'http://localhost:8000')
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def execute(self, state: StateType) -> ResponseType:
        """Main entry point for report generation"""
        user_message = state_get(state, "user_message")
        user_id = state_get(state, "user_id", "unknown_user")  # Provide default
        session_id = state_get(state, "session_id")
        incident_form_types = state_get(state, "incident_form_types", [])

        self.logger.info(f"🔍 REPORT_GENERATOR: Starting execution")
        self.logger.info(f"🔍 REPORT_GENERATOR: user_message='{user_message}', user_id='{user_id}', session_id='{session_id}', incident_form_types={incident_form_types}")

        try:
            # Parse the report request
            report_params = await self._parse_report_intent(user_message, user_id)

            if report_params.get("needs_clarification"):
                return await self._handle_report_clarification(report_params, user_message)

            # Extract keywords with fallback
            keywords = report_params.get("keywords", [])

            # Fallback: If LLM failed to extract keywords, try basic extraction from user message
            if not keywords and user_message:
                keywords = self._extract_keywords_from_message(user_message)
                if keywords:
                    self.logger.warning(f"⚠️ REPORT_GENERATOR: LLM failed to extract keywords, using fallback: {keywords}")
                else:
                    self.logger.error(f"❌ REPORT_GENERATOR: No keywords extracted from message: '{user_message}'")
                    return NodeResponse(
                        final_response="I couldn't determine what type of forms you want a report about. Please be more specific about which forms or topics you're interested in (e.g., 'incident reports', 'safety forms', 'construction checklists').",
                        is_complete=False,
                        requires_clarification=True
                    )

            # Use improved keyword-based database query
            self.logger.info(f"🔍 REPORT_GENERATOR: Using enhanced database query with keywords: {keywords}")
            report_data = await self._query_forms_from_database(
                user_id=user_id,
                keywords=keywords,
                start_date=report_params.get("time_period", {}).get("start_date"),
                end_date=report_params.get("time_period", {}).get("end_date")
            )

            # Generate the actual report
            report_content = await self._generate_report(report_data, report_params)

            return NodeResponse(
                final_response=report_content,
                is_complete=True
            )
            
        except Exception as e:
            self.logger.error(f"🚨 REPORT_GENERATOR ERROR: {type(e).__name__}: {e}")
            self.logger.exception(f"🚨 REPORT_GENERATOR TRACEBACK:")
            return NodeResponse(
                final_response=f"I encountered an error while generating the report: {str(e)}. Please try again with a different request.",
                is_complete=False,
                error_message=str(e)
            )
    
    async def _parse_report_intent(self, user_message: str, user_id: str) -> Dict[str, Any]:
        """Parse user message to extract report parameters with multilingual support"""

        # Enhanced prompt with multilingual examples and better JSON structure
        prompt = f"""You are an expert at parsing report generation requests in multiple languages (English and Portuguese).
Extract report parameters from the user's message.

User message: "{user_message}"

Respond with ONLY valid JSON - no markdown, no extra text, just the JSON object:

{{
    "report_type": "summary",
    "time_period": {{
        "start_date": null,
        "end_date": null,
        "relative": null
    }},
    "form_types": [],
    "keywords": [],
    "language": "en|pt",
    "metrics": ["completion_rate", "response_time", "field_analysis"],
    "format": "summary",
    "focus_areas": [],
    "confidence_score": 0.8,
    "confidence_reasoning": "User asked for incident report, high confidence"
}}

IMPORTANT KEYWORD MAPPING:
- "incident/incidente/acidente" → keywords: ["incident", "incidente", "acidente"]
- "report/relatório" → keywords: ["report", "relatório"]
- "construction/construção" → keywords: ["construction", "construção"]
- "hospital/médico" → keywords: ["hospital", "médico", "medical"]

Examples:
- "give a report about incident" → {{"report_type": "summary", "keywords": ["incident", "incidente"], "language": "en", "confidence_score": 0.9}}
- "relatório de incidente" → {{"report_type": "summary", "keywords": ["incident", "incidente"], "language": "pt", "confidence_score": 0.9}}
- "incidente construction" → {{"report_type": "summary", "keywords": ["incident", "incidente", "construction", "construção"], "confidence_score": 0.85}}
"""

        try:
            response = await self.llm.ainvoke(prompt)
            response_content = response.content.strip()

            # Log the raw response for debugging
            self.logger.info(f"🔍 REPORT_GENERATOR: Raw LLM response: {response_content[:200]}...")

            # Try to extract JSON from the response if it's wrapped in markdown or other text
            json_content = response_content
            if "```json" in response_content:
                # Extract JSON from markdown code blocks
                start = response_content.find("```json") + 7
                end = response_content.find("```", start)
                if end != -1:
                    json_content = response_content[start:end].strip()
            elif response_content.startswith("```") and response_content.endswith("```"):
                # Remove generic code block markers
                json_content = response_content[3:-3].strip()
            elif "{" in response_content and "}" in response_content:
                # Extract JSON from within the response
                start = response_content.find("{")
                end = response_content.rfind("}") + 1
                json_content = response_content[start:end]

            self.logger.info(f"🔍 REPORT_GENERATOR: Extracted JSON content: {json_content[:200]}...")

            if not json_content.strip():
                raise json.JSONDecodeError("Empty JSON content", "", 0)

            report_params = json.loads(json_content)

            # Resolve relative dates
            if report_params.get("time_period", {}).get("relative"):
                report_params["time_period"] = self._resolve_relative_dates(
                    report_params["time_period"]["relative"]
                )

            # Use ConfidenceManager to evaluate the parsing result
            context = {
                "alternatives": [],  # No alternatives for parsing, but include for consistency
                "reasoning": report_params.get("confidence_reasoning", "")
            }
            confidence_result: ConfidenceResult = self.confidence_manager.evaluate_confidence(
                report_params.get("confidence_score", 0.0), context
            )

            # Add confidence system results to the report params
            report_params["confidence_level"] = confidence_result.level.value
            if confidence_result.requires_clarification and confidence_result.clarification_message:
                report_params["needs_clarification"] = True
                report_params["clarification_message"] = confidence_result.clarification_message
            else:
                report_params["needs_clarification"] = False
                report_params["clarification_message"] = None

            return report_params

        except (json.JSONDecodeError, Exception) as e:
            self.logger.error(f"Error parsing report intent: {e}")
            if hasattr(response, 'content'):
                self.logger.error(f"Raw response content: {response.content}")

            # Return a low-confidence result that requires clarification
            context = {
                "alternatives": [],
                "reasoning": f"Error parsing report intent: {str(e)}"
            }
            confidence_result: ConfidenceResult = self.confidence_manager.evaluate_confidence(0.0, context)

            return {
                "report_type": "summary",
                "needs_clarification": True,
                "clarification_message": confidence_result.clarification_message or "Could you please provide more specific details about what you're looking for?",
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
    
    async def _handle_report_clarification(self, report_params: Dict[str, Any], original_message: str) -> Dict[str, Any]:
        """Handle cases where report intent needs clarification using ConfidenceManager"""
        
        # If we have a clarification message from the confidence system, use it
        if report_params.get("clarification_message"):
            clarification_message = report_params["clarification_message"]
        else:
            # Fallback to our own message
            reason = report_params.get("clarification_reason", "I couldn't understand your report request clearly")
            
            clarification_message = f"""I'd like to help you generate a report, but I need more details about "{original_message}".

{reason}

I can generate these types of reports:

📊 **Summary Reports**: Overall statistics and key metrics
📈 **Analytics Reports**: Detailed analysis and trends over time  
✅ **Completion Rate Reports**: Form completion statistics
⏱️ **Response Time Analysis**: How quickly forms are filled out
🔍 **Field Analysis**: Most/least used fields, common responses
👥 **User Activity Reports**: Who's submitting forms and when

For any report, I can focus on:
• Specific time periods (this week, last month, etc.)
• Particular form types (safety reports, checklists, etc.) 
• Specific metrics or areas of interest

What kind of report would you like? Please be specific about:
- **Type**: What kind of analysis do you need?
- **Time period**: What date range should I cover?
- **Scope**: All forms or specific types?
- **Detail level**: Summary or detailed breakdown?"""

        return NodeResponse(
            final_response=clarification_message,
            is_complete=False,
            requires_clarification=True
        )
    
    async def _gather_report_data(self, report_params: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Gather data needed for the report using API endpoints"""
        
        try:
            # Build query parameters for data gathering
            query_params = {"user_id": user_id}
            
            time_period = report_params.get("time_period", {})
            if time_period.get("start_date"):
                query_params["start_date"] = time_period["start_date"]
            if time_period.get("end_date"):
                query_params["end_date"] = time_period["end_date"]
            
            if report_params.get("form_types"):
                query_params["form_types"] = ",".join(report_params["form_types"])
            
            async with self.http_client as client:
                auth_header = {"Authorization": f"Bearer {await self._get_auth_token(user_id)}"}
                
                # Get form submissions data
                forms_response = await client.get(
                    f"{self.base_url}/api/forms/submissions",
                    params=query_params,
                    headers=auth_header
                )
                
                # Get analytics data
                analytics_response = await client.get(
                    f"{self.base_url}/api/analytics/forms",
                    params=query_params,
                    headers=auth_header
                )
                
                # Get form templates
                templates_response = await client.get(
                    f"{self.base_url}/api/forms/templates",
                    headers=auth_header
                )
                
                return {
                    "submissions": forms_response.json() if forms_response.status_code == 200 else [],
                    "analytics": analytics_response.json() if analytics_response.status_code == 200 else {},
                    "templates": templates_response.json() if templates_response.status_code == 200 else [],
                    "query_params": query_params
                }
                
        except Exception as e:
            self.logger.error(f"Error gathering report data: {e}")
            # Return mock data for development
            return await self._get_mock_report_data(report_params)
    
    async def _get_mock_report_data(self, report_params: Dict[str, Any]) -> Dict[str, Any]:
        """Mock report data for development"""
        return {
            "submissions": [
                {
                    "id": "form_1",
                    "template_id": "safety_report",
                    "template_name": "Safety Incident Report", 
                    "submitted_by": "John Doe",
                    "submitted_at": "2025-09-26T14:30:00Z",
                    "completion_time_seconds": 420,
                    "status": "completed"
                },
                {
                    "id": "form_2",
                    "template_id": "daily_checklist", 
                    "template_name": "Daily Equipment Checklist",
                    "submitted_by": "Jane Smith",
                    "submitted_at": "2025-09-26T09:15:00Z", 
                    "completion_time_seconds": 180,
                    "status": "completed"
                }
            ],
            "analytics": {
                "total_submissions": 15,
                "completion_rate": 0.87,
                "average_completion_time": 300,
                "most_active_users": ["John Doe", "Jane Smith"],
                "form_type_distribution": {
                    "safety_report": 8,
                    "daily_checklist": 7
                }
            },
            "templates": [
                {"id": "safety_report", "name": "Safety Incident Report", "field_count": 12},
                {"id": "daily_checklist", "name": "Daily Equipment Checklist", "field_count": 8}
            ]
        }
    
    async def _generate_report(self, data: Dict[str, Any], params: Dict[str, Any]) -> str:
        """Generate the actual report content using LLM"""

        report_type = params.get("report_type", "summary")
        format_type = params.get("format", "summary")

        # Detect if this is an incident report
        is_incident_report = self._is_incident_data(data)

        # Prepare data summary for LLM
        data_summary = {
            "total_submissions": len(data.get("submissions", [])),
            "analytics": data.get("analytics", {}),
            "templates": data.get("templates", []),
            "time_period": params.get("time_period", {}),
            "is_incident_report": is_incident_report
        }

        # Detect language from report params
        language = params.get("language", "en")
        is_portuguese = language == "pt"

        if is_incident_report:
            if is_portuguese:
                prompt = f"""Gere um RELATÓRIO ABRANGENTE DE SEGURANÇA DE INCIDENTES com base nos dados de envio de formulários de incidentes a seguir.

Tipo de Relatório: {report_type}
Formato: {format_type}
Resumo dos Dados: {json.dumps(data_summary, indent=2, default=str)}
Envios de Incidentes em Bruto: {json.dumps(data.get('submissions', [])[:10], indent=2, default=str)}

Este é um RELATÓRIO DE INCIDENTE DE SEGURANÇA. Crie um relatório bem estruturado que inclua:

1. **🚨 Resumo Executivo** - Destaques críticos de segurança e visão geral do incidente
2. **📊 Estatísticas de Incidentes** - Total de incidentes, tipos, níveis de gravidade
3. **🏗️ Análise de Segurança** - Padrões, tendências e fatores de risco identificados
4. **⚠️ Métricas-chave de Segurança** - Taxas de incidentes, tempos de resposta, causas comuns
5. **🛡️ Recomendações de Segurança** - Etapas práticas para prevenir futuros incidentes
6. **📈 Tendências e Padrões** - Análise baseada em tempo da frequência de incidentes
7. **👥 Impacto no Pessoal** - Indivíduos e departamentos afetados

Foque em SEGURANÇA e PREVENÇÃO. Destaque:
- Tipos de incidentes mais comuns
- Áreas ou atividades de alto risco
- Padrões de tempo (dias/horas com mais incidentes)
- Análise de severidade
- Medidas preventivas necessárias

Use linguagem clara focada em segurança e enfatize melhorias de segurança acionáveis.
Inclua números específicos, porcentagens e métricas de segurança quando relevante.
Responda SEMPRE em português brasileiro.
"""
            else:
                prompt = f"""Generate a comprehensive INCIDENT SAFETY REPORT based on the following incident form submission data.

Report Type: {report_type}
Format: {format_type}
Data Summary: {json.dumps(data_summary, indent=2, default=str)}
Raw Incident Submissions: {json.dumps(data.get('submissions', [])[:10], indent=2, default=str)}

This is a SAFETY INCIDENT REPORT. Create a well-structured report that includes:

1. **🚨 Executive Summary** - Critical safety highlights and incident overview
2. **📊 Incident Statistics** - Total incidents, types, severity levels
3. **🏗️ Safety Analysis** - Patterns, trends, and risk factors identified
4. **⚠️ Key Safety Metrics** - Incident rates, response times, common causes
5. **🛡️ Safety Recommendations** - Actionable steps to prevent future incidents
6. **📈 Trends and Patterns** - Time-based analysis of incident frequency
7. **👥 Personnel Impact** - Affected individuals and departments

Focus on SAFETY and PREVENTION. Highlight:
- Most common incident types
- High-risk areas or activities
- Time patterns (days/hours with more incidents)
- Severity analysis
- Preventive measures needed

Use clear safety-focused language and emphasize actionable safety improvements.
Include specific numbers, percentages, and safety metrics where relevant.
"""
        else:
            prompt = f"""Generate a comprehensive {report_type} report based on the following form submission data.

Report Type: {report_type}
Format: {format_type}
Data Summary: {json.dumps(data_summary, indent=2, default=str)}
Raw Submissions: {json.dumps(data.get('submissions', [])[:10], indent=2, default=str)}  # First 10 for context

Create a well-structured report that includes:

1. **Executive Summary** - Key highlights and metrics
2. **Data Overview** - Basic statistics and counts
3. **Analysis** - Insights and patterns found in the data
4. **Key Metrics** - Important performance indicators
5. **Recommendations** - Actionable insights (if applicable)

Make the report engaging, informative, and actionable. Use emojis and formatting to make it visually appealing.
Include specific numbers and percentages where relevant.

Focus on providing valuable insights that would help improve form processes and user experience.
"""

        try:
            response = await self.llm.ainvoke(prompt)
            report_content = response.content
            
            # Add interactive footer
            report_content += "\n\n" + self._generate_interactive_footer(data, params)
            
            return report_content
            
        except Exception as e:
            self.logger.error(f"Error generating report content: {e}")
            return self._generate_basic_report(data, params)
    
    def _generate_basic_report(self, data: Dict[str, Any], params: Dict[str, Any]) -> str:
        """Generate a basic report as fallback"""
        submissions = data.get("submissions", [])
        analytics = data.get("analytics", {})
        
        report = f"""# 📊 Form Submissions Report

## Executive Summary
- **Total Submissions**: {len(submissions)}
- **Completion Rate**: {analytics.get('completion_rate', 0) * 100:.1f}%
- **Average Completion Time**: {analytics.get('average_completion_time', 0)} seconds

## Recent Activity
"""
        
        for submission in submissions[:5]:
            report += f"- {submission.get('template_name', 'Unknown Form')} by {submission.get('submitted_by', 'Unknown')} ({self._format_date(submission.get('submitted_at', ''))})\n"
        
        if len(submissions) > 5:
            report += f"\n... and {len(submissions) - 5} more submissions\n"
        
        return report + "\n" + self._generate_interactive_footer(data, params)
    
    def _generate_interactive_footer(self, data: Dict[str, Any], params: Dict[str, Any]) -> str:
        """Generate interactive options footer"""
        return """---

**What would you like to do next?**
📈 Generate a different type of report
🔍 Search for specific forms from this data  
📊 Get detailed analytics on specific metrics
📋 Export this data in a different format
❓ Ask questions about this data

Just let me know what interests you most!"""
    
    def _format_date(self, date_string: str) -> str:
        """Format date string for display"""
        try:
            if date_string:
                dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
                return dt.strftime("%Y-%m-%d")
            return "Unknown"
        except Exception:
            return "Unknown"
    
    def _is_incident_data(self, data: Dict[str, Any]) -> bool:
        """Detect if the report data contains incident-related information."""
        try:
            templates = data.get("templates", [])
            submissions = data.get("submissions", [])

            # Check template titles for incident keywords
            incident_keywords = ["incident", "incidente", "acidente", "accident", "segurança", "safety"]
            for template in templates:
                title = template.get("title", "").lower()
                if any(keyword in title for keyword in incident_keywords):
                    return True

            # Check submission form titles for incident keywords
            for submission in submissions:
                form_title = submission.get("form_title", "").lower()
                if any(keyword in form_title for keyword in incident_keywords):
                    return True

            return False
        except Exception:
            return False

    async def _get_auth_token(self, user_id: str) -> str:
        """Get authentication token for API calls"""
        return "mock_token_for_development"

    async def _query_forms_from_database(self, user_id: str, keywords: List[str] = None,
                                         start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Enhanced form query with multilingual keyword support."""
        try:
            db = db_connections.mongo_db

            # Build enhanced keyword search query
            template_query = {}

            if keywords:
                # Create regex pattern for multilingual search
                keyword_pattern = "|".join(keywords)
                template_query = {
                    "$or": [
                        {"title": {"$regex": keyword_pattern, "$options": "i"}},
                        {"description": {"$regex": keyword_pattern, "$options": "i"}}
                    ]
                }
                self.logger.info(f"🔍 FORM_QUERY: Searching forms with keywords: {keywords}")
                self.logger.info(f"🔍 FORM_QUERY: MongoDB query: {template_query}")
            else:
                # If no keywords, get all forms
                self.logger.info(f"🔍 FORM_QUERY: No keywords provided, getting all forms")

            # Get matching form templates
            matching_templates = []
            async for template in db.form_templates.find(template_query):
                matching_templates.append({
                    "id": str(template["_id"]),
                    "title": template.get("title", ""),
                    "description": template.get("description", ""),
                    "context_id": template.get("context_id", ""),
                    "fields": template.get("fields", [])
                })

            self.logger.info(f"🔍 FORM_QUERY: Found {len(matching_templates)} matching templates")
            for template in matching_templates:
                self.logger.info(f"  - {template['title']} (ID: {template['id']})")

            if not matching_templates:
                self.logger.warning(f"🔍 FORM_QUERY: No templates found for keywords: {keywords}")
                return {"templates": [], "submissions": [], "analytics": {}}

            # Get template IDs for submission query
            template_ids = [template["id"] for template in matching_templates]

            # Build query for form responses
            submission_query = {
                "form_template_id": {"$in": template_ids}
            }

            # Add date filters if provided
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter["$gte"] = start_date
                if end_date:
                    date_filter["$lte"] = end_date
                if date_filter:
                    submission_query["submitted_at"] = date_filter

            self.logger.info(f"🔍 FORM_QUERY: Querying responses with: {submission_query}")

            # Query form submissions
            submissions = []
            analytics = {
                "total_submissions": 0,
                "completion_rate": 0.0,
                "form_type_distribution": {},
                "recent_activity": []
            }

            submission_count = 0
            async for submission in db.form_responses.find(submission_query).sort("submitted_at", -1):
                submission_count += 1
                template_title = next((t["title"] for t in matching_templates if t["id"] == submission.get("form_template_id")), "Unknown")

                submissions.append({
                    "id": str(submission["_id"]),
                    "form_template_id": submission.get("form_template_id"),
                    "form_title": template_title,
                    "user_id": submission.get("user_id"),
                    "responses": submission.get("responses", {}),
                    "submitted_at": submission.get("submitted_at"),
                    "status": submission.get("status", "completed")
                })

                # Update analytics
                analytics["form_type_distribution"][template_title] = analytics["form_type_distribution"].get(template_title, 0) + 1

            analytics["total_submissions"] = len(submissions)
            analytics["completion_rate"] = 1.0 if submissions else 0.0

            self.logger.info(f"🔍 FORM_QUERY: Found {len(matching_templates)} templates and {len(submissions)} submissions")
            self.logger.info(f"🔍 FORM_QUERY: Form distribution: {analytics['form_type_distribution']}")

            return {
                "templates": matching_templates,
                "submissions": submissions,
                "analytics": analytics
            }

        except Exception as e:
            self.logger.error(f"🚨 FORM_QUERY ERROR: {e}")
            self.logger.exception("Full traceback:")
            return {"templates": [], "submissions": [], "analytics": {}, "error": str(e)}

    def _extract_keywords_from_message(self, user_message: str) -> List[str]:
        """
        Fallback keyword extraction when LLM fails.
        Extracts common form-related keywords from user message.
        """
        keywords = []
        message_lower = user_message.lower()

        # Common keyword mappings (add more as needed)
        keyword_map = {
            "incident": ["incident", "incidente", "acidente"],
            "safety": ["safety", "segurança"],
            "construction": ["construction", "construção", "obra"],
            "hospital": ["hospital", "hospitalar", "médico", "medical"],
            "maintenance": ["maintenance", "manutenção"],
            "inspection": ["inspection", "inspeção"],
            "checklist": ["checklist", "verificação"],
            "report": ["report", "relatório"],
            "evaluation": ["evaluation", "avaliação"],
            "assessment": ["assessment", "avaliação"],
        }

        # Extract keywords that appear in the message
        for key, variants in keyword_map.items():
            if any(variant in message_lower for variant in variants):
                keywords.extend(variants)

        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)

        return unique_keywords

    def _get_required_state_keys(self) -> list:
        """Get required state keys for report generation."""
        return ["session_id", "user_message"]