"""
Advanced confidence tracking and reasoning system.
"""

from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class ConfidenceLevel(Enum):
    """Standardized confidence levels with semantic meaning."""
    VERY_HIGH = "very_high"    # 90-100% - Extremely confident
    HIGH = "high"              # 75-89%  - Confident
    MEDIUM = "medium"          # 50-74%  - Somewhat confident
    LOW = "low"                # 25-49%  - Low confidence
    VERY_LOW = "very_low"      # 0-24%   - Very uncertain

    @classmethod
    def from_score(cls, score: float) -> 'ConfidenceLevel':
        """Convert numeric score to confidence level."""
        if score >= 0.9:
            return cls.VERY_HIGH
        elif score >= 0.75:
            return cls.HIGH
        elif score >= 0.5:
            return cls.MEDIUM
        elif score >= 0.25:
            return cls.LOW
        else:
            return cls.VERY_LOW

    def to_emoji(self) -> str:
        """Get emoji representation of confidence level."""
        emoji_map = {
            self.VERY_HIGH: "🟢",
            self.HIGH: "🟡",
            self.MEDIUM: "🟠",
            self.LOW: "🔴",
            self.VERY_LOW: "⚫"
        }
        return emoji_map[self]

    def to_portuguese(self) -> str:
        """Get Portuguese description."""
        portuguese_map = {
            self.VERY_HIGH: "Muito confiante",
            self.HIGH: "Confiante",
            self.MEDIUM: "Moderadamente confiante",
            self.LOW: "Pouco confiante",
            self.VERY_LOW: "Muito incerto"
        }
        return portuguese_map[self]


@dataclass
class ReasoningStep:
    """Individual step in reasoning chain."""
    step_type: str              # "analysis", "matching", "validation", etc.
    description: str            # What was done in this step
    input_data: Dict[str, Any]  # Input to this step
    output_data: Dict[str, Any] # Output from this step
    confidence: float           # Confidence in this step (0-1)
    reasoning: str              # Why this conclusion was reached
    evidence: List[str] = field(default_factory=list)  # Supporting evidence
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "step_type": self.step_type,
            "description": self.description,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "evidence": self.evidence,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ReasoningChain:
    """Complete chain of reasoning for a decision."""
    decision_id: str
    decision_type: str          # "form_prediction", "field_extraction", etc.
    initial_input: Dict[str, Any]
    final_output: Dict[str, Any]
    overall_confidence: float
    steps: List[ReasoningStep] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def add_step(self, step: ReasoningStep):
        """Add a reasoning step to the chain."""
        self.steps.append(step)
        # Update overall confidence (weighted average)
        if self.steps:
            total_confidence = sum(s.confidence for s in self.steps)
            self.overall_confidence = total_confidence / len(self.steps)

    def get_confidence_level(self) -> ConfidenceLevel:
        """Get semantic confidence level."""
        return ConfidenceLevel.from_score(self.overall_confidence)

    def get_summary(self) -> str:
        """Get human-readable summary of the reasoning."""
        level = self.get_confidence_level()
        step_count = len(self.steps)

        return f"{level.to_emoji()} {level.to_portuguese()} ({self.overall_confidence:.1%}) baseado em {step_count} etapas de análise"

    def get_detailed_explanation(self) -> str:
        """Get detailed explanation for users."""
        explanations = []
        explanations.append(f"**Decisão:** {self.decision_type}")
        explanations.append(f"**Confiança:** {self.get_summary()}")
        explanations.append("\n**Processo de raciocínio:**")

        for i, step in enumerate(self.steps, 1):
            explanations.append(f"{i}. **{step.description}**")
            explanations.append(f"   - Confiança: {step.confidence:.1%}")
            explanations.append(f"   - Raciocínio: {step.reasoning}")
            if step.evidence:
                explanations.append(f"   - Evidência: {', '.join(step.evidence)}")

        return "\n".join(explanations)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "decision_id": self.decision_id,
            "decision_type": self.decision_type,
            "initial_input": self.initial_input,
            "final_output": self.final_output,
            "overall_confidence": self.overall_confidence,
            "confidence_level": self.get_confidence_level().value,
            "steps": [step.to_dict() for step in self.steps],
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


class ConfidenceTracker:
    """
    Advanced confidence tracking system with reasoning chains.
    Tracks confidence at multiple levels and provides detailed explanations.
    """

    def __init__(self):
        self.decision_history: List[ReasoningChain] = []
        self.confidence_thresholds = {
            "form_prediction": 0.7,    # Require 70% confidence for form prediction
            "field_extraction": 0.6,   # 60% for field extraction
            "validation": 0.8,         # 80% for validation decisions
            "intent_classification": 0.6  # 60% for intent classification
        }

    def start_reasoning_chain(self, decision_id: str, decision_type: str, initial_input: Dict[str, Any]) -> ReasoningChain:
        """Start a new reasoning chain for a decision."""
        chain = ReasoningChain(
            decision_id=decision_id,
            decision_type=decision_type,
            initial_input=initial_input,
            final_output={},
            overall_confidence=0.0
        )

        logger.info(f"Started reasoning chain for {decision_type} (ID: {decision_id})")
        return chain

    def add_reasoning_step(self, chain: ReasoningChain, step_type: str, description: str,
                          input_data: Dict[str, Any], output_data: Dict[str, Any],
                          confidence: float, reasoning: str, evidence: List[str] = None) -> ReasoningStep:
        """Add a step to the reasoning chain."""
        step = ReasoningStep(
            step_type=step_type,
            description=description,
            input_data=input_data,
            output_data=output_data,
            confidence=confidence,
            reasoning=reasoning,
            evidence=evidence or []
        )

        chain.add_step(step)
        logger.debug(f"Added reasoning step: {description} (confidence: {confidence:.2f})")
        return step

    def complete_reasoning_chain(self, chain: ReasoningChain, final_output: Dict[str, Any]) -> ReasoningChain:
        """Complete a reasoning chain and store it in history."""
        chain.final_output = final_output
        self.decision_history.append(chain)

        logger.info(f"Completed reasoning chain {chain.decision_id} with confidence {chain.overall_confidence:.2f}")
        return chain

    def should_proceed_with_confidence(self, decision_type: str, confidence: float) -> bool:
        """Check if confidence is sufficient to proceed with a decision."""
        threshold = self.confidence_thresholds.get(decision_type, 0.5)
        return confidence >= threshold

    def get_confidence_explanation(self, chain: ReasoningChain, for_user: bool = True) -> str:
        """Get confidence explanation suitable for users or developers."""
        if for_user:
            return chain.get_detailed_explanation()
        else:
            # Developer-focused explanation with more technical details
            dev_info = []
            dev_info.append(f"Decision ID: {chain.decision_id}")
            dev_info.append(f"Type: {chain.decision_type}")
            dev_info.append(f"Overall Confidence: {chain.overall_confidence:.4f}")
            dev_info.append(f"Confidence Level: {chain.get_confidence_level().value}")
            dev_info.append(f"Steps: {len(chain.steps)}")
            dev_info.append("Step Details:")

            for step in chain.steps:
                dev_info.append(f"  - {step.step_type}: {step.confidence:.4f} - {step.description}")
                if step.evidence:
                    dev_info.append(f"    Evidence: {step.evidence}")

            return "\n".join(dev_info)

    def get_recent_decisions(self, limit: int = 10) -> List[ReasoningChain]:
        """Get recent decision chains for analysis."""
        return self.decision_history[-limit:]

    def get_confidence_stats(self) -> Dict[str, Any]:
        """Get confidence statistics across all decisions."""
        if not self.decision_history:
            return {"total_decisions": 0}

        confidences = [chain.overall_confidence for chain in self.decision_history]
        decision_types = {}

        for chain in self.decision_history:
            if chain.decision_type not in decision_types:
                decision_types[chain.decision_type] = []
            decision_types[chain.decision_type].append(chain.overall_confidence)

        stats = {
            "total_decisions": len(self.decision_history),
            "average_confidence": sum(confidences) / len(confidences),
            "min_confidence": min(confidences),
            "max_confidence": max(confidences),
            "by_type": {}
        }

        for decision_type, type_confidences in decision_types.items():
            stats["by_type"][decision_type] = {
                "count": len(type_confidences),
                "average": sum(type_confidences) / len(type_confidences),
                "min": min(type_confidences),
                "max": max(type_confidences)
            }

        return stats


# Global instance for easy access
confidence_tracker = ConfidenceTracker()