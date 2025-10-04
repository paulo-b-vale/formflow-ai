"""
Smart form selection system for low confidence scenarios.
Instead of failing when confidence is low, present alternatives to user.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

from .confidence import ConfidenceLevel, ReasoningChain

logger = logging.getLogger(__name__)


@dataclass
class FormAlternative:
    """Represents a form alternative with reasoning."""
    form_id: str
    title: str
    description: str
    confidence: float
    reasoning: str
    match_keywords: List[str]
    context_title: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "form_id": self.form_id,
            "title": self.title,
            "description": self.description,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "match_keywords": self.match_keywords,
            "context_title": self.context_title
        }


@dataclass
class FormSelectionScenario:
    """Represents a form selection scenario with alternatives."""
    user_message: str
    overall_confidence: float
    alternatives: List[FormAlternative]
    reasoning_chain: Optional[ReasoningChain] = None
    session_id: Optional[str] = None
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()

    def get_top_alternatives(self, count: int = 3) -> List[FormAlternative]:
        """Get top N alternatives sorted by confidence."""
        return sorted(self.alternatives, key=lambda x: x.confidence, reverse=True)[:count]

    def generate_selection_message(self) -> str:
        """Generate user-friendly selection message in Portuguese."""
        confidence_level = ConfidenceLevel.from_score(self.overall_confidence)

        top_alternatives = self.get_top_alternatives(3)

        message_parts = [
            f"{confidence_level.to_emoji()} Encontrei algumas opções que podem corresponder à sua solicitação:",
            f"📝 Sua mensagem: \"{self.user_message}\"",
            "",
            "🎯 Formulários possíveis:"
        ]

        for i, alt in enumerate(top_alternatives, 1):
            confidence_emoji = ConfidenceLevel.from_score(alt.confidence).to_emoji()

            message_parts.extend([
                f"",
                f"**{i}. {alt.title}** {confidence_emoji}",
                f"   📄 {alt.description}",
                f"   🎯 Correspondência: {alt.reasoning}",
                f"   🔑 Palavras-chave: {', '.join(alt.match_keywords)}"
            ])

            if alt.context_title:
                message_parts.append(f"   📁 Área: {alt.context_title}")

        message_parts.extend([
            "",
            "💬 **Escolha uma opção:**",
            "• Digite o número (1, 2, ou 3)",
            "• Ou diga 'nenhuma' se nenhuma opção serve",
            "• Ou reformule sua solicitação com mais detalhes"
        ])

        return "\n".join(message_parts)

    def handle_user_selection(self, user_input: str) -> Dict[str, Any]:
        """
        Handle user selection and return appropriate response.

        Args:
            user_input: User's selection input

        Returns:
            Dictionary with selection result
        """
        user_input_clean = user_input.strip().lower()

        # Check for direct number selection
        if user_input_clean in ['1', '2', '3']:
            try:
                selection_index = int(user_input_clean) - 1
                top_alternatives = self.get_top_alternatives(3)

                if 0 <= selection_index < len(top_alternatives):
                    selected_form = top_alternatives[selection_index]

                    return {
                        "action": "form_selected",
                        "form_id": selected_form.form_id,
                        "form_title": selected_form.title,
                        "confidence": selected_form.confidence,
                        "reasoning": f"Usuário selecionou opção {user_input_clean}: {selected_form.title}",
                        "success": True
                    }
                else:
                    return {
                        "action": "invalid_selection",
                        "error": f"Opção {user_input_clean} não está disponível. Escolha 1, 2 ou 3.",
                        "success": False
                    }
            except ValueError:
                pass

        # Check for rejection
        rejection_keywords = ['nenhuma', 'nenhum', 'não', 'nao', 'none', 'cancel', 'cancelar']
        if any(keyword in user_input_clean for keyword in rejection_keywords):
            return {
                "action": "rejected_all",
                "message": "Entendo que nenhuma opção serve. Você pode reformular sua solicitação com mais detalhes ou especificar exatamente que tipo de formulário você precisa.",
                "success": False
            }

        # Check for selection by name/keyword
        for i, alternative in enumerate(self.get_top_alternatives(3), 1):
            # Check if user mentioned the form title or key words
            form_keywords = [
                alternative.title.lower(),
                *[kw.lower() for kw in alternative.match_keywords]
            ]

            if any(keyword in user_input_clean for keyword in form_keywords):
                return {
                    "action": "form_selected",
                    "form_id": alternative.form_id,
                    "form_title": alternative.title,
                    "confidence": alternative.confidence,
                    "reasoning": f"Usuário mencionou palavras relacionadas a: {alternative.title}",
                    "success": True
                }

        # If we get here, it's an unclear selection
        return {
            "action": "unclear_selection",
            "message": "Não entendi sua seleção. Por favor:\n• Digite 1, 2 ou 3 para escolher uma opção\n• Digite 'nenhuma' se não gosta de nenhuma\n• Ou reformule sua solicitação original",
            "success": False
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "user_message": self.user_message,
            "overall_confidence": self.overall_confidence,
            "confidence_level": ConfidenceLevel.from_score(self.overall_confidence).value,
            "alternatives": [alt.to_dict() for alt in self.alternatives],
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class SmartFormSelector:
    """
    Smart form selection system that handles low confidence scenarios
    by presenting alternatives to users.
    """

    def __init__(self, confidence_threshold: float = 0.7):
        """
        Initialize the smart form selector.

        Args:
            confidence_threshold: Confidence below which to show alternatives
        """
        self.confidence_threshold = confidence_threshold
        self.active_selections: Dict[str, FormSelectionScenario] = {}

    def should_show_alternatives(self, confidence: float) -> bool:
        """Check if we should show alternatives based on confidence."""
        return confidence < self.confidence_threshold

    def create_selection_scenario(self, user_message: str, prediction_result: Dict[str, Any],
                                session_id: str = None) -> FormSelectionScenario:
        """
        Create a form selection scenario from prediction results.

        Args:
            user_message: Original user message
            prediction_result: Result from form prediction including alternatives
            session_id: Session identifier

        Returns:
            FormSelectionScenario object
        """
        # Extract alternatives from prediction result
        alternatives = []

        # Primary prediction as first alternative
        if prediction_result.get("form_template_id"):
            alternatives.append(FormAlternative(
                form_id=prediction_result["form_template_id"],
                title=prediction_result.get("form_title", "Formulário Principal"),
                description=prediction_result.get("form_description", ""),
                confidence=prediction_result.get("confidence_score", 0.5),
                reasoning=prediction_result.get("reasoning", "Primeira opção sugerida"),
                match_keywords=prediction_result.get("matched_keywords", [])
            ))

        # Additional alternatives
        for alt_data in prediction_result.get("alternative_forms", []):
            if isinstance(alt_data, dict):
                alternatives.append(FormAlternative(
                    form_id=alt_data.get("form_id", ""),
                    title=alt_data.get("title", "Formulário Alternativo"),
                    description=alt_data.get("description", ""),
                    confidence=alt_data.get("confidence", 0.3),
                    reasoning=alt_data.get("reasoning", "Opção alternativa"),
                    match_keywords=alt_data.get("match_keywords", []),
                    context_title=alt_data.get("context_title")
                ))

        scenario = FormSelectionScenario(
            user_message=user_message,
            overall_confidence=prediction_result.get("confidence_score", 0.5),
            alternatives=alternatives,
            session_id=session_id
        )

        # Store active selection for this session
        if session_id:
            self.active_selections[session_id] = scenario

        logger.info(f"Created selection scenario for session {session_id} with {len(alternatives)} alternatives")
        return scenario

    def handle_selection_response(self, session_id: str, user_input: str) -> Optional[Dict[str, Any]]:
        """
        Handle user's response to form selection.

        Args:
            session_id: Session identifier
            user_input: User's selection input

        Returns:
            Selection result or None if no active selection
        """
        if session_id not in self.active_selections:
            return None

        scenario = self.active_selections[session_id]
        result = scenario.handle_user_selection(user_input)

        # If successfully selected or rejected, remove from active selections
        if result.get("action") in ["form_selected", "rejected_all"]:
            del self.active_selections[session_id]

        logger.info(f"Handled selection for session {session_id}: {result.get('action')}")
        return result

    def has_active_selection(self, session_id: str) -> bool:
        """Check if there's an active form selection for this session."""
        return session_id in self.active_selections

    def get_active_selection(self, session_id: str) -> Optional[FormSelectionScenario]:
        """Get active selection scenario for session."""
        return self.active_selections.get(session_id)

    def clear_selection(self, session_id: str):
        """Clear active selection for session."""
        if session_id in self.active_selections:
            del self.active_selections[session_id]
            logger.info(f"Cleared selection for session {session_id}")

    def get_selection_stats(self) -> Dict[str, Any]:
        """Get statistics about form selections."""
        return {
            "active_selections": len(self.active_selections),
            "sessions_with_selections": list(self.active_selections.keys())
        }


# Global instance for easy access
smart_form_selector = SmartFormSelector()