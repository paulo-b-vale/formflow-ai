"""
Execution tracing system for detailed agent workflow analysis.
"""

from typing import Dict, List, Any, Optional, Callable, ContextManager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from contextlib import contextmanager
from enum import Enum
import json
import uuid
import logging
import threading
import time

logger = logging.getLogger(__name__)


class TraceEventType(Enum):
    """Types of trace events."""
    NODE_START = "node_start"
    NODE_END = "node_end"
    PROMPT_EXECUTION = "prompt_execution"
    FIELD_EXTRACTION = "field_extraction"
    VALIDATION = "validation"
    ERROR = "error"
    DECISION = "decision"
    LLM_CALL = "llm_call"


@dataclass
class TraceNode:
    """Individual trace event in the execution tree."""
    id: str
    event_type: TraceEventType
    name: str                           # Human-readable name
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None    # Seconds
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    children: List['TraceNode'] = field(default_factory=list)
    parent_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None

    def finish(self, success: bool = True, error_message: Optional[str] = None, **output_data):
        """Mark the trace node as finished."""
        self.end_time = datetime.utcnow()
        self.duration = (self.end_time - self.start_time).total_seconds()
        self.success = success
        self.error_message = error_message
        self.output_data.update(output_data)

    def add_child(self, child: 'TraceNode'):
        """Add a child trace node."""
        child.parent_id = self.id
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "name": self.name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "metadata": self.metadata,
            "parent_id": self.parent_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "success": self.success,
            "error_message": self.error_message,
            "children": [child.to_dict() for child in self.children]
        }

    def get_execution_summary(self) -> Dict[str, Any]:
        """Get a summary of this execution branch."""
        total_duration = self.duration or 0
        child_duration = sum(child.duration or 0 for child in self.children)

        return {
            "name": self.name,
            "duration": total_duration,
            "child_duration": child_duration,
            "self_duration": total_duration - child_duration,
            "children_count": len(self.children),
            "success": self.success,
            "error_message": self.error_message
        }


class TracingContext:
    """Context manager for execution tracing."""

    def __init__(self, tracer: 'ExecutionTracer'):
        self.tracer = tracer
        self.local = threading.local()

    @contextmanager
    def trace_execution(self, event_type: TraceEventType, name: str,
                       session_id: Optional[str] = None, **metadata) -> ContextManager[TraceNode]:
        """Context manager for tracing a code block execution."""
        trace_node = self.tracer.start_trace(
            event_type=event_type,
            name=name,
            session_id=session_id,
            **metadata
        )

        try:
            yield trace_node
            trace_node.finish(success=True)
        except Exception as e:
            trace_node.finish(success=False, error_message=str(e))
            raise
        finally:
            self.tracer.finish_trace(trace_node.id)

    def get_current_trace(self) -> Optional[TraceNode]:
        """Get the current active trace node."""
        return getattr(self.local, 'current_trace', None)

    def set_current_trace(self, trace_node: Optional[TraceNode]):
        """Set the current active trace node."""
        self.local.current_trace = trace_node


class ExecutionTracer:
    """
    Advanced execution tracing system for detailed agent workflow analysis.
    Tracks every step of agent execution with timing, inputs, outputs, and hierarchical structure.
    """

    def __init__(self):
        self.traces: Dict[str, TraceNode] = {}
        self.active_traces: Dict[str, TraceNode] = {}
        self.context = TracingContext(self)
        self.callbacks: List[Callable[[TraceNode], None]] = []

    def start_trace(self, event_type: TraceEventType, name: str,
                   session_id: Optional[str] = None, **input_data) -> TraceNode:
        """
        Start a new trace node.

        Args:
            event_type: Type of event being traced
            name: Human-readable name for the trace
            session_id: Associated session ID
            **input_data: Input data for the traced operation

        Returns:
            TraceNode representing this execution
        """
        trace_id = str(uuid.uuid4())

        trace_node = TraceNode(
            id=trace_id,
            event_type=event_type,
            name=name,
            start_time=datetime.utcnow(),
            session_id=session_id,
            input_data=input_data
        )

        # If there's a current trace, add this as a child
        current_trace = self.context.get_current_trace()
        if current_trace:
            current_trace.add_child(trace_node)

        # Set as current trace
        self.context.set_current_trace(trace_node)
        self.active_traces[trace_id] = trace_node

        logger.debug(f"Started trace: {name} (ID: {trace_id})")
        return trace_node

    def finish_trace(self, trace_id: str, **output_data):
        """
        Finish a trace node.

        Args:
            trace_id: ID of trace to finish
            **output_data: Output data from the traced operation
        """
        if trace_id not in self.active_traces:
            logger.warning(f"Attempted to finish non-existent trace: {trace_id}")
            return

        trace_node = self.active_traces[trace_id]
        if not trace_node.end_time:  # Only finish if not already finished
            trace_node.finish(**output_data)

        # Store completed trace
        self.traces[trace_id] = trace_node
        del self.active_traces[trace_id]

        # Update current trace context
        parent_trace = self.get_trace_by_id(trace_node.parent_id) if trace_node.parent_id else None
        self.context.set_current_trace(parent_trace)

        # Notify callbacks
        for callback in self.callbacks:
            try:
                callback(trace_node)
            except Exception as e:
                logger.error(f"Error in trace callback: {e}")

        logger.debug(f"Finished trace: {trace_node.name} (duration: {trace_node.duration:.3f}s)")

    def get_trace_by_id(self, trace_id: str) -> Optional[TraceNode]:
        """Get a trace node by ID."""
        return self.traces.get(trace_id) or self.active_traces.get(trace_id)

    def get_session_traces(self, session_id: str) -> List[TraceNode]:
        """Get all traces for a specific session."""
        session_traces = []
        for trace in self.traces.values():
            if trace.session_id == session_id:
                session_traces.append(trace)
        return sorted(session_traces, key=lambda t: t.start_time)

    def get_execution_tree(self, session_id: str) -> Optional[TraceNode]:
        """Get the complete execution tree for a session."""
        session_traces = self.get_session_traces(session_id)

        # Find root trace (no parent)
        root_traces = [t for t in session_traces if t.parent_id is None]

        return root_traces[0] if root_traces else None

    def analyze_performance(self, session_id: str) -> Dict[str, Any]:
        """
        Analyze performance for a session.

        Args:
            session_id: Session to analyze

        Returns:
            Performance analysis
        """
        traces = self.get_session_traces(session_id)

        if not traces:
            return {"error": "No traces found for session"}

        total_duration = sum(t.duration or 0 for t in traces if t.duration)

        # Group by event type
        by_type = {}
        for trace in traces:
            event_type = trace.event_type.value
            if event_type not in by_type:
                by_type[event_type] = []
            by_type[event_type].append(trace)

        type_analysis = {}
        for event_type, type_traces in by_type.items():
            type_duration = sum(t.duration or 0 for t in type_traces)
            type_analysis[event_type] = {
                "count": len(type_traces),
                "total_duration": type_duration,
                "average_duration": type_duration / len(type_traces),
                "percentage_of_total": (type_duration / total_duration * 100) if total_duration > 0 else 0
            }

        # Find bottlenecks
        slowest_traces = sorted(traces, key=lambda t: t.duration or 0, reverse=True)[:5]

        return {
            "session_id": session_id,
            "total_traces": len(traces),
            "total_duration": total_duration,
            "by_type": type_analysis,
            "slowest_operations": [
                {
                    "name": t.name,
                    "duration": t.duration,
                    "event_type": t.event_type.value
                } for t in slowest_traces
            ],
            "success_rate": sum(1 for t in traces if t.success) / len(traces)
        }

    def get_debug_info(self, session_id: str) -> Dict[str, Any]:
        """
        Get comprehensive debug information for a session.

        Args:
            session_id: Session to analyze

        Returns:
            Debug information including traces, performance, and errors
        """
        traces = self.get_session_traces(session_id)
        failed_traces = [t for t in traces if not t.success]

        execution_tree = self.get_execution_tree(session_id)
        performance = self.analyze_performance(session_id)

        return {
            "session_id": session_id,
            "execution_tree": execution_tree.to_dict() if execution_tree else None,
            "performance_analysis": performance,
            "failed_operations": [
                {
                    "name": t.name,
                    "error": t.error_message,
                    "event_type": t.event_type.value,
                    "timestamp": t.start_time.isoformat()
                } for t in failed_traces
            ],
            "trace_count": len(traces),
            "active_traces": len(self.active_traces)
        }

    def add_callback(self, callback: Callable[[TraceNode], None]):
        """Add a callback to be called when traces complete."""
        self.callbacks.append(callback)

    def export_traces(self, session_id: str, format: str = "json") -> str:
        """
        Export traces for external analysis.

        Args:
            session_id: Session to export
            format: Export format ("json", "csv")

        Returns:
            Exported data as string
        """
        traces = self.get_session_traces(session_id)

        if format == "json":
            return json.dumps([trace.to_dict() for trace in traces], indent=2)
        elif format == "csv":
            # Simple CSV export
            lines = ["id,name,event_type,duration,success,start_time"]
            for trace in traces:
                lines.append(f"{trace.id},{trace.name},{trace.event_type.value},{trace.duration},{trace.success},{trace.start_time.isoformat()}")
            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def clear_old_traces(self, older_than_hours: int = 24):
        """Clear traces older than specified hours."""
        cutoff_time = datetime.utcnow() - timedelta(hours=older_than_hours)

        old_trace_ids = [
            trace_id for trace_id, trace in self.traces.items()
            if trace.start_time < cutoff_time
        ]

        for trace_id in old_trace_ids:
            del self.traces[trace_id]

        logger.info(f"Cleared {len(old_trace_ids)} old traces")


# Global tracer instance
execution_tracer = ExecutionTracer()


# Decorator for easy tracing
def trace_execution(event_type: TraceEventType, name: Optional[str] = None):
    """
    Decorator to automatically trace function execution.

    Args:
        event_type: Type of event being traced
        name: Custom name for the trace (defaults to function name)
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            trace_name = name or f"{func.__module__}.{func.__name__}"

            with execution_tracer.context.trace_execution(event_type, trace_name) as trace:
                # Add function arguments to trace
                trace.metadata["function"] = func.__name__
                trace.metadata["module"] = func.__module__

                result = await func(*args, **kwargs)

                # Add result info to trace
                trace.output_data["result_type"] = type(result).__name__

                return result

        def sync_wrapper(*args, **kwargs):
            trace_name = name or f"{func.__module__}.{func.__name__}"

            with execution_tracer.context.trace_execution(event_type, trace_name) as trace:
                # Add function arguments to trace
                trace.metadata["function"] = func.__name__
                trace.metadata["module"] = func.__module__

                result = func(*args, **kwargs)

                # Add result info to trace
                trace.output_data["result_type"] = type(result).__name__

                return result

        # Return appropriate wrapper based on function type
        if hasattr(func, '__code__') and 'await' in func.__code__.co_names:
            return async_wrapper
        else:
            return sync_wrapper

    return decorator