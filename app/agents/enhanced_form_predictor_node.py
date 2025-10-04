# app/agents/enhanced_form_predictor_node.py
from app.utils.observability import ObservabilityMixin
from app.utils.langchain_utils import get_gemini_llm
from app.database import db
from app.utils.confidence_system import ConfidenceManager, ConfidenceResult
from app.cache.redis_cache import get_cached_user_forms, cache_user_forms
from app.agents.reasoning.form_selection import smart_form_selector, FormAlternative
from app.agents.prompts.manager import PromptManager
from app.agents.prompts.templates import PromptLibrary
from app.agents.base import state_get
import json
import logging
import httpx
import uuid
from bson import ObjectId

logger = logging.getLogger(__name__)

class EnhancedFormPredictorNode(ObservabilityMixin):
    def __init__(self):
        self.llm = get_gemini_llm()
        self.confidence_manager = ConfidenceManager()
        self.prompt_manager = PromptManager()
        self.prompt_library = PromptLibrary(self.prompt_manager)
        self.confidence_threshold = 0.7  # Threshold for smart form selection

    async def run(self, state):
        """
        Enhanced form prediction with interactive confidence handling and API integration.
        """
        # Use state_get instead of getattr to properly handle dict states
        user_message = state_get(state, "user_message")
        user_token = state_get(state, "user_token")
        user_id = state_get(state, "user_id")
        api_client = state_get(state, "api_client")
        session_id = state_get(state, "session_id")

        self.log_info(f"Predicting form for message: {user_message}")

        # Check if this is actually a report/analysis request that was misrouted
        if user_message:
            user_msg_lower = user_message.lower()
            report_indicators = ["report", "relatório", "analysis", "análise", "resumo", "summary",
                               "dados", "data", "estatística", "estatisticas", "tendência", "trend",
                               "gerar", "generate", "criar", "create", "mostrar dados", "show data"]

            incident_indicators = ["incident", "incidente", "acidente", "accident", "segurança", "safety",
                                 "construção", "construction", "obra", "workplace", "lesão", "injury"]

            has_report_request = any(indicator in user_msg_lower for indicator in report_indicators)
            has_incident_context = any(indicator in user_msg_lower for indicator in incident_indicators)

            if has_report_request:
                print(f"🔀 FORM_PREDICTOR: Detected report request, redirecting to report_generator")

                # Identify specific incident forms if this is an incident report request
                incident_form_types = []
                if has_incident_context:
                    if any(word in user_msg_lower for word in ["construção", "construction", "obra"]):
                        incident_form_types.append("construction_incident")
                    if any(word in user_msg_lower for word in ["hospital", "médico", "medical", "patient"]):
                        incident_form_types.append("hospital_incident")

                return {
                    "next_node": "report_generator",
                    "requires_clarification": False,
                    "incident_form_types": incident_form_types,
                    "final_response": "Detectei que você quer um relatório. Redirecionando para o gerador de relatórios...",
                    "reasoning": f"User request appears to be for report generation with incident context: {incident_form_types}"
                }

        # Get available forms with caching optimization
        logger.info(f"Form access check - user_id: {user_id}, user_token present: {bool(user_token)}, api_client present: {bool(api_client)}")

        # Try cache first
        available_forms = await get_cached_user_forms(user_id) if user_id else None

        if available_forms:
            logger.info(f"✅ Using cached forms for user {user_id}: {len(available_forms)} forms")
        else:
            # Cache miss - fetch from API or database
            if user_token and api_client and user_id:
                available_forms = await self._get_user_forms_via_api(user_id, user_token, api_client)
            else:
                # Fallback to database query, ensuring to pass user_id for access filtering
                available_forms = await self._get_forms_from_database(user_id)

            # Cache the result for future requests
            if available_forms and user_id:
                await cache_user_forms(user_id, available_forms)
                logger.info(f"✅ Retrieved and cached {len(available_forms)} forms for user {user_id}")
            else:
                logger.warning(f"⚠️ No forms retrieved for user {user_id}")

        if not available_forms:
            return {
                "error_message": "Nenhum formulário está disponível para você no momento. Entre em contato com seu administrador para obter acesso aos formulários.",
                "confidence_score": 0.0,
                "reasoning": "No accessible forms found"
            }

        # Enhanced prediction with detailed form analysis
        prediction_result = await self._predict_form_with_confidence(user_message, available_forms)

        # Add original user message and session_id to prediction for context
        prediction_result["original_user_message"] = user_message
        prediction_result["session_id"] = session_id

        # Handle different confidence levels interactively
        return await self._handle_prediction_result(prediction_result, available_forms)

    async def _get_user_forms_via_api(self, user_id: str, user_token: str, api_client: httpx.AsyncClient) -> list:
        """Get forms available to the user via API calls."""
        try:
            logger.info(f"Attempting to get forms via API for user {user_id}")
            headers = {"Authorization": f"Bearer {user_token}"}

            # Get user's accessible contexts
            contexts_response = await api_client.get(
                f"/forms-management/contexts",
                headers=headers
            )

            logger.info(f"Contexts API response: {contexts_response.status_code}")
            if contexts_response.status_code != 200:
                logger.warning(f"Failed to fetch user contexts via API: {contexts_response.status_code}, falling back to database")
                return await self._get_forms_from_database(user_id)
            
            user_contexts = contexts_response.json()
            
            # For each context the user has access to, we need to somehow get the templates
            # Since there's no direct API endpoint for non-admins to list all forms by context,
            # we'll use the database method which is more reliable for access control
            logger.info(f"User has access to {len(user_contexts)} contexts, using database fallback for form retrieval")
            return await self._get_forms_from_database(user_id)
        
        except Exception as e:
            logger.error(f"Error retrieving forms via API: {e}")
            return await self._get_forms_from_database(user_id)

    async def _get_forms_from_database(self, user_id: str = None) -> list:
        """Fallback method to get forms directly from database."""
        try:
            # Get contexts the user has access to
            context_query = {}
            if user_id:
                # Ensure we search for both string and ObjectId versions of user_id
                user_id_str = str(user_id)
                context_query["$or"] = [
                    {"created_by": user_id_str},
                    {"assigned_professionals": {"$in": [user_id_str]}},
                    {"assigned_users": {"$in": [user_id_str]}}
                ]

            logger.info(f"Searching for contexts with query: {context_query}")
            contexts_cursor = db.contexts.find(context_query)
            accessible_context_ids = set()
            context_count = 0
            async for context in contexts_cursor:
                context_count += 1
                # Convert ObjectId to string since form templates store context_id as string
                accessible_context_ids.add(str(context["_id"]))

            logger.info(f"Found {context_count} accessible contexts for user {user_id}: {list(accessible_context_ids)}")

            # Get forms that belong to accessible contexts and are not archived
            forms_query = {
                "status": {"$ne": "archived"},
                "context_id": {"$in": list(accessible_context_ids)}
            }
            logger.info(f"Searching for forms with query: {forms_query}")

            forms_cursor = db.form_templates.find(forms_query, {
                "title": 1, "description": 1, "context_id": 1, "fields": 1, "tags": 1
            })

            forms_list = []
            form_count = 0
            async for form in forms_cursor:
                form_count += 1
                # Get context information for enrichment
                context = await db.contexts.find_one({"_id": form["context_id"]})
                
                access_level = "limited"
                if context:
                    if str(context.get('created_by')) == str(user_id):
                        access_level = "owner"
                    elif str(user_id) in [str(p) for p in context.get('assigned_professionals', [])]:
                        access_level = "professional"
                    elif str(user_id) in [str(u) for u in context.get('assigned_users', [])]:
                        access_level = "user"
                
                form_data = {
                    "id": str(form['_id']),
                    "title": form['title'],
                    "description": form.get('description', ''),
                    "context_title": context.get("title", "Unknown Context") if context else "Unknown Context",
                    "context_description": context.get("description", "") if context else "",
                    "field_count": len(form.get('fields', [])),
                    "required_fields": len([f for f in form.get('fields', []) if f.get('required', False)]),
                    "tags": form.get('tags', []),
                    "access_level": access_level
                }
                forms_list.append(form_data)

            logger.info(f"Found {form_count} forms in database, retrieved {len(forms_list)} forms for user {user_id}")
            return forms_list
            
        except Exception as e:
            logger.error(f"Error retrieving forms from database: {e}")
            return []

    def _determine_access_level(self, user_id: str, context: dict, form: dict) -> str:
        """Determine user's access level to the form."""
        if context.get('created_by') == user_id:
            return "owner"
        elif user_id in context.get('assigned_professionals', []):
            return "professional"
        elif user_id in context.get('assigned_users', []):
            return "user"
        else:
            return "limited"

    async def _predict_form_with_confidence(self, user_message: str, available_forms: list) -> dict:
        """Enhanced form prediction with detailed analysis using managed prompts."""

        # Format available forms for the enhanced prompt template
        available_forms_text = self._format_forms_for_prompt(available_forms)

        # Use the enhanced prompt template v3 that provides alternatives
        template_id = self.prompt_library.get_form_prediction_prompt(enhanced=True)

        try:
            # Execute prompt using the centralized prompt manager (async version)
            result = await self.prompt_manager.execute_prompt_async(
                template_id,
                self.llm.ainvoke,
                user_message=user_message,
                available_forms=available_forms_text
            )

            if not result.success:
                logger.error(f"Prompt execution failed: {result.error_message}")
                return self._create_error_prediction_result(result.error_message)

            # Parse the structured response
            try:
                # Clean the response - remove markdown code blocks and preamble
                clean_response = result.raw_response.strip()

                # Remove markdown code blocks
                if clean_response.startswith("```json"):
                    clean_response = clean_response[7:]
                if clean_response.startswith("```"):
                    clean_response = clean_response[3:]
                if clean_response.endswith("```"):
                    clean_response = clean_response[:-3]
                clean_response = clean_response.strip()

                # Try to find JSON in the response (handles cases where LLM adds preamble)
                json_start = clean_response.find('{')
                if json_start > 0:
                    logger.warning(f"LLM added preamble before JSON, skipping {json_start} characters")
                    clean_response = clean_response[json_start:]

                json_end = clean_response.rfind('}')
                if json_end > 0 and json_end < len(clean_response) - 1:
                    logger.warning(f"LLM added postamble after JSON, truncating")
                    clean_response = clean_response[:json_end + 1]

                prediction_data = json.loads(clean_response)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response: {result.raw_response[:500]}")
                logger.error(f"JSON decode error: {e}")
                return self._create_error_prediction_result("Response parsing error")

            # Transform from enhanced template format to our expected format
            prediction_result = self._transform_enhanced_prediction(prediction_data, available_forms)

            # Validate and enrich the prediction result
            prediction_result = self._validate_prediction_result(prediction_result, available_forms)

            logger.info(f"Form prediction completed: ID={prediction_result.get('predicted_form_id')}, Confidence={prediction_result.get('confidence_score', 0):.2f}")

            return prediction_result

        except Exception as e:
            logger.error(f"Form prediction error: {e}")
            return self._create_error_prediction_result(f"Prediction system error: {str(e)}")

    def _format_forms_for_prompt(self, available_forms: list) -> str:
        """Format available forms for the enhanced prompt template."""
        forms_description = []
        for form in available_forms:
            form_desc = f"""
ID: {form.get('id', 'unknown')}
Título: {form.get('title', 'Sem título')}
Contexto: {form.get('context_title', 'Desconhecido')}
Descrição: {form.get('description', 'Sem descrição disponível')}
Campos: {form.get('field_count', 0)} total ({form.get('required_fields', 0)} obrigatórios)
Tags: {', '.join(form.get('tags', [])) if form.get('tags') else 'Nenhuma'}
Nível de Acesso: {form.get('access_level', 'limitado')}
"""
            forms_description.append(form_desc.strip())

        return "\n\n---\n\n".join(forms_description)

    def _transform_enhanced_prediction(self, prediction_data: dict, available_forms: list) -> dict:
        """Transform enhanced prompt response to our expected format."""
        # Extract primary prediction
        primary = prediction_data.get("primary_prediction", {})

        # Transform alternatives to our format
        alternatives = []
        for alt in prediction_data.get("alternative_forms", []):
            alternatives.append({
                "id": alt.get("form_id"),
                "title": alt.get("title"),
                "confidence": alt.get("confidence"),
                "reason": alt.get("reasoning"),
                "context_title": alt.get("context_title")
            })

        return {
            "predicted_form_id": primary.get("form_id"),
            "confidence_score": primary.get("confidence_score", 0.0),
            "reasoning": primary.get("reasoning", ""),
            "keyword_matches": primary.get("matched_keywords", []),
            "alternative_forms": alternatives,
            "requires_clarification": prediction_data.get("requires_user_selection", False),
            "clarification_type": "low_confidence" if prediction_data.get("requires_user_selection") else "none",
            "user_intent_analysis": "Análise baseada em palavras-chave e contexto",
            "overall_confidence": prediction_data.get("overall_confidence", 0.0),
            "reasoning_steps": prediction_data.get("reasoning_steps", [])
        }

    def _create_error_prediction_result(self, error_message: str) -> dict:
        """Create a standard error prediction result."""
        return {
            "predicted_form_id": None,
            "confidence_score": 0.0,
            "reasoning": error_message,
            "requires_clarification": True,
            "clarification_type": "system_error",
            "alternative_forms": []
        }

    def _validate_prediction_result(self, result: dict, available_forms: list) -> dict:
        """Validate and enrich the prediction result."""
        predicted_id = result.get("predicted_form_id")
        
        # Ensure predicted form exists in available forms
        if predicted_id and predicted_id != "null":
            form_exists = any(form.get("id") == predicted_id for form in available_forms)
            if not form_exists:
                logger.warning(f"Predicted form ID {predicted_id} not found in available forms")
                result["predicted_form_id"] = None
                result["confidence_score"] = 0.0
                result["requires_clarification"] = True
        
        # Ensure confidence score is valid
        confidence = result.get("confidence_score", 0.0)
        if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
            result["confidence_score"] = 0.0
        
        # Auto-set clarification requirement for low confidence
        if result.get("confidence_score", 0) < 0.7:
            result["requires_clarification"] = True
            if not result.get("clarification_type"):
                result["clarification_type"] = "low_confidence"
        
        return result

    async def _handle_prediction_result(self, prediction: dict, available_forms: list) -> dict:
        """Handle prediction results with smart form selection for low confidence scenarios."""
        predicted_id = prediction.get("predicted_form_id")
        confidence_score = prediction.get("confidence_score", 0.0)
        reasoning = prediction.get("reasoning", "")
        requires_user_selection = prediction.get("requires_clarification", False)
        session_id = prediction.get("session_id")  # Preserve original session_id

        # First check if the LLM determined that user selection is needed
        # This respects the LLM's analysis which considers context beyond just confidence score
        if requires_user_selection or smart_form_selector.should_show_alternatives(confidence_score):
            # REQUIRES CLARIFICATION: Use SmartFormSelector to present alternatives
            reason = "LLM determined clarification needed" if requires_user_selection else f"Low confidence ({confidence_score:.2f})"
            logger.info(f"Showing form alternatives - Reason: {reason}")

            # Use existing session_id or create a new one for tracking this selection
            selection_tracking_id = str(uuid.uuid4())

            # Create selection scenario using the smart form selector
            scenario = smart_form_selector.create_selection_scenario(
                user_message=prediction.get("original_user_message", "Solicitação do usuário"),
                prediction_result=prediction,
                session_id=selection_tracking_id
            )

            # Generate user-friendly selection message
            selection_message = scenario.generate_selection_message()

            return {
                "session_id": session_id,  # Preserve original session_id
                "requires_clarification": True,
                "requires_form_selection": True,
                "selection_session_id": selection_tracking_id,
                "clarification_message": selection_message,
                "confidence_score": confidence_score,
                "reasoning": reasoning,
                "alternative_forms": [alt.to_dict() for alt in scenario.alternatives],
                "overall_confidence": prediction.get("overall_confidence", confidence_score)
            }
        else:
            # HIGH CONFIDENCE: Direct form assignment
            form_details = self._get_form_details(predicted_id, available_forms)

            # Use ConfidenceManager for confidence level evaluation
            context = {
                "alternatives": prediction.get("alternative_forms", []),
                "reasoning": reasoning
            }
            confidence_result: ConfidenceResult = self.confidence_manager.evaluate_confidence(confidence_score, context)

            success_message = f"✅ Perfeito! Encontrei o formulário certo para você: **{form_details.get('title', 'Formulário Desconhecido')}** de {form_details.get('context_title', 'Contexto Desconhecido')}."

            if form_details.get('description'):
                success_message += f"\n\n📄 Sobre este formulário: {form_details['description']}"

            if reasoning:
                success_message += f"\n\n💭 Por que escolhi este: {reasoning}"

            success_message += f"\n\n📊 Confiança: {confidence_score:.0%} ({confidence_result.level.value}) | Este formulário tem {form_details.get('field_count', 0)} campos ({form_details.get('required_fields', 0)} obrigatórios)."
            success_message += "\n\n➡️ Vamos começar!"

            return {
                "session_id": session_id,  # Preserve original session_id
                "form_template_id": predicted_id,
                "confidence_score": confidence_score,
                "confidence_level": confidence_result.level.value,
                "reasoning": reasoning,
                "requires_clarification": False,
                "final_response": success_message,
                "form_details": form_details
            }

    def _create_confirmation_response(self, prediction: dict, available_forms: list) -> dict:
        """Create a response that asks user to confirm the predicted form."""
        predicted_id = prediction.get("predicted_form_id")
        confidence = prediction.get("confidence_score", 0.0)
        reasoning = prediction.get("reasoning", "")
        alternatives = prediction.get("alternative_forms", [])
        
        form_details = self._get_form_details(predicted_id, available_forms)
        
        message_parts = [
            f"I think you might want the **{form_details.get('title', 'Unknown Form')}** form from {form_details.get('context_title', 'Unknown Context')} (Confidence: {confidence:.0%})."
        ]
        
        if reasoning:
            message_parts.append(f"\n*Why I think this matches:* {reasoning}")
        
        if form_details.get('description'):
            message_parts.append(f"\n*About this form:* {form_details['description']}")
        
        message_parts.append(f"\n*Form details:* {form_details.get('field_count', 0)} fields, {form_details.get('required_fields', 0)} required")
        
        # Show alternatives if available
        if alternatives and len(alternatives) > 0:
            message_parts.append("**Other possible matches:**")
            for alt in alternatives[:2]:  # Show top 2 alternatives
                alt_details = self._get_form_details(alt.get('id'), available_forms)
                message_parts.append(f"• {alt_details.get('title', 'Unknown')} ({alt.get('confidence', 0):.0%} match)")
        
        message_parts.append("**Is this the right form?** Reply 'yes' to proceed, or tell me which form you'd prefer.")
        
        return {
            "form_template_id": predicted_id,
            "confidence_score": confidence,
            "reasoning": reasoning,
            "requires_clarification": True,
            "clarification_message": "".join(message_parts),
            "alternative_forms": alternatives
        }

    def _create_interactive_selection_response(self, prediction: dict, available_forms: list) -> dict:
        """Create an interactive form selection response when confidence is low."""
        clarification_type = prediction.get("clarification_type", "unknown")
        reasoning = prediction.get("reasoning", "Unable to determine the best form match")
        
        if clarification_type == "no_matches":
            message = f"I couldn't find a form that clearly matches your request. {reasoning}\n\n"
        elif clarification_type == "multiple_matches":
            message = f"Several forms could match your request. {reasoning}\n\n"
        else:
            message = f"I need more information to find the right form. {reasoning}\n\n"
        
        # Show available forms in an organized way
        message += "**Here are the forms you can access:**\n\n"
        
        # Group forms by context for better organization
        forms_by_context = {}
        for form in available_forms:
            context = form.get('context_title', 'Unknown Context')
            if context not in forms_by_context:
                forms_by_context[context] = []
            forms_by_context[context].append(form)
        
        for context, context_forms in forms_by_context.items():
            message += f"**📋 {context}:**\n"
            for form in context_forms[:3]:  # Limit to 3 forms per context
                field_info = f"({form.get('field_count', 0)} fields)"
                tags_info = f" | Tags: {', '.join(form.get('tags', []))}" if form.get('tags') else ""
                message += f"• **{form.get('title', 'Unknown')}** {field_info}{tags_info}\n"
                if form.get('description'):
                    message += f"  _{form.get('description')[:100]}{'...' if len(form.get('description', '')) > 100 else ''}_\n"
            
            if len(context_forms) > 3:
                message += f"  ... and {len(context_forms) - 3} more forms\n"
            message += "\n"
        
        message += "**Please tell me:**\n"
        message += "• Which form you'd like to work with (by name), or\n"
        message += "• More details about what you need to accomplish\n"
        
        return {
            "requires_clarification": True,
            "clarification_message": message,
            "confidence_score": prediction.get("confidence_score", 0.0),
            "reasoning": reasoning,
            "available_forms_summary": forms_by_context
        }

    def _get_form_details(self, form_id: str, available_forms: list) -> dict:
        """Get detailed information about a specific form."""
        for form in available_forms:
            if form.get('id') == form_id:
                return form
        
        return {
            "id": form_id,
            "title": "Unknown Form",
            "context_title": "Unknown Context",
            "description": "",
            "field_count": 0,
            "required_fields": 0
        }

    def handle_form_selection_response(self, session_id: str, user_input: str, available_forms: list) -> dict:
        """Handle user's response to form selection alternatives."""
        # Use the smart form selector to handle the response
        selection_result = smart_form_selector.handle_selection_response(session_id, user_input)

        if not selection_result:
            return {
                "error": "Não há seleção ativa para esta sessão.",
                "requires_clarification": True
            }

        if selection_result.get("success"):
            if selection_result.get("action") == "form_selected":
                # User successfully selected a form
                form_id = selection_result.get("form_id")
                form_details = self._get_form_details(form_id, available_forms)

                success_message = f"✅ Perfeito! Você escolheu o formulário **{selection_result.get('form_title')}**."
                if form_details.get('description'):
                    success_message += f"\n\n📄 {form_details['description']}"
                success_message += f"\n\n📊 Confiança: {selection_result.get('confidence', 0):.0%}"
                success_message += f"\n📝 {selection_result.get('reasoning', '')}"
                success_message += "\n\n➡️ Vamos começar a preencher!"

                return {
                    "form_template_id": form_id,
                    "confidence_score": selection_result.get("confidence", 0.7),
                    "reasoning": selection_result.get("reasoning", "Usuário selecionou manualmente"),
                    "requires_clarification": False,
                    "final_response": success_message,
                    "form_details": form_details
                }
            elif selection_result.get("action") == "rejected_all":
                # User rejected all options
                return {
                    "requires_clarification": True,
                    "clarification_message": selection_result.get("message"),
                    "selection_rejected": True
                }
        else:
            # Invalid or unclear selection
            return {
                "requires_clarification": True,
                "clarification_message": selection_result.get("message", "Seleção não compreendida. Tente novamente."),
                "invalid_selection": True
            }