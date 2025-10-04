"""
Pre-defined prompt templates for various agent tasks.
"""

from typing import List, Dict, Any
from .manager import PromptTemplate, PromptType, PromptManager


class FormPredictionPrompts:
    """Prompt templates for form prediction tasks."""

    @staticmethod
    def get_enhanced_form_prediction_template() -> PromptTemplate:
        """Enhanced form prediction with alternatives and smart selection."""
        return PromptTemplate(
            id="form_prediction_enhanced_v3",
            name="Enhanced Form Prediction with Smart Alternatives",
            prompt_type=PromptType.FORM_PREDICTION,
            version="3.0.0",
            description="Predicts appropriate form with detailed alternatives for user selection",
            variables=["user_message", "available_forms"],
            template="""Você é um especialista em análise de intenções para sistema de formulários.

TAREFA: Analisar a mensagem do usuário e prever formulários apropriados.

MENSAGEM DO USUÁRIO: "{user_message}"

FORMULÁRIOS DISPONÍVEIS:
{available_forms}

PROCESSO DE RACIOCÍNIO:
1. ANÁLISE DA MENSAGEM: Identifique palavras-chave, contexto e intenção
2. CORRESPONDÊNCIA: Compare com títulos, descrições e tags dos formulários
3. RANKING: Ordene os formulários por relevância com confiança individual
4. JUSTIFICATIVA: Explique o raciocínio para cada opção

RESPONDA EM JSON:
{{
    "primary_prediction": {{
        "form_id": "id_do_formulario_principal",
        "title": "Nome do Formulário",
        "description": "Descrição do formulário",
        "confidence_score": 0.85,
        "reasoning": "Explicação para esta escolha",
        "matched_keywords": ["palavra1", "palavra2"],
        "context_title": "Área/Contexto"
    }},
    "alternative_forms": [
        {{
            "form_id": "id_alternativo_1",
            "title": "Formulário Alternativo 1",
            "description": "Descrição da alternativa",
            "confidence": 0.65,
            "reasoning": "Por que esta é uma alternativa válida",
            "match_keywords": ["palavra3", "palavra4"],
            "context_title": "Área/Contexto"
        }},
        {{
            "form_id": "id_alternativo_2",
            "title": "Formulário Alternativo 2",
            "description": "Descrição da segunda alternativa",
            "confidence": 0.55,
            "reasoning": "Por que esta também pode servir",
            "match_keywords": ["palavra5"],
            "context_title": "Área/Contexto"
        }}
    ],
    "overall_confidence": 0.75,
    "reasoning_steps": [
        {{
            "step": "análise_mensagem",
            "finding": "Identifiquei palavras-chave e contexto",
            "confidence": 0.9
        }},
        {{
            "step": "correspondência_formulários",
            "finding": "Encontrei 3 formulários com correspondência",
            "confidence": 0.8
        }}
    ],
    "requires_user_selection": false
}}

REGRAS IMPORTANTES:
- SEMPRE forneça pelo menos 2-3 alternativas, mesmo com alta confiança
- Se confiança primária < 70%, definir requires_user_selection=true
- Ordene alternativas por confiança (maior primeiro)
- Matched_keywords devem ser palavras específicas da mensagem do usuário
- Reasoning deve explicar POR QUE cada formulário faz sentido
- Context_title deve indicar a área/categoria do formulário""",
            examples=[
                {
                    "user_message": "Preciso reportar um acidente na obra",
                    "expected_primary": "construction_incident_report",
                    "expected_alternatives": ["safety_report", "general_incident_report"],
                    "reasoning": "Palavra 'acidente' indica relatório de incidente, 'obra' especifica construção"
                }
            ]
        )

    @staticmethod
    def get_quick_form_prediction_template() -> PromptTemplate:
        """Fast form prediction for high-confidence cases."""
        return PromptTemplate(
            id="form_prediction_quick_v1",
            name="Quick Form Prediction",
            prompt_type=PromptType.FORM_PREDICTION,
            version="1.0.0",
            description="Fast form prediction for obvious cases",
            variables=["user_message", "available_forms"],
            template="""Mensagem: "{user_message}"
Formulários: {available_forms}

Responda apenas o ID do formulário mais apropriado e confiança:
{{"form_id": "xxx", "confidence": 0.xx}}"""
        )


class FieldExtractionPrompts:
    """Prompt templates for field extraction tasks."""

    @staticmethod
    def get_multi_field_extraction_template() -> PromptTemplate:
        """Extract multiple fields from user message with confidence."""
        return PromptTemplate(
            id="field_extraction_multi_v2",
            name="Multi-Field Extraction with Confidence",
            prompt_type=PromptType.FIELD_EXTRACTION,
            version="2.0.0",
            description="Extracts multiple form fields from user message with confidence tracking",
            variables=["user_message", "unfilled_fields"],
            template="""Você é um especialista em extrair informações de mensagens para preencher formulários.

MENSAGEM DO USUÁRIO: "{user_message}"

CAMPOS PARA PREENCHER:
{unfilled_fields}

PROCESSO:
1. IDENTIFICAÇÃO: Encontre informações na mensagem que correspondem aos campos
2. VALIDAÇÃO: Verifique se a informação está no formato correto
3. CONFIANÇA: Avalie certeza de cada extração (0-100%)

RESPONDA EM JSON:
{{
    "extracted_fields": {{
        "campo_id": {{
            "value": "valor_extraído",
            "confidence": 0.95,
            "reasoning": "Encontrei 'João Silva' que claramente é um nome",
            "source_text": "Meu nome é João Silva"
        }}
    }},
    "summary": {{
        "total_fields_found": 3,
        "average_confidence": 0.87,
        "extraction_quality": "high"
    }}
}}

REGRAS:
- Apenas extraia informações que você tem certeza (confiança > 60%)
- Para campos de seleção, use apenas valores das opções fornecidas
- Para datas, converta para formato AAAA-MM-DD
- NÃO invente informações que não estão na mensagem""",
            examples=[
                {
                    "user_message": "Meu nome é João Silva, telefone (11) 99999-9999",
                    "expected_extraction": {
                        "nome": {"value": "João Silva", "confidence": 0.95},
                        "telefone": {"value": "(11) 99999-9999", "confidence": 0.9}
                    }
                }
            ]
        )

    @staticmethod
    def get_single_field_validation_template() -> PromptTemplate:
        """Validate a single field with detailed feedback."""
        return PromptTemplate(
            id="field_validation_single_v1",
            name="Single Field Validation",
            prompt_type=PromptType.VALIDATION,
            version="1.0.0",
            description="Validates a single field value with detailed feedback",
            variables=["field_info", "user_input"],
            template="""CAMPO: {field_info}
VALOR FORNECIDO: "{user_input}"

Valide e responda:
{{
    "is_valid": true/false,
    "processed_value": "valor_limpo",
    "confidence": 0.9,
    "issues": ["problema1", "problema2"],
    "suggestions": ["sugestão1", "sugestão2"]
}}"""
        )


class IntentClassificationPrompts:
    """Prompt templates for intent classification."""

    @staticmethod
    def get_intent_classification_template() -> PromptTemplate:
        """Classify user intent with confidence."""
        return PromptTemplate(
            id="intent_classification_v1",
            name="Intent Classification",
            prompt_type=PromptType.INTENT_CLASSIFICATION,
            version="1.0.0",
            description="Classifies user intent for routing decisions",
            variables=["user_message"],
            template="""Classifique a intenção do usuário:

MENSAGEM: "{user_message}"

INTENÇÕES POSSÍVEIS:
- fill_form: Quer preencher um formulário
- search_forms: Quer buscar formulários existentes
- generate_report: Quer relatórios/análises
- clarification_needed: Mensagem ambígua

RESPONDA:
{{
    "intent": "fill_form",
    "confidence": 0.85,
    "reasoning": "Usuário mencionou 'preencher' explicitamente"
}}"""
        )


class ClarificationPrompts:
    """Prompt templates for clarification scenarios."""

    @staticmethod
    def get_smart_clarification_template() -> PromptTemplate:
        """Generate smart clarification questions."""
        return PromptTemplate(
            id="clarification_smart_v1",
            name="Smart Clarification Generator",
            prompt_type=PromptType.CLARIFICATION,
            version="1.0.0",
            description="Generates contextual clarification questions",
            variables=["user_message", "available_options", "context"],
            template="""MENSAGEM AMBÍGUA: "{user_message}"
CONTEXTO: {context}
OPÇÕES DISPONÍVEIS: {available_options}

Gere uma pergunta de esclarecimento útil e específica em português.
Seja conciso e ofereça opções concretas quando possível.

RESPOSTA:
{{
    "clarification_message": "Preciso esclarecer...",
    "suggested_options": ["opção1", "opção2"],
    "confidence_needed": 0.7
}}"""
        )


class PromptLibrary:
    """Central library for managing all prompt templates."""

    def __init__(self, prompt_manager: PromptManager):
        self.manager = prompt_manager
        self.register_all_templates()

    def register_all_templates(self):
        """Register all predefined templates."""
        templates = [
            # Form Prediction
            FormPredictionPrompts.get_enhanced_form_prediction_template(),
            FormPredictionPrompts.get_quick_form_prediction_template(),

            # Field Extraction
            FieldExtractionPrompts.get_multi_field_extraction_template(),
            FieldExtractionPrompts.get_single_field_validation_template(),

            # Intent Classification
            IntentClassificationPrompts.get_intent_classification_template(),

            # Clarification
            ClarificationPrompts.get_smart_clarification_template(),
        ]

        for template in templates:
            self.manager.register_template(template)

    def get_form_prediction_prompt(self, enhanced: bool = True) -> str:
        """Get form prediction prompt ID."""
        return "form_prediction_enhanced_v3" if enhanced else "form_prediction_quick_v1"

    def get_field_extraction_prompt(self) -> str:
        """Get field extraction prompt ID."""
        return "field_extraction_multi_v2"

    def get_intent_classification_prompt(self) -> str:
        """Get intent classification prompt ID."""
        return "intent_classification_v1"

    def get_clarification_prompt(self) -> str:
        """Get clarification prompt ID."""
        return "clarification_smart_v1"