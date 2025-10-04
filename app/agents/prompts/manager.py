"""
Advanced prompt management system with versioning, A/B testing, and performance tracking.
"""

from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import logging
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


class PromptType(Enum):
    """Types of prompts in the system."""
    FORM_PREDICTION = "form_prediction"
    FIELD_EXTRACTION = "field_extraction"
    INTENT_CLASSIFICATION = "intent_classification"
    VALIDATION = "validation"
    CLARIFICATION = "clarification"


@dataclass
class PromptTemplate:
    """
    Structured prompt template with metadata and versioning.
    """
    id: str
    name: str
    prompt_type: PromptType
    template: str                    # Template string with placeholders
    version: str                     # Semantic version (e.g., "1.2.0")
    description: str                 # What this prompt does
    variables: List[str]             # Required variables for the template
    examples: List[Dict[str, Any]] = field(default_factory=list)  # Few-shot examples
    metadata: Dict[str, Any] = field(default_factory=dict)        # Additional metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    performance_metrics: Dict[str, float] = field(default_factory=dict)

    def render(self, **variables) -> str:
        """
        Render the prompt template with provided variables.

        Args:
            **variables: Variables to substitute in template

        Returns:
            Rendered prompt string
        """
        try:
            # Check if all required variables are provided
            missing_vars = set(self.variables) - set(variables.keys())
            if missing_vars:
                raise ValueError(f"Missing required variables: {missing_vars}")

            # Add examples if available
            rendered_prompt = self.template
            if self.examples:
                examples_text = self._format_examples()
                rendered_prompt = rendered_prompt.replace("{examples}", examples_text)

            # Substitute variables
            return rendered_prompt.format(**variables)

        except Exception as e:
            logger.error(f"Error rendering prompt template {self.id}: {e}")
            raise

    def _format_examples(self) -> str:
        """Format few-shot examples for inclusion in prompt."""
        if not self.examples:
            return ""

        formatted_examples = []
        for i, example in enumerate(self.examples, 1):
            formatted_examples.append(f"Exemplo {i}:")
            for key, value in example.items():
                formatted_examples.append(f"{key}: {value}")
            formatted_examples.append("")  # Empty line between examples

        return "\n".join(formatted_examples)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "prompt_type": self.prompt_type.value,
            "template": self.template,
            "version": self.version,
            "description": self.description,
            "variables": self.variables,
            "examples": self.examples,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "performance_metrics": self.performance_metrics
        }


@dataclass
class PromptResult:
    """
    Result of a prompt execution with performance tracking.
    """
    prompt_id: str
    prompt_version: str
    input_variables: Dict[str, Any]
    rendered_prompt: str
    raw_response: str
    parsed_response: Any
    execution_time: float            # Seconds
    token_count: Optional[int] = None
    cost: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    confidence_score: Optional[float] = None
    reasoning: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging and analysis."""
        return {
            "prompt_id": self.prompt_id,
            "prompt_version": self.prompt_version,
            "input_variables": self.input_variables,
            "execution_time": self.execution_time,
            "token_count": self.token_count,
            "cost": self.cost,
            "success": self.success,
            "error_message": self.error_message,
            "confidence_score": self.confidence_score,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp.isoformat()
        }


class PromptManager:
    """
    Advanced prompt management system with versioning, A/B testing, and optimization.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize prompt manager.

        Args:
            storage_path: Path to store prompt templates and performance data
        """
        self.storage_path = storage_path or Path("prompts")
        self.storage_path.mkdir(exist_ok=True)

        self.templates: Dict[str, PromptTemplate] = {}
        self.execution_history: List[PromptResult] = []
        self.ab_tests: Dict[str, Dict[str, Any]] = {}

        self._load_templates()

    def register_template(self, template: PromptTemplate) -> None:
        """
        Register a new prompt template.

        Args:
            template: PromptTemplate to register
        """
        self.templates[template.id] = template
        self._save_template(template)
        logger.info(f"Registered prompt template: {template.name} (v{template.version})")

    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """
        Get a prompt template by ID.

        Args:
            template_id: Template identifier

        Returns:
            PromptTemplate or None if not found
        """
        return self.templates.get(template_id)

    def get_templates_by_type(self, prompt_type: PromptType) -> List[PromptTemplate]:
        """
        Get all templates of a specific type.

        Args:
            prompt_type: Type of prompts to retrieve

        Returns:
            List of matching templates
        """
        return [t for t in self.templates.values() if t.prompt_type == prompt_type]

    def execute_prompt(self, template_id: str, llm_function: Callable, **variables) -> PromptResult:
        """
        Execute a prompt template with performance tracking.

        Args:
            template_id: ID of template to execute
            llm_function: Function to call LLM (should accept prompt string)
            **variables: Variables for template rendering

        Returns:
            PromptResult with execution details
        """
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        execution_id = str(uuid.uuid4())
        start_time = datetime.utcnow()

        try:
            # Render the prompt
            rendered_prompt = template.render(**variables)

            # Execute the LLM call
            response = llm_function(rendered_prompt)

            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()

            # Create result
            result = PromptResult(
                prompt_id=template.id,
                prompt_version=template.version,
                input_variables=variables,
                rendered_prompt=rendered_prompt,
                raw_response=response.content if hasattr(response, 'content') else str(response),
                parsed_response=response,
                execution_time=execution_time,
                success=True
            )

            # Store in history
            self.execution_history.append(result)
            self._update_template_metrics(template.id, result)

            logger.info(f"Successfully executed prompt {template_id} in {execution_time:.2f}s")
            return result

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            error_result = PromptResult(
                prompt_id=template.id,
                prompt_version=template.version,
                input_variables=variables,
                rendered_prompt="",
                raw_response="",
                parsed_response=None,
                execution_time=execution_time,
                success=False,
                error_message=str(e)
            )

            self.execution_history.append(error_result)
            logger.error(f"Error executing prompt {template_id}: {e}")
            return error_result

    async def execute_prompt_async(self, template_id: str, llm_function: Callable, **variables) -> PromptResult:
        """
        Execute a prompt template with performance tracking (async version).

        Args:
            template_id: ID of template to execute
            llm_function: Async function to call LLM (should accept prompt string)
            **variables: Variables for template rendering

        Returns:
            PromptResult with execution details
        """
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        execution_id = str(uuid.uuid4())
        start_time = datetime.utcnow()

        try:
            # Render the prompt
            rendered_prompt = template.render(**variables)

            # Execute the LLM call (await if async)
            response = await llm_function(rendered_prompt)

            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()

            # Create result
            result = PromptResult(
                prompt_id=template.id,
                prompt_version=template.version,
                input_variables=variables,
                rendered_prompt=rendered_prompt,
                raw_response=response.content if hasattr(response, 'content') else str(response),
                parsed_response=response,
                execution_time=execution_time,
                success=True
            )

            # Store in history
            self.execution_history.append(result)
            self._update_template_metrics(template.id, result)

            logger.info(f"Successfully executed async prompt {template_id} in {execution_time:.2f}s")
            return result

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            error_result = PromptResult(
                prompt_id=template.id,
                prompt_version=template.version,
                input_variables=variables,
                rendered_prompt="",
                raw_response="",
                parsed_response=None,
                execution_time=execution_time,
                success=False,
                error_message=str(e)
            )

            self.execution_history.append(error_result)
            logger.error(f"Error executing async prompt {template_id}: {e}")
            return error_result

    def start_ab_test(self, test_name: str, template_a_id: str, template_b_id: str,
                     split_ratio: float = 0.5) -> str:
        """
        Start an A/B test between two prompt templates.

        Args:
            test_name: Name of the A/B test
            template_a_id: ID of template A
            template_b_id: ID of template B
            split_ratio: Ratio of traffic to send to template A (0.0-1.0)

        Returns:
            A/B test ID
        """
        test_id = str(uuid.uuid4())

        self.ab_tests[test_id] = {
            "test_name": test_name,
            "template_a_id": template_a_id,
            "template_b_id": template_b_id,
            "split_ratio": split_ratio,
            "started_at": datetime.utcnow().isoformat(),
            "results_a": [],
            "results_b": []
        }

        logger.info(f"Started A/B test '{test_name}' with templates {template_a_id} vs {template_b_id}")
        return test_id

    def get_prompt_performance(self, template_id: str) -> Dict[str, Any]:
        """
        Get performance metrics for a prompt template.

        Args:
            template_id: Template ID

        Returns:
            Performance metrics dictionary
        """
        template_results = [r for r in self.execution_history if r.prompt_id == template_id]

        if not template_results:
            return {"message": "No execution history found"}

        successful_results = [r for r in template_results if r.success]

        metrics = {
            "total_executions": len(template_results),
            "successful_executions": len(successful_results),
            "success_rate": len(successful_results) / len(template_results),
            "average_execution_time": sum(r.execution_time for r in successful_results) / len(successful_results) if successful_results else 0,
            "average_confidence": sum(r.confidence_score for r in successful_results if r.confidence_score) / len([r for r in successful_results if r.confidence_score]) if successful_results else None
        }

        return metrics

    def optimize_template(self, template_id: str, optimization_goal: str = "confidence") -> Dict[str, Any]:
        """
        Suggest optimizations for a prompt template based on performance data.

        Args:
            template_id: Template to optimize
            optimization_goal: Goal for optimization ("confidence", "speed", "accuracy")

        Returns:
            Optimization suggestions
        """
        performance = self.get_prompt_performance(template_id)
        template = self.get_template(template_id)

        suggestions = []

        if performance["success_rate"] < 0.9:
            suggestions.append("Consider adding more examples or clearer instructions")

        if performance["average_execution_time"] > 10.0:
            suggestions.append("Prompt might be too long - consider shortening")

        if performance.get("average_confidence", 0) < 0.7:
            suggestions.append("Add chain-of-thought reasoning to improve confidence")

        return {
            "template_id": template_id,
            "current_performance": performance,
            "optimization_goal": optimization_goal,
            "suggestions": suggestions
        }

    def _load_templates(self):
        """Load templates from storage."""
        templates_file = self.storage_path / "templates.json"
        if templates_file.exists():
            try:
                with open(templates_file) as f:
                    data = json.load(f)
                    for template_data in data.get("templates", []):
                        template = self._dict_to_template(template_data)
                        self.templates[template.id] = template

                logger.info(f"Loaded {len(self.templates)} prompt templates")
            except Exception as e:
                logger.error(f"Error loading templates: {e}")

    def _save_template(self, template: PromptTemplate):
        """Save template to storage."""
        templates_file = self.storage_path / "templates.json"

        # Load existing templates
        templates_data = {"templates": []}
        if templates_file.exists():
            try:
                with open(templates_file) as f:
                    templates_data = json.load(f)
            except Exception:
                pass

        # Update or add the template
        existing_index = None
        for i, existing in enumerate(templates_data["templates"]):
            if existing["id"] == template.id:
                existing_index = i
                break

        template_dict = template.to_dict()
        if existing_index is not None:
            templates_data["templates"][existing_index] = template_dict
        else:
            templates_data["templates"].append(template_dict)

        # Save back to file
        with open(templates_file, 'w') as f:
            json.dump(templates_data, f, indent=2)

    def _dict_to_template(self, data: Dict[str, Any]) -> PromptTemplate:
        """Convert dictionary to PromptTemplate object."""
        return PromptTemplate(
            id=data["id"],
            name=data["name"],
            prompt_type=PromptType(data["prompt_type"]),
            template=data["template"],
            version=data["version"],
            description=data["description"],
            variables=data["variables"],
            examples=data.get("examples", []),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            performance_metrics=data.get("performance_metrics", {})
        )

    def _update_template_metrics(self, template_id: str, result: PromptResult):
        """Update template performance metrics based on execution result."""
        template = self.templates.get(template_id)
        if not template:
            return

        # Update metrics
        template.performance_metrics["last_execution"] = datetime.utcnow().isoformat()
        template.performance_metrics["total_executions"] = template.performance_metrics.get("total_executions", 0) + 1

        if result.success:
            template.performance_metrics["successful_executions"] = template.performance_metrics.get("successful_executions", 0) + 1

        # Save updated template
        self._save_template(template)