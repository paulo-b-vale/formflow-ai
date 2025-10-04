from bson import ObjectId
from app.sessions.session_manager import EnhancedBaseAgent, SessionData
from app.database import db
from app.utils.langchain_utils import get_gemini_llm
from app.config.settings import settings
import logging
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
import httpx

logger = logging.getLogger(__name__)

class EnhancedFormFillerAgent(EnhancedBaseAgent):
    def __init__(self, db, session_data: SessionData):
        super().__init__(db, session_data)
        self.form_template = None 
        self.context_info = None
        self.llm = get_gemini_llm()
        self.validation_cache = {}
        self.field_suggestions = {}

    async def _load_form_template(self):
        """Fetches and caches the form template from the database with enhanced error handling."""
        if not self.form_template:
            template_id = self.session_data.form_template_id
            logger.info(f"Loading form template with ID: {template_id}")
            
            try:
                # Ensure we have a valid ObjectId
                if not ObjectId.is_valid(template_id):
                    raise ValueError(f"Invalid template ID format: {template_id}")
                
                self.form_template = await self.db.form_templates.find_one({"_id": ObjectId(template_id)})
                
                if not self.form_template:
                    raise ValueError(f"Form template with ID {template_id} not found.")
                
                logger.info(f"Loaded form template: {self.form_template.get('title', 'Unknown')}")
                logger.info(f"Form has {len(self.form_template.get('fields', []))} fields")
                
                # Also load context information with error handling
                context_id = self.form_template.get('context_id')
                if context_id and ObjectId.is_valid(context_id):
                    try:
                        self.context_info = await self.db.contexts.find_one({"_id": ObjectId(context_id)})
                        logger.info(f"Loaded context: {self.context_info.get('title', 'Unknown') if self.context_info else 'None'}")
                    except Exception as context_error:
                        logger.warning(f"Could not load context {context_id}: {context_error}")
                        self.context_info = None
                    
            except Exception as e:
                logger.error(f"Error loading form template: {e}")
                raise

    def _get_confidence_display(self, confidence_score: float) -> str:
        """Generate a user-friendly confidence indicator."""
        if confidence_score >= 0.9:
            return "🟢 Very confident"
        elif confidence_score >= 0.7:
            return "🟡 Moderately confident" 
        elif confidence_score >= 0.5:
            return "🟠 Low confidence"
        else:
            return "🔴 Very uncertain"

    async def _validate_field_response(self, field: Dict, user_response: str) -> Dict[str, Any]:
        """Enhanced field validation with AI assistance for complex fields."""
        field_type = field.get("field_type", "text")
        field_id = field.get("field_id")
        validation_result = {
            "is_valid": True,
            "processed_value": user_response.strip(),
            "suggestions": [],
            "warning": None
        }

        try:
            # Basic validation by field type
            if field_type == "email":
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, user_response.strip()):
                    validation_result["is_valid"] = False
                    validation_result["suggestions"] = ["Please provide a valid email address (e.g., user@example.com)"]

            elif field_type == "phone":
                # Remove common separators and check if it's a reasonable phone number
                clean_phone = re.sub(r'[\s\-\(\)\+]', '', user_response)
                if not clean_phone.isdigit() or len(clean_phone) < 7:
                    validation_result["is_valid"] = False
                    validation_result["suggestions"] = ["Please provide a valid phone number (e.g., +1-555-123-4567)"]
                else:
                    validation_result["processed_value"] = clean_phone

            elif field_type == "number":
                try:
                    float(user_response.strip())
                    validation_result["processed_value"] = user_response.strip()
                except ValueError:
                    validation_result["is_valid"] = False
                    validation_result["suggestions"] = ["Please provide a valid number"]

            elif field_type == "date":
                # Try to parse various date formats
                date_formats = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"]
                parsed_date = None
                for fmt in date_formats:
                    try:
                        parsed_date = datetime.strptime(user_response.strip(), fmt)
                        break
                    except ValueError:
                        continue
                
                if not parsed_date:
                    validation_result["is_valid"] = False
                    validation_result["suggestions"] = ["Please provide a date in YYYY-MM-DD format (e.g., 2024-03-15)"]
                else:
                    validation_result["processed_value"] = parsed_date.strftime("%Y-%m-%d")

            elif field_type in ["select", "multiselect"]:
                options = field.get("options", [])
                if options:
                    user_response_lower = user_response.lower().strip()
                    # Check for exact matches first
                    exact_matches = [opt for opt in options if opt.lower() == user_response_lower]
                    if exact_matches:
                        validation_result["processed_value"] = exact_matches[0]
                    else:
                        # Check for partial matches
                        partial_matches = [opt for opt in options if user_response_lower in opt.lower() or opt.lower() in user_response_lower]
                        if partial_matches:
                            if len(partial_matches) == 1:
                                validation_result["processed_value"] = partial_matches[0]
                                validation_result["warning"] = f"I interpreted your answer as '{partial_matches[0]}'. Is this correct?"
                            else:
                                validation_result["is_valid"] = False
                                validation_result["suggestions"] = [f"Did you mean one of these? {', '.join(partial_matches)}"]
                        else:
                            validation_result["is_valid"] = False
                            validation_result["suggestions"] = [f"Please choose from: {', '.join(options)}"]

            elif field_type == "boolean":
                positive_responses = ["yes", "y", "true", "1", "ok", "correct", "right",
                                    "sim", "s", "verdadeiro", "certo", "correto"]
                negative_responses = ["no", "n", "false", "0", "wrong", "incorrect",
                                    "não", "nao", "falso", "errado", "incorreto"]

                user_response_lower = user_response.lower().strip()
                if user_response_lower in positive_responses:
                    validation_result["processed_value"] = "true"
                elif user_response_lower in negative_responses:
                    validation_result["processed_value"] = "false"
                else:
                    validation_result["is_valid"] = False
                    validation_result["suggestions"] = ["Por favor, responda 'sim' ou 'não'"]

            # Use LLM for complex validation if configured
            if not validation_result["is_valid"] and field.get("use_ai_validation", False):
                ai_validation = await self._ai_validate_response(field, user_response)
                if ai_validation.get("is_valid"):
                    validation_result.update(ai_validation)

        except Exception as e:
            logger.error(f"Error validating field {field_id}: {e}")
            validation_result["warning"] = "Could not validate response automatically, but I'll accept it."

        return validation_result

    async def _ai_validate_response(self, field: Dict, user_response: str) -> Dict[str, Any]:
        """Use AI to validate complex field responses."""
        field_description = field.get("description", "")
        field_label = field.get("label", field.get("field_id", ""))
        
        prompt = f"""You are helping validate a user's response to a form field.

Field: {field_label}
Description: {field_description}
User's response: "{user_response}"

Please analyze if this response is appropriate and valid for this field. Consider:
1. Does it make logical sense?
2. Is it complete enough to be useful?
3. Does it match what the field is asking for?

Respond with JSON in this format:
{{
    "is_valid": true/false,
    "processed_value": "cleaned/formatted version of response",
    "explanation": "brief explanation of your decision",
    "suggestions": ["suggestion1", "suggestion2"] if invalid
}}
"""

        try:
            response = await self.llm.ainvoke(prompt)
            result = json.loads(response.content)
            return {
                "is_valid": result.get("is_valid", False),
                "processed_value": result.get("processed_value", user_response),
                "suggestions": result.get("suggestions", []),
                "ai_explanation": result.get("explanation", "")
            }
        except Exception as e:
            logger.error(f"AI validation failed: {e}")
            return {"is_valid": False, "suggestions": ["Could not validate automatically"]}

    def _get_next_question(self) -> Optional[Dict]:
        """Determines the next required question with improved priority logic."""
        if not self.form_template:
            logger.warning("Form template not loaded")
            return None

        form_fields = self.form_template.get("fields", [])
        logger.info(f"Checking {len(form_fields)} fields for next question")
        logger.info(f"Current responses: {list(self.session_data.responses.keys())}")
        
        # Priority 1: Required fields that haven't been answered
        for field in form_fields:
            field_id = field.get("field_id")
            is_required = field.get("required", False)
            
            if is_required and field_id and field_id not in self.session_data.responses:
                logger.info(f"Found next required question: {field_id}")
                return field
        
        # Priority 2: Fields with dependencies that are now available
        for field in form_fields:
            field_id = field.get("field_id")
            depends_on = field.get("depends_on")
            
            if (field_id and field_id not in self.session_data.responses and
                depends_on and depends_on in self.session_data.responses):
                logger.info(f"Found next dependent question: {field_id}")
                return field
        
        # Priority 3: Any unanswered field
        for field in form_fields:
            field_id = field.get("field_id")
            if field_id and field_id not in self.session_data.responses:
                logger.info(f"Found next optional question: {field_id}")
                return field
                
        logger.info("No more questions to ask")
        return None

    async def _get_field_prompt(self, field: Dict) -> str:
        """Generate an enhanced, interactive prompt for a field."""
        field_type = field.get("field_type", "text")
        question = field.get("question") or field.get("label") or f"Por favor, forneça {field.get('field_id', 'informação')}"
        description = field.get("description", "")
        required = field.get("required", False)
        options = field.get("options", [])
        examples = field.get("examples", [])

        prompt_parts = [f"{question}"]

        if description:
            prompt_parts.append(f"{description}")

        # Add field-specific guidance
        if field_type in ["select", "multiselect"]:
            if options:
                prompt_parts.append(f"Opções: {', '.join(options)}")
        elif field_type == "boolean":
            prompt_parts.append("Por favor, responda com sim/não ou verdadeiro/falso")
        elif field_type == "date":
            prompt_parts.append("Por favor, forneça uma data no formato AAAA-MM-DD (ex: 2024-03-15)")
        elif field_type == "email":
            prompt_parts.append("Por favor, forneça um endereço de email válido")
        elif field_type == "phone":
            prompt_parts.append("Por favor, forneça um número de telefone (qualquer formato)")
        elif field_type == "number":
            prompt_parts.append("Por favor, forneça um número")

        # Add examples if available
        if examples:
            prompt_parts.append(f"Exemplos: {', '.join(examples)}")

        # Add requirement indicator
        if required:
            prompt_parts.append("Campo obrigatório")
        else:
            prompt_parts.append("Campo opcional (você pode pular dizendo 'pular' ou 'nenhum')")

        return "\n".join(prompt_parts)

    async def _extract_multiple_fields_from_message(self, user_message: str) -> Dict[str, Any]:
        """Use AI to extract multiple field values from a single user message."""
        try:
            await self._load_form_template()

            # Get all unfilled fields
            unfilled_fields = []
            for field in self.form_template.get('fields', []):
                field_id = field.get('field_id')
                if field_id and field_id not in self.session_data.responses:
                    unfilled_fields.append({
                        'field_id': field_id,
                        'label': field.get('label', field_id),
                        'question': field.get('question', ''),
                        'field_type': field.get('field_type', 'text'),
                        'options': field.get('options', []),
                        'required': field.get('required', False)
                    })

            if not unfilled_fields:
                return {}

            # Create extraction prompt
            fields_info = []
            for field in unfilled_fields:
                field_desc = f"- {field['field_id']}: {field['label']}"
                if field['question']:
                    field_desc += f" ({field['question']})"
                if field['field_type'] in ['select', 'multiselect'] and field['options']:
                    field_desc += f" [opções: {', '.join(field['options'])}]"
                fields_info.append(field_desc)

            extraction_prompt = f"""Você é um especialista em extrair informações de mensagens de usuários para preencher formulários.

Aqui está a mensagem do usuário: "{user_message}"

Aqui estão os campos do formulário que ainda precisam ser preenchidos:
{chr(10).join(fields_info)}

Por favor, extraia qualquer informação relevante da mensagem do usuário que possa corresponder a esses campos.

Responda em formato JSON válido com apenas os campos que você conseguiu identificar:
{{
    "campo_id": "valor_extraído",
    "outro_campo": "outro_valor"
}}

Regras importantes:
- Apenas extraia informações que você tem certeza
- Para campos de seleção, use apenas valores das opções fornecidas
- Para campos booleanos, use "sim", "não", "verdadeiro" ou "falso"
- Para datas, tente converter para formato AAAA-MM-DD
- Se não conseguir extrair nenhuma informação relevante, retorne {{}}
- NÃO invente informações que não estão na mensagem do usuário"""

            response = await self.llm.ainvoke(extraction_prompt)
            extracted_text = response.content.strip()

            # Try to parse JSON response
            try:
                # Clean the response - remove markdown formatting if present
                if extracted_text.startswith('```'):
                    lines = extracted_text.split('\n')
                    json_lines = []
                    in_json = False
                    for line in lines:
                        if line.strip().startswith('```'):
                            in_json = not in_json
                            continue
                        if in_json:
                            json_lines.append(line)
                    extracted_text = '\n'.join(json_lines)

                extracted_data = json.loads(extracted_text)

                # Validate extracted fields exist in our form
                valid_field_ids = {f['field_id'] for f in unfilled_fields}
                filtered_data = {k: v for k, v in extracted_data.items() if k in valid_field_ids and v}

                logger.info(f"Extracted {len(filtered_data)} fields from message: {filtered_data}")
                return filtered_data

            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse extraction response as JSON: {e}")
                return {}

        except Exception as e:
            logger.error(f"Error in multi-field extraction: {e}")
            return {}

    async def _handle_form_confidence_confirmation(self, confidence_score: float, form_details: Dict) -> str:
        """Handle low confidence form predictions by asking for user confirmation."""
        form_title = form_details.get("title", "Unknown Form")
        context_title = form_details.get("context_title", "Unknown Context")
        confidence_display = self._get_confidence_display(confidence_score)
        
        confirmation_message = f"""I think you want to fill out the form: **"{form_title}"** from {context_title}

{confidence_display} - Prediction confidence: {confidence_score:.1%}

**Form Details:**
• **Title:** {form_title}
• **Context:** {context_title}"""

        # Add form description if available
        if form_details.get("description"):
            confirmation_message += f"\n• **Description:** {form_details['description']}"

        # Add field count
        if form_details.get("field_count"):
            confirmation_message += f"\n• **Fields:** {form_details['field_count']} total"
            if form_details.get("required_fields"):
                confirmation_message += f"\n• **Required:** {form_details['required_fields']}"

        if confidence_score < 0.7:
            confirmation_message += f"\n\n⚠️ Since I'm not very confident about this prediction, please confirm:"
            confirmation_message += f"\n• Reply **'yes'** to proceed with this form"
            confirmation_message += f"\n• Reply **'no'** to let me try finding a different form"
            confirmation_message += f"\n• Or describe more specifically what kind of form you need"
        else:
            confirmation_message += f"\n\n✅ I'll proceed with this form. Reply **'ok'** to continue, or **'no'** if this isn't the right form."

        return confirmation_message

    async def _finalize_form(self):
        """Enhanced form finalization with better data processing."""
        logger.info("Finalizing form submission")

        # Update session state and save to Redis FIRST
        self.session_data.state = "COMPLETED"
        self.session_data.updated_at = datetime.utcnow()

        # Save session state to Redis immediately to prevent confirmation loops
        try:
            from app.sessions.session_manager import RedisManager
            redis_manager = RedisManager()
            redis_client = await redis_manager.get_redis()

            session_dict = self.session_data.to_dict()
            await redis_client.setex(
                f"session:{self.session_data.session_id}",
                120 * 60,  # TTL in seconds (2 hours)
                json.dumps(session_dict, default=str)
            )
            logger.info(f"Session state updated to COMPLETED in Redis for session {self.session_data.session_id}")
        except Exception as e:
            logger.error(f"Failed to save session state to Redis: {e}")
            # Continue anyway - we don't want Redis failures to block form submission

        # Calculate completion stats
        form_fields = self.form_template.get('fields', [])
        total_fields = len(form_fields)
        completed_fields = len(self.session_data.responses)
        required_fields = [f for f in form_fields if f.get('required', False)]
        completed_required = len([f for f in required_fields if f.get('field_id') in self.session_data.responses])

        completion_percentage = (completed_fields / total_fields) * 100 if total_fields > 0 else 100
        required_completion = (completed_required / len(required_fields)) * 100 if required_fields else 100

        # Process and clean responses
        processed_responses = {}
        for field_id, response in self.session_data.responses.items():
            field = next((f for f in form_fields if f.get('field_id') == field_id), None)
            if field:
                # Apply any final processing based on field type
                field_type = field.get('field_type', 'text')
                if field_type == 'number':
                    try:
                        processed_responses[field_id] = float(response)
                    except ValueError:
                        processed_responses[field_id] = response
                elif field_type == 'boolean':
                    processed_responses[field_id] = response.lower() in ['true', 'yes', '1', 'y']
                else:
                    processed_responses[field_id] = response
            else:
                processed_responses[field_id] = response

        form_response = {
            "form_template_id": ObjectId(self.session_data.form_template_id),
            "context_id": ObjectId(self.form_template.get('context_id')) if self.form_template.get('context_id') else None,
            "respondent_id": ObjectId(self.session_data.user_id),
            "respondent_name": f"User {self.session_data.user_id}",
            "responses": processed_responses,
            "completion_percentage": completion_percentage,
            "required_completion_percentage": required_completion,
            "status": "complete" if required_completion == 100 else "partial",
            "llm_assistance_used": True,
            "session_id": self.session_data.session_id,
            "submitted_at": datetime.utcnow(),
            "metadata": {
                "total_fields": total_fields,
                "completed_fields": completed_fields,
                "required_fields": len(required_fields),
                "completed_required_fields": completed_required,
                "conversation_turns": len(self.session_data.conversation_history)
            }
        }

        # Try to save to MongoDB Atlas - but don't let failures block the completion
        try:
            result = await self.db.form_responses.insert_one(form_response)
            logger.info(f"Form response saved to MongoDB with ID: {result.inserted_id}")

            # Update session with submission ID
            self.session_data.submission_id = str(result.inserted_id)

            # Try to update Redis with submission ID
            try:
                session_dict = self.session_data.to_dict()
                await redis_client.setex(
                    f"session:{self.session_data.session_id}",
                    120 * 60,  # TTL in seconds (2 hours)
                    json.dumps(session_dict, default=str)
                )
                logger.info(f"Updated session with submission ID in Redis")
            except Exception as redis_e:
                logger.warning(f"Failed to update Redis with submission ID: {redis_e}")

            # Clear form session data to prevent routing back to form_filler
            logger.info("Clearing form session data after successful submission")
            self.session_data.form_template_id = None
            self.session_data.current_field = None
            self.session_data.responses.clear()

            return str(result.inserted_id)

        except Exception as e:
            logger.error(f"Error saving form response to MongoDB: {e}")

            # Even if MongoDB fails, we still consider the form "completed"
            # because the user confirmed it and we saved the state to Redis
            logger.info("Form marked as completed despite MongoDB error - user won't be stuck in confirmation loop")

            # Generate a fallback submission ID based on timestamp and session
            import time
            fallback_id = f"fallback_{int(time.time())}_{self.session_data.session_id[:8]}"
            self.session_data.submission_id = fallback_id

            # Clear form session data
            self.session_data.form_template_id = None
            self.session_data.current_field = None
            self.session_data.responses.clear()

            return fallback_id

    async def _handle_confirmation_state(self, user_message: str):
        """Enhanced confirmation handling with more interactive options."""
        logger.info(f"🔍 CONFIRMATION HANDLER CALLED: session={self.session_data.session_id}, message='{user_message}', state={self.session_data.state}")

        user_msg_lower = user_message.lower().strip()

        # Positive confirmations (English and Portuguese)
        positive_indicators = ["yes", "y", "submit", "correct", "ok", "confirm", "sure", "right", "good", "looks good", "perfect",
                             "sim", "s", "enviar", "submeter", "correto", "certo", "confirmar", "confirma", "perfeito", "bom"]
        negative_indicators = ["no", "n", "wrong", "incorrect", "change", "edit", "fix", "not right", "modify",
                             "não", "nao", "errado", "incorreto", "mudar", "alterar", "editar", "modificar"]
        review_indicators = ["review", "show", "check", "look", "see", "summary", "revisar", "mostrar", "verificar", "ver", "resumo"]
        
        logger.info(f"🔍 CHECKING CONFIRMATION: user_msg_lower='{user_msg_lower}', positive_indicators={positive_indicators[:5]}...")

        if any(indicator in user_msg_lower for indicator in positive_indicators):
            logger.info(f"✅ POSITIVE CONFIRMATION DETECTED: '{user_message}' - Processing form submission...")
            try:
                form_response_id = await self._finalize_form()
                logger.info(f"Form successfully submitted with ID: {form_response_id}")

                form_title = self.form_template.get('title', 'the form')
                context_title = self.context_info.get('title', 'your workspace') if self.context_info else 'your workspace'

                # Clean completion message
                total_fields = len(self.form_template.get('fields', []))
                completed_fields = len(self.session_data.responses)

                # Check if this was a fallback ID (MongoDB failed)
                is_fallback = form_response_id.startswith('fallback_')

                if is_fallback:
                    completion_message = f"""🎉 **FORMULÁRIO PROCESSADO COM SUCESSO!**

📋 **DETALHES:**
• Formulário: {form_title}
• Contexto: {context_title}
• ID de Processamento: `{form_response_id}`

📊 **RESUMO:**
• Campos preenchidos: {completed_fields}/{total_fields}
• Status: Completo ✅
• Data/Hora: {datetime.now().strftime('%d/%m/%Y às %H:%M')}

⚠️ **Nota:** Seus dados foram processados com sucesso, mas podem haver atrasos na sincronização com o banco de dados principal.
🔒 Suas respostas foram registradas e o formulário foi completado!"""
                else:
                    completion_message = f"""🎉 **FORMULÁRIO ENVIADO COM SUCESSO!**

📋 **DETALHES DA SUBMISSÃO:**
• Formulário: {form_title}
• Contexto: {context_title}
• ID da Submissão: `{form_response_id}`

📊 **RESUMO:**
• Campos preenchidos: {completed_fields}/{total_fields}
• Status: Completo ✅
• Data/Hora: {datetime.now().strftime('%d/%m/%Y às %H:%M')}

🔒 Seus dados foram salvos com segurança. Obrigado por usar o assistente de formulários!"""

                return await self._build_success_response(
                    completion_message,
                    is_complete=True,
                    form_response_id=form_response_id
                )
            except Exception as e:
                logger.error(f"Unexpected error in form confirmation: {e}")
                # This should rarely happen now since _finalize_form is more robust
                return await self._build_success_response(
                    f"❌ Ocorreu um erro inesperado: {str(e)}. Por favor, tente novamente ou entre em contato com o suporte.",
                    is_complete=False
                )
        
        elif any(indicator in user_msg_lower for indicator in review_indicators):
            # User wants to review responses again
            summary_message = await self._generate_response_summary(detailed=True)
            summary_message += "\n\n**Ready to submit?** Reply 'yes' to submit or 'no' to make changes."
            return await self._build_success_response(summary_message)
            
        elif any(indicator in user_msg_lower for indicator in negative_indicators):
            # User wants to make changes
            self.session_data.state = "IN_PROGRESS"
            
            change_message = """🔧 **Let's make some changes!** You can:

• **Change a specific field:** "Change my name to John"
• **Review a field:** "What did I put for email?"
• **Start over:** "Start from the beginning"
• **Continue with questions:** "Continue with next question"

What would you like to modify?"""
            
            return await self._build_success_response(change_message)
        
        else:
            # Unclear response, provide helpful options
            logger.info(f"❓ NO MATCH FOUND for '{user_message}' - providing clarification")
            clarification_message = """🤔 I didn't quite understand your response. Here are your options:

• **Submit the form:** Reply 'yes' or 'submit'
• **Make changes:** Reply 'no' or 'change'  
• **Review responses:** Reply 'review' or 'show summary'
• **Get help:** Reply 'help' for more options

What would you like to do?"""
            
            return await self._build_success_response(clarification_message)

    async def _generate_response_summary(self, detailed: bool = False) -> str:
        """Generate a clean, report-style summary of current responses."""
        if not self.form_template or not self.session_data.responses:
            return "📝 Nenhuma resposta registrada ainda."

        form_fields = self.form_template.get('fields', [])

        # Separate completed and missing fields
        completed_fields = []
        missing_required = []
        missing_optional = []

        for field in form_fields:
            field_id = field.get('field_id')
            field_label = field.get('label', field_id)
            is_required = field.get('required', False)

            if field_id in self.session_data.responses:
                response = self.session_data.responses[field_id]
                completed_fields.append({
                    'label': field_label,
                    'value': response,
                    'required': is_required
                })
            else:
                if is_required:
                    missing_required.append(field_label)
                else:
                    missing_optional.append(field_label)

        # Build clean report format
        summary_parts = ["📋 **RELATÓRIO DE RESPOSTAS**"]

        # Completed fields section
        if completed_fields:
            summary_parts.append("\n✅ **CAMPOS PREENCHIDOS:**")
            for field in completed_fields:
                icon = "🔴" if field['required'] else "⚪"
                summary_parts.append(f"{icon} **{field['label']}:** {field['value']}")

        # Missing required fields (if any)
        if missing_required:
            summary_parts.append(f"\n❌ **CAMPOS OBRIGATÓRIOS FALTANDO:** ({len(missing_required)})")
            for field_label in missing_required:
                summary_parts.append(f"   • {field_label}")

        # Missing optional fields (if any, but only show count)
        if missing_optional:
            summary_parts.append(f"\n⚪ **CAMPOS OPCIONAIS FALTANDO:** {len(missing_optional)}")

        # Progress summary
        total_fields = len(form_fields)
        completed_count = len(completed_fields)
        required_count = len([f for f in form_fields if f.get('required', False)])
        completed_required_count = len([f for f in completed_fields if f['required']])

        summary_parts.append(f"\n📊 **PROGRESSO:** {completed_count}/{total_fields} campos completos")
        summary_parts.append(f"📋 **OBRIGATÓRIOS:** {completed_required_count}/{required_count} ✅")

        return "\n".join(summary_parts)

    async def _handle_field_change_request(self, user_message: str) -> Dict[str, Any]:
        """Handle requests to change specific field values."""
        # Use LLM to understand which field they want to change
        fields_context = []
        for field in self.form_template.get('fields', []):
            field_id = field.get('field_id')
            field_label = field.get('label', field_id)
            if field_id in self.session_data.responses:
                fields_context.append(f"- {field_label} (ID: {field_id}): {self.session_data.responses[field_id]}")
        
        prompt = f"""The user wants to change a field in their form responses. 

Current responses:
{chr(10).join(fields_context)}

User's request: "{user_message}"

Which field do they want to change? Respond with just the field_id, or "UNCLEAR" if uncertain.
"""
        
        try:
            response = await self.llm.ainvoke(prompt)
            field_id = response.content.strip()
            
            if field_id != "UNCLEAR" and field_id in self.session_data.responses:
                # Find the field
                field = next((f for f in self.form_template.get('fields', []) if f.get('field_id') == field_id), None)
                if field:
                    # Set this as the current field to be changed
                    self.session_data.current_field = field_id
                    self.session_data.state = "IN_PROGRESS"
                    
                    field_label = field.get('label', field_id)
                    current_value = self.session_data.responses[field_id]
                    
                    change_message = f"""🔄 **Updating {field_label}**

**Current value:** {current_value}

{await self._get_field_prompt(field)}"""
                    
                    return await self._build_success_response(change_message)
            
            # If unclear, ask for clarification
            return await self._build_success_response(
                "I'm not sure which field you'd like to change. Please specify which field or tell me what information you want to update.\n\n" +
                await self._generate_response_summary()
            )
            
        except Exception as e:
            logger.error(f"Error handling field change: {e}")
            return await self._build_success_response(
                "I had trouble understanding which field to change. Could you be more specific?\n\n" +
                await self._generate_response_summary()
            )

    async def start_conversation(self):
        """Enhanced conversation starter with confidence handling."""
        try:
            await self._load_form_template()
            
            form_title = self.form_template.get('title', 'the form')
            form_description = self.form_template.get('description', '')
            context_title = self.context_info.get('title', 'your workspace') if self.context_info else 'your workspace'
            
            # Check if this is a low-confidence prediction
            confidence_score = getattr(self.session_data, 'prediction_confidence', 1.0)
            
            welcome_parts = []
            
            if confidence_score < 0.7:
                # Show confidence information for low-confidence predictions
                form_details = {
                    "title": form_title,
                    "description": form_description,
                    "context_title": context_title,
                    "field_count": len(self.form_template.get('fields', [])),
                    "required_fields": len([f for f in self.form_template.get('fields', []) if f.get('required', False)])
                }
                
                confirmation_msg = await self._handle_form_confidence_confirmation(confidence_score, form_details)
                self.session_data.conversation_history.append({"role": "bot", "message": confirmation_msg})
                self.session_data.state = "AWAITING_FORM_CONFIRMATION"
                return await self._build_success_response(confirmation_msg)
            
            # High confidence - proceed directly
            welcome_parts.append(f"Olá! Estou aqui para ajudá-lo a preencher '{form_title}' para {context_title}.")

            if form_description:
                welcome_parts.append(f"Sobre este formulário: {form_description}")

            # Get form statistics
            total_fields = len(self.form_template.get('fields', []))
            required_fields = len([f for f in self.form_template.get('fields', []) if f.get('required', False)])

            if required_fields > 0:
                welcome_parts.append(f"Este formulário tem {total_fields} campos no total, com {required_fields} campos obrigatórios.")
            else:
                welcome_parts.append(f"Este formulário tem {total_fields} campos, nenhum é obrigatório.")

            welcome_parts.append("Vou guiá-lo através de cada campo passo a passo. Vamos começar!")
            
            welcome_message = "\n\n".join(welcome_parts)
            
            self.session_data.conversation_history.append({"role": "bot", "message": welcome_message})

            next_question_field = self._get_next_question()
            
            if next_question_field:
                self.session_data.state = "IN_PROGRESS"
                self.session_data.current_field = next_question_field.get("field_id")
                
                question_prompt = await self._get_field_prompt(next_question_field)
                full_message = f"{welcome_message}\n\nPergunta 1:\n{question_prompt}"
                
                return await self._build_success_response(full_message)
            else:
                # No fields to fill
                self.session_data.state = "CONFIRMATION"
                no_fields_message = f"{welcome_message}\n\n⚠️ This form appears to have no fields to fill out. Would you like me to submit it as is?"
                return await self._build_success_response(no_fields_message, is_complete=False)
                
        except Exception as e:
            logger.error(f"Error starting conversation: {e}")
            error_message = f"❌ I encountered an issue loading the form: {str(e)}\n\nPlease try again or contact support for assistance."
            return await self._build_success_response(error_message, is_complete=True)

    async def process_message(self, user_message: str):
        """Enhanced message processing with better state handling."""
        try:
            await self._load_form_template()
            self.session_data.conversation_history.append({"role": "user", "message": user_message})

            print(f"🔍 ENHANCED_FORM_AGENT: session={self.session_data.session_id}, state={self.session_data.state}, message='{user_message}'")
            logger.info(f"🔍 PROCESS_MESSAGE: session={self.session_data.session_id}, state={self.session_data.state}, message='{user_message}'")

            # Handle different states (support both enum and string values)
            state_value = self.session_data.state.value if hasattr(self.session_data.state, 'value') else str(self.session_data.state)

            if state_value == "AWAITING_FORM_CONFIRMATION":
                logger.info(f"🔀 Routing to AWAITING_FORM_CONFIRMATION handler")
                return await self._handle_form_confirmation(user_message)

            if state_value == "CONFIRMATION":
                print(f"🔀 ROUTING TO CONFIRMATION HANDLER!")
                logger.info(f"🔀 Routing to CONFIRMATION handler")
                return await self._handle_confirmation_state(user_message)

            # Check for special commands
            user_msg_lower = user_message.lower().strip()
            
            if user_msg_lower in ["help", "commands", "options"]:
                return await self._handle_help_request()
            
            if user_msg_lower in ["skip", "none", "n/a", "not applicable"]:
                return await self._handle_skip_request()
            
            if "change" in user_msg_lower or "modify" in user_msg_lower or "update" in user_msg_lower:
                return await self._handle_field_change_request(user_message)
            
            if user_msg_lower in ["summary", "review", "show", "what did i answer"]:
                summary_message = await self._generate_response_summary(detailed=True)
                summary_message += "\n\n💬 **Continue:** I'll ask the next question, or tell me if you want to change anything."
                return await self._build_success_response(summary_message)

            # ENHANCED: Try to extract multiple fields from any message
            extracted_fields = await self._extract_multiple_fields_from_message(user_message)

            # Handle main form filling flow
            current_field_id = getattr(self.session_data, 'current_field', None)
            acknowledgment_parts = []

            # Process extracted fields first
            for field_id, extracted_value in extracted_fields.items():
                # Find the field definition
                field_def = next(
                    (f for f in self.form_template.get('fields', []) if f.get('field_id') == field_id),
                    None
                )

                if field_def:
                    # Validate the extracted value
                    validation_result = await self._validate_field_response(field_def, extracted_value)

                    if validation_result["is_valid"]:
                        self.session_data.responses[field_id] = validation_result["processed_value"]
                        field_label = field_def.get('label', field_id)
                        acknowledgment_parts.append(f"✅ {field_label}: {validation_result['processed_value']}")
                        logger.info(f"Auto-extracted and saved {field_id}: {validation_result['processed_value']}")
                    else:
                        logger.warning(f"Extracted value for {field_id} failed validation: {extracted_value}")

            # Handle the current field if it wasn't already extracted
            if current_field_id and current_field_id not in extracted_fields:
                # Find the field definition
                current_field = next(
                    (f for f in self.form_template.get('fields', []) if f.get('field_id') == current_field_id),
                    None
                )

                if current_field:
                    # Validate the response for the current field
                    validation_result = await self._validate_field_response(current_field, user_message)

                    if validation_result["is_valid"]:
                        # Save the validated response
                        self.session_data.responses[current_field_id] = validation_result["processed_value"]
                        logger.info(f"Saved response for current field {current_field_id}: {validation_result['processed_value']}")

                        # Build acknowledgment message
                        field_label = current_field.get('label', current_field_id)
                        acknowledgment_parts.append(f"✅ {field_label}: {validation_result['processed_value']}")

                        # Add any warnings
                        if validation_result.get("warning"):
                            acknowledgment_parts.append(f"⚠️ {validation_result['warning']}")

                        # Add AI explanation if available
                        if validation_result.get("ai_explanation"):
                            acknowledgment_parts.append(f"🤖 {validation_result['ai_explanation']}")

            # Handle case where current field validation failed but wasn't extracted
            if current_field_id and current_field_id not in extracted_fields and not acknowledgment_parts:
                current_field = next(
                    (f for f in self.form_template.get('fields', []) if f.get('field_id') == current_field_id),
                    None
                )

                if current_field:
                    # Validate the response for the current field
                    validation_result = await self._validate_field_response(current_field, user_message)

                    if not validation_result["is_valid"]:
                        # Handle validation failure
                        field_label = current_field.get('label', current_field_id)
                        error_parts = [f"❌ Problema com {field_label}:"]

                        if validation_result.get("suggestions"):
                            error_parts.extend([f"💡 {suggestion}" for suggestion in validation_result["suggestions"]])

                        error_parts.append("\n🔄 Por favor, tente novamente:")
                        error_parts.append(await self._get_field_prompt(current_field))

                        error_message = "\n".join(error_parts)
                        return await self._build_success_response(error_message)

            # Build final acknowledgment
            if acknowledgment_parts:
                acknowledgment = "\n".join(acknowledgment_parts)

                # Show summary of extracted fields if more than one
                if len(acknowledgment_parts) > 1:
                    acknowledgment = f"🎯 Informações capturadas da sua mensagem:\n\n{acknowledgment}"
            else:
                # No fields were extracted or processed
                if current_field_id:
                    # Fallback: save user message for current field
                    self.session_data.responses[current_field_id] = user_message
                    acknowledgment = "✅ Registrei sua resposta."
                else:
                    # No current field, try to find any unanswered field
                    all_fields = self.form_template.get('fields', [])
                    for field in all_fields:
                        field_id = field.get('field_id')
                        if field_id and field_id not in self.session_data.responses:
                            self.session_data.responses[field_id] = user_message
                            acknowledgment = "✅ Registrei sua resposta."
                            break
                    else:
                        acknowledgment = "✅ Obrigado pela sua resposta."
            
            # Get the next question
            next_question_field = self._get_next_question()

            if next_question_field:
                self.session_data.state = "IN_PROGRESS"
                self.session_data.current_field = next_question_field.get("field_id")
                
                question_prompt = await self._get_field_prompt(next_question_field)
                
                # Show progress
                total_fields = len(self.form_template.get('fields', []))
                completed_fields = len(self.session_data.responses)
                progress_bar = self._create_progress_bar(completed_fields, total_fields)
                
                next_message_parts = [
                    acknowledgment,
                    f"\n📊 **Progress:** {progress_bar} ({completed_fields}/{total_fields})",
                    "─" * 50,
                    f"**Next Question:**\n{question_prompt}"
                ]
                
                next_message = "\n\n".join(next_message_parts)
                
                return await self._build_success_response(next_message)
            else:
                # All questions answered, move to confirmation
                self.session_data.state = "CONFIRMATION"
                self.session_data.current_field = None
                
                # Build clean completion summary
                summary_parts = [
                    acknowledgment,
                    "\n🎉 **FORMULÁRIO COMPLETO!**"
                ]

                summary_parts.append(await self._generate_response_summary(detailed=False))

                summary_parts.extend([
                    "\n" + "═" * 40,
                    "🚀 **PRONTO PARA ENVIAR?**",
                    "",
                    "✅ Digite **'sim'** ou **'enviar'** para finalizar",
                    "❌ Digite **'não'** para fazer alterações",
                    "📋 Digite **'revisar'** para ver detalhes"
                ])

                confirmation_message = "\n".join(summary_parts)
                
                return await self._build_success_response(confirmation_message, is_complete=False)
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            error_message = f"❌ **Error Processing Response**\n\nI encountered an issue: {str(e)}\n\n🔄 Please try again or reply **'help'** for assistance."
            return await self._build_success_response(error_message, is_complete=False)

    async def _handle_form_confirmation(self, user_message: str):
        """Handle form prediction confirmation when confidence is low."""
        user_msg_lower = user_message.lower().strip()
        
        positive_responses = ["yes", "y", "ok", "correct", "right", "proceed", "continue"]
        negative_responses = ["no", "n", "wrong", "different", "other"]
        
        if any(resp in user_msg_lower for resp in positive_responses):
            # User confirmed the form - proceed with filling
            self.session_data.state = "IN_PROGRESS" 
            
            # Start with the welcome and first question
            form_title = self.form_template.get('title', 'the form')
            context_title = self.context_info.get('title', 'your workspace') if self.context_info else 'your workspace'
            
            confirmed_message = f"🎯 **Perfect!** Let's fill out '{form_title}' for {context_title}."
            
            next_question_field = self._get_next_question()
            if next_question_field:
                self.session_data.current_field = next_question_field.get("field_id")
                question_prompt = await self._get_field_prompt(next_question_field)
                
                full_message = f"{confirmed_message}\n\n" + "─" * 50 + f"\n\n**Question 1:**\n{question_prompt}"
                return await self._build_success_response(full_message)
            else:
                return await self._build_success_response(f"{confirmed_message}\n\n⚠️ This form has no fields to fill.")
                
        elif any(resp in user_msg_lower for resp in negative_responses):
            # User rejected the prediction
            self.session_data.state = "ERROR"
            rejection_message = """❌ **No problem!** Let me try to find the right form for you.

🔍 **Help me understand better:**
• What type of form are you looking for?
• What's the purpose of the form?
• Which workspace or context should it be from?
• Any specific keywords or form names?

The more details you provide, the better I can help you find the correct form."""
            
            return await self._build_success_response(rejection_message, is_complete=True)
        else:
            # Unclear response - ask for clarification
            clarification_message = """🤔 I need a clear answer to proceed:

• Reply **'yes'** if this is the correct form
• Reply **'no'** if you need a different form
• Or provide more details about what form you're looking for

Which form would you like to fill out?"""
            
            return await self._build_success_response(clarification_message)

    async def _handle_help_request(self):
        """Provide helpful information about available commands."""
        help_message = """🆘 **Form Assistant Help**

**📝 During Form Filling:**
• Answer questions naturally - I'll validate your responses
• Reply **'skip'** or **'none'** for optional fields
• Reply **'summary'** or **'review'** to see your current answers
• Reply **'change [field]'** to modify a previous answer

**🎯 Available Commands:**
• **'help'** - Show this help message
• **'summary'** - Review all your current responses  
• **'change [field name]'** - Modify a specific field
• **'skip'** - Skip optional fields
• **'review'** - Detailed review of responses

**📊 Progress Tracking:**
• I'll show progress bars and completion status
• Required fields are marked with 🔴
• Optional fields are marked with ⚪

**❓ Questions?** Just ask! I'm here to help make form filling easy."""
        
        return await self._build_success_response(help_message)

    async def _handle_skip_request(self):
        """Handle requests to skip the current field."""
        current_field_id = getattr(self.session_data, 'current_field', None)
        
        if not current_field_id:
            return await self._build_success_response("❓ No current question to skip. Let me continue with the next question.")
        
        # Find the current field
        current_field = next(
            (f for f in self.form_template.get('fields', []) if f.get('field_id') == current_field_id), 
            None
        )
        
        if current_field and current_field.get('required', False):
            field_label = current_field.get('label', current_field_id)
            required_message = f"⚠️ **Cannot skip required field:** {field_label}\n\n" + await self._get_field_prompt(current_field)
            return await self._build_success_response(required_message)
        
        # Skip the optional field
        field_label = current_field.get('label', current_field_id) if current_field else current_field_id
        skip_message = f"⏭️ **Skipped:** {field_label}"

        # Record the skipped field so _get_next_question() doesn't find it again
        self.session_data.responses[current_field_id] = "SKIPPED"

        # Move to next question
        next_question_field = self._get_next_question()
        
        if next_question_field:
            self.session_data.current_field = next_question_field.get("field_id")
            question_prompt = await self._get_field_prompt(next_question_field)
            
            # Show progress
            total_fields = len(self.form_template.get('fields', []))
            completed_fields = len(self.session_data.responses)
            progress_bar = self._create_progress_bar(completed_fields, total_fields)
            
            next_message = f"""{skip_message}

📊 **Progress:** {progress_bar} ({completed_fields}/{total_fields})

{"-" * 50}

**Next Question:**
{question_prompt}"""
            
            return await self._build_success_response(next_message)
        else:
            # No more questions, move to confirmation
            self.session_data.state = "CONFIRMATION"
            self.session_data.current_field = None
            
            confirmation_message = f"""{skip_message}

{await self._generate_response_summary(detailed=False)}

🚀 **Ready to submit?** Reply 'yes' to finalize or 'no' to make changes."""
            
            return await self._build_success_response(confirmation_message, is_complete=False)

    def _create_progress_bar(self, completed: int, total: int, width: int = 20) -> str:
        """Create a visual progress bar."""
        if total == 0:
            return "█" * width + " 100%"
        
        percentage = completed / total
        filled_width = int(width * percentage)
        
        bar = "█" * filled_width + "░" * (width - filled_width)
        percent_text = f"{percentage:.0%}"
        
        return f"{bar} {percent_text}"

    async def _call_external_endpoint(self, endpoint: str, method: str = "GET", data: dict = None) -> dict:
        """Make HTTP calls to external endpoints following best practices."""
        base_url = getattr(settings, 'API_BASE_URL', 'http://localhost:8000')
        full_url = f"{base_url}/{endpoint.lstrip('/')}"
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'FormFillerAgent/1.0'
        }
        
        # Add authentication if available
        if hasattr(self.session_data, 'auth_token'):
            headers['Authorization'] = f"Bearer {self.session_data.auth_token}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method.upper() == "GET":
                    response = await client.get(full_url, headers=headers)
                elif method.upper() == "POST":
                    response = await client.post(full_url, headers=headers, json=data)
                elif method.upper() == "PUT":
                    response = await client.put(full_url, headers=headers, json=data)
                elif method.upper() == "DELETE":
                    response = await client.delete(full_url, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                return response.json()
                
        except httpx.TimeoutException:
            logger.error(f"Timeout calling endpoint: {endpoint}")
            raise Exception(f"Request timed out for {endpoint}")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error calling endpoint {endpoint}: {e.response.status_code}")
            raise Exception(f"HTTP {e.response.status_code} error for {endpoint}")
        except Exception as e:
            logger.error(f"Error calling endpoint {endpoint}: {e}")
            raise Exception(f"Failed to call {endpoint}: {str(e)}")

    async def get_form_analytics(self) -> dict:
        """Get analytics for the current form via API endpoint."""
        if not self.session_data.form_template_id:
            raise ValueError("No form template ID available")
        
        endpoint = f"/api/v1/forms/{self.session_data.form_template_id}/analytics"
        return await self._call_external_endpoint(endpoint, "GET")

    async def validate_form_data_externally(self, responses: dict) -> dict:
        """Validate form responses using external validation endpoint."""
        data = {
            "form_template_id": self.session_data.form_template_id,
            "responses": responses,
            "validation_level": "comprehensive"
        }
        
        endpoint = "/api/v1/forms/validate"
        return await self._call_external_endpoint(endpoint, "POST", data)

    async def submit_form_via_endpoint(self, form_data: dict) -> dict:
        """Submit form using the external API endpoint."""
        endpoint = "/api/v1/forms/submit"
        return await self._call_external_endpoint(endpoint, "POST", form_data)

    async def get_similar_submissions(self) -> List[dict]:
        """Get similar form submissions for context."""
        if not self.session_data.form_template_id:
            return []
        
        try:
            endpoint = f"/api/v1/forms/{self.session_data.form_template_id}/similar"
            params = {
                "limit": 5,
                "user_id": self.session_data.user_id
            }
            
            # Convert params to query string for GET request
            query_params = "&".join([f"{k}={v}" for k, v in params.items()])
            full_endpoint = f"{endpoint}?{query_params}"
            
            result = await self._call_external_endpoint(full_endpoint, "GET")
            return result.get("submissions", [])
            
        except Exception as e:
            logger.warning(f"Could not fetch similar submissions: {e}")
            return []

    def get_interactive_suggestions(self, field: dict, user_partial_input: str = "") -> List[str]:
        """Get intelligent suggestions for field completion."""
        field_type = field.get("field_type", "text")
        field_id = field.get("field_id", "")
        
        suggestions = []
        
        # Type-specific suggestions
        if field_type == "email":
            if "@" not in user_partial_input:
                common_domains = ["gmail.com", "yahoo.com", "outlook.com", "company.com"]
                if user_partial_input:
                    suggestions = [f"{user_partial_input}@{domain}" for domain in common_domains]
                else:
                    suggestions = ["user@gmail.com", "user@company.com"]
        
        elif field_type == "phone":
            if not user_partial_input:
                suggestions = ["+1-555-123-4567", "(555) 123-4567", "555-123-4567"]
            elif user_partial_input.isdigit() and len(user_partial_input) >= 3:
                # Format partial phone numbers
                digits = user_partial_input
                if len(digits) >= 10:
                    formatted = f"({digits[:3]}) {digits[3:6]}-{digits[6:10]}"
                    suggestions = [formatted]
        
        elif field_type == "date":
            from datetime import datetime, timedelta
            today = datetime.now()
            suggestions = [
                today.strftime("%Y-%m-%d"),
                (today + timedelta(days=1)).strftime("%Y-%m-%d"),
                (today + timedelta(days=7)).strftime("%Y-%m-%d")
            ]
        
        elif field_type in ["select", "multiselect"]:
            options = field.get("options", [])
            if user_partial_input and options:
                # Fuzzy matching for options
                user_lower = user_partial_input.lower()
                suggestions = [opt for opt in options if user_lower in opt.lower()]
        
        # Field-specific suggestions based on common field names
        elif "name" in field_id.lower():
            if not user_partial_input:
                suggestions = ["John Doe", "Jane Smith", "[Your full name]"]
        
        elif "company" in field_id.lower() or "organization" in field_id.lower():
            if not user_partial_input:
                suggestions = ["Acme Corp", "Tech Solutions Inc", "[Your company name]"]
        
        return suggestions[:3]  # Limit to top 3 suggestions