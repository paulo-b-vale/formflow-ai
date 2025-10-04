"""
Router node for determining the next agent to handle user requests.
"""

from typing import Optional
import logging

from ..base import BaseNode, state_get
from ..types import StateType, ResponseType, NodeResponse, NodeType
from app.utils.langchain_utils import get_gemini_llm
from app.sessions.session_manager import SessionManager

logger = logging.getLogger(__name__)


class RouterNode(BaseNode):
    """
    Enhanced routing node with optimized first message handling.
    Routes user messages to appropriate agent nodes based on intent and context.
    """

    def __init__(self, session_manager: Optional[SessionManager] = None):
        """
        Initialize router node.

        Args:
            session_manager: Optional session manager for state checking
        """
        super().__init__(NodeType.ROUTER, "router")
        self.llm = get_gemini_llm()
        self.session_manager = session_manager

    async def execute(self, state: StateType) -> ResponseType:
        """
        Route user message to appropriate node.

        Args:
            state: Current conversation state

        Returns:
            Response with next_node determined
        """
        # DEBUG: Log raw state to diagnose user_message issue
        self.logger.info(f"🔍 ROUTER DEBUG RAW STATE: type={type(state)}, keys={list(state.keys()) if isinstance(state, dict) else 'N/A'}")
        if isinstance(state, dict):
            self.logger.info(f"🔍 ROUTER DEBUG user_message in state: {'user_message' in state}, value={state.get('user_message', 'KEY_NOT_FOUND')}")

        user_message = state_get(state, "user_message")
        session_id = state_get(state, "session_id")
        session_state = state_get(state, "session_state", "STARTING")

        # Skip logging to avoid None formatting issues
        # TODO: Fix logging after container rebuild

        if not user_message:
            self.logger.info("No user message found, routing to form predictor")
            return NodeResponse(next_node="form_predictor")

        # Check for existing form session
        session_data = await self._get_session_data(session_id)
        self.logger.info(f"🔍 ROUTER: session_data exists: {session_data is not None}")
        if session_data:
            self.logger.info(f"🔍 ROUTER: session_state={getattr(session_data, 'state', 'NO_STATE')}, form_template_id={getattr(session_data, 'form_template_id', 'NO_ID')}")

        if session_data and hasattr(session_data, 'form_template_id') and session_data.form_template_id:
            self.logger.info(f"✅ ROUTER: Routing to form_filler for template: {session_data.form_template_id}")
            return NodeResponse(next_node="form_filler")
        else:
            self.logger.info(f"❌ ROUTER: No form_template_id found, session_data={session_data is not None}")

        # Check if this might be a report/search request before defaulting to form filling
        report_keywords = ["report", "relatório", "análise", "analysis", "resumo", "summary", "dados", "data", "estatística", "estatisticas", "tendência", "trend"]
        search_keywords = ["buscar", "search", "encontrar", "find", "consultar", "query", "mostrar", "show", "ver", "see", "list"]

        user_msg_lower = user_message.lower()
        might_be_report = any(keyword in user_msg_lower for keyword in report_keywords)
        might_be_search = any(keyword in user_msg_lower for keyword in search_keywords)

        print(f"🔍 ROUTER DEBUG: message='{user_message}', might_be_report={might_be_report}, might_be_search={might_be_search}")

        # Skip intent classification optimization only for clear form requests
        if (session_state == "STARTING" or not session_data) and not might_be_report and not might_be_search:
            self.logger.info("First message detected, appears to be form request - routing to form predictor")
            return NodeResponse(next_node="form_predictor")

        print(f"🔍 ROUTER: Will perform intent classification for: '{user_message}'")

        # Enhanced intent classification only for subsequent messages
        intent = await self._classify_intent(user_message)
        self.logger.info(f"Classified intent: '{intent}' for message: '{user_message}'")

        intent_mapping = {
            "fill_form": "form_predictor",
            "search_forms": "form_searcher",
            "generate_report": "report_generator",
            "clarification_needed": "clarification_handler"
        }

        next_node = intent_mapping.get(intent, "form_predictor")
        print(f"🔀 ROUTER DECISION: intent='{intent}' -> routing to '{next_node}'")
        self.logger.info(f"Routing to node: {next_node}")

        return NodeResponse(next_node=next_node)

    async def _classify_intent(self, user_message: str) -> str:
        """
        Enhanced intent classification with better prompting.

        Args:
            user_message: User's message to classify

        Returns:
            Classified intent string
        """
        prompt = f"""Você é um especialista em classificar intenções de usuários para um sistema de gerenciamento de formulários.

Baseado na mensagem do usuário, classifique a intenção em uma das seguintes categorias:

1. **fill_form** - Usuário quer iniciar, continuar ou interagir com o preenchimento de um formulário
   Exemplos: "Preciso preencher um formulário", "ajude-me com o relatório de segurança", "quero enviar informações"

2. **search_forms** - Usuário quer encontrar, consultar ou pesquisar através de formulários enviados existentes
   Exemplos: "mostre-me os relatórios de ontem", "encontre os formulários do João", "que formulários foram enviados hoje"

3. **generate_report** - Usuário quer análises, resumos ou relatórios dos dados de formulários
   Exemplos: "gere um resumo", "mostre-me as análises", "crie um relatório", "quais são as tendências"

4. **clarification_needed** - A solicitação do usuário não está clara ou pode corresponder a múltiplas intenções
   Exemplos: solicitações vagas, linguagem ambígua

Mensagem do usuário: "{user_message}"

Responda com APENAS o nome da categoria (fill_form, search_forms, generate_report, ou clarification_needed).
"""

        try:
            response = await self.llm.ainvoke(prompt)
            intent = response.content.lower().strip()

            # Normalize intent response
            if "fill_form" in intent or "form" in intent:
                return "fill_form"
            elif "search" in intent:
                return "search_forms"
            elif "report" in intent or "generate" in intent:
                return "generate_report"
            else:
                return "clarification_needed"

        except Exception as e:
            self.logger.error(f"Error classifying intent: {e}")
            return "fill_form"  # Safe default

    async def _get_session_data(self, session_id: str):
        """
        Get session data with enhanced error handling.

        Args:
            session_id: Session identifier

        Returns:
            Session data or None
        """
        if self.session_manager and session_id:
            try:
                return await self.session_manager.get_session(session_id)
            except Exception as e:
                self.logger.error(f"Error retrieving session data: {e}")
                return None
        return None

    def _get_required_state_keys(self) -> list:
        """Get required state keys for routing."""
        return ["session_id"]  # user_message is optional for routing