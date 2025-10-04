# app/utils/cost_tracker.py
import logging
from typing import Any, Dict, List, Optional
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import LLMResult
from datetime import datetime

logger = logging.getLogger(__name__)

class GeminiPricing:
    """Google Gemini API pricing constants (as of 2024-2025)"""
    
    PRICING = {
        'gemini-1.5-flash': {'input': 0.075, 'output': 0.30},
        'gemini-1.5-flash-8b': {'input': 0.0375, 'output': 0.15},
        'gemini-1.5-pro': {'input': 1.25, 'output': 5.00},
        'gemini-2.0-flash': {'input': 0.075, 'output': 0.30},
        'gemini-2.5-flash': {'input': 0.075, 'output': 0.30},  # Add pricing for gemini-2.5-flash
        'gemini-2.5-pro': {'input': 4.00, 'output': 20.00}
    }
    
    @classmethod
    def calculate_cost(cls, model: str, input_tokens: int, output_tokens: int) -> Dict[str, float]:
        """Calculate costs for input/output tokens"""
        model_clean = model.lower().replace('models/', '')
        pricing = cls.PRICING.get(model_clean, cls.PRICING['gemini-1.5-flash'])
        
        input_cost = (input_tokens / 1_000_000) * pricing['input']
        output_cost = (output_tokens / 1_000_000) * pricing['output']
        total_cost = input_cost + output_cost
        
        return {
            'input_cost': round(input_cost, 6),
            'output_cost': round(output_cost, 6),
            'total_cost': round(total_cost, 6),
            'model': model_clean,
            'pricing_tier': pricing
        }

class CostTrackingCallback(BaseCallbackHandler):
    """Advanced callback handler to track both tokens and costs"""
    
    def __init__(self, node_name: str = None, user_id: str = None, session_id: str = None):
        self.node_name = node_name
        self.user_id = user_id
        self.session_id = session_id
        self.total_tokens = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.call_count = 0
        self.total_cost = 0.0
        self.total_input_cost = 0.0
        self.total_output_cost = 0.0
        self.call_history = []
        
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Called when LLM ends running."""
        logger.debug(f"LLM response received: {response}")
        
        # Handle different LLM response formats for token usage
        token_usage = None
        model_name = "gemini-1.5-flash"  # Default model
        
        # Try to extract token usage from various locations in the response
        if response.llm_output:
            logger.debug(f"LLM output keys: {list(response.llm_output.keys())}")
            
            # Try different ways to extract token usage based on LLM provider
            if 'token_usage' in response.llm_output:
                # Standard format
                token_usage = response.llm_output['token_usage']
                model_name = response.llm_output.get('model_name', model_name)
            elif 'usage_metadata' in response.llm_output:
                # Google AI Studio format
                usage_metadata = response.llm_output['usage_metadata']
                token_usage = {
                    'prompt_tokens': usage_metadata.get('prompt_token_count', 0),
                    'completion_tokens': usage_metadata.get('candidates_token_count', 0),
                    'total_tokens': usage_metadata.get('total_token_count', 0)
                }
                model_name = response.llm_output.get('model_name', model_name)
            elif 'model_name' in response.llm_output:
                model_name = response.llm_output['model_name']
        
        # If we still don't have token usage, check in the generations
        if token_usage is None and hasattr(response, 'generations') and response.generations:
            logger.debug("Checking generations for token usage...")
            # Look in the first generation's message for usage metadata
            first_generation = response.generations[0][0] if response.generations and response.generations[0] else None
            if first_generation and hasattr(first_generation, 'message'):
                message = first_generation.message
                if hasattr(message, 'usage_metadata') and message.usage_metadata:
                    usage_metadata = message.usage_metadata
                    token_usage = {
                        'prompt_tokens': usage_metadata.get('input_tokens', 0),
                        'completion_tokens': usage_metadata.get('output_tokens', 0),
                        'total_tokens': usage_metadata.get('total_tokens', 0)
                    }
                    logger.debug(f"Extracted token usage from message.usage_metadata: {token_usage}")
                elif hasattr(message, 'response_metadata') and message.response_metadata:
                    response_metadata = message.response_metadata
                    if 'usage_metadata' in response_metadata:
                        usage_metadata = response_metadata['usage_metadata']
                        token_usage = {
                            'prompt_tokens': usage_metadata.get('input_tokens', 0),
                            'completion_tokens': usage_metadata.get('output_tokens', 0),
                            'total_tokens': usage_metadata.get('total_tokens', 0)
                        }
                        logger.debug(f"Extracted token usage from message.response_metadata: {token_usage}")
                    model_name = response_metadata.get('model_name', model_name)
        
        # If we still don't have token usage, try to extract from generation_info
        if token_usage is None and hasattr(response, 'generations') and response.generations:
            first_generation = response.generations[0][0] if response.generations and response.generations[0] else None
            if first_generation and hasattr(first_generation, 'generation_info') and first_generation.generation_info:
                gen_info = first_generation.generation_info
                if 'usage_metadata' in gen_info:
                    usage_metadata = gen_info['usage_metadata']
                    token_usage = {
                        'prompt_tokens': usage_metadata.get('input_tokens', 0),
                        'completion_tokens': usage_metadata.get('output_tokens', 0),
                        'total_tokens': usage_metadata.get('total_tokens', 0)
                    }
                    logger.debug(f"Extracted token usage from generation_info: {token_usage}")
                model_name = gen_info.get('model_name', model_name)
        
        if token_usage is not None:
            logger.debug(f"Token usage extracted: {token_usage}")
            prompt_tokens = token_usage.get('prompt_tokens', 0)
            completion_tokens = token_usage.get('completion_tokens', 0) 
            total_tokens = token_usage.get('total_tokens', prompt_tokens + completion_tokens)
            
            # Ensure we have valid values
            prompt_tokens = max(0, prompt_tokens)
            completion_tokens = max(0, completion_tokens)
            total_tokens = max(0, total_tokens)
            
            cost_info = GeminiPricing.calculate_cost(model_name, prompt_tokens, completion_tokens)
            
            self.total_input_tokens += prompt_tokens
            self.total_output_tokens += completion_tokens
            self.total_tokens += total_tokens
            self.total_input_cost += cost_info['input_cost']
            self.total_output_cost += cost_info['output_cost']
            self.total_cost += cost_info['total_cost']
            self.call_count += 1
            
            call_info = {
                'timestamp': datetime.now().isoformat(),
                'node_name': self.node_name,
                'user_id': self.user_id,
                'session_id': self.session_id,
                'call_number': self.call_count,
                'model': model_name,
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'total_tokens': total_tokens,
                'input_cost': cost_info['input_cost'],
                'output_cost': cost_info['output_cost'],
                'total_cost': cost_info['total_cost']
            }
            self.call_history.append(call_info)
            
            logger.info(
                f"[{self.node_name or 'Unknown'}] LLM Call #{self.call_count}: "
                f"{prompt_tokens} input + {completion_tokens} output = {total_tokens} tokens "
                f"(${cost_info['total_cost']:.6f})"
            )
        else:
            # Even if we can't get exact token counts, we still want to track that an LLM call was made
            # Use estimated average token counts for basic tracking
            estimated_prompt_tokens = 500  # Estimated average
            estimated_completion_tokens = 200  # Estimated average
            estimated_total_tokens = estimated_prompt_tokens + estimated_completion_tokens
            
            cost_info = GeminiPricing.calculate_cost(model_name, estimated_prompt_tokens, estimated_completion_tokens)
            
            self.total_input_tokens += estimated_prompt_tokens
            self.total_output_tokens += estimated_completion_tokens
            self.total_tokens += estimated_total_tokens
            self.total_input_cost += cost_info['input_cost']
            self.total_output_cost += cost_info['output_cost']
            self.total_cost += cost_info['total_cost']
            self.call_count += 1
            
            call_info = {
                'timestamp': datetime.now().isoformat(),
                'node_name': self.node_name,
                'user_id': self.user_id,
                'session_id': self.session_id,
                'call_number': self.call_count,
                'model': model_name,
                'prompt_tokens': estimated_prompt_tokens,
                'completion_tokens': estimated_completion_tokens,
                'total_tokens': estimated_total_tokens,
                'input_cost': cost_info['input_cost'],
                'output_cost': cost_info['output_cost'],
                'total_cost': cost_info['total_cost'],
                'estimated': True  # Flag to indicate these are estimates
            }
            self.call_history.append(call_info)
            
            logger.warning(
                f"[{self.node_name or 'Unknown'}] LLM Call #{self.call_count}: "
                f"Token usage not available, using estimated counts: "
                f"{estimated_prompt_tokens} input + {estimated_completion_tokens} output = {estimated_total_tokens} tokens "
                f"(${cost_info['total_cost']:.6f})"
            )
            logger.debug(f"No token usage found in LLM response. Response keys: {list(response.llm_output.keys()) if response.llm_output else 'None'}")
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Get comprehensive usage and cost summary"""
        return {
            'node_name': self.node_name,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'total_calls': self.call_count,
            'total_tokens': self.total_tokens,
            'total_input_tokens': self.total_input_tokens,
            'total_output_tokens': self.total_output_tokens,
            'total_cost': round(self.total_cost, 6),
            'total_input_cost': round(self.total_input_cost, 6),
            'total_output_cost': round(self.total_output_cost, 6),
        }

class SessionCostAggregator:
    """Aggregates costs across multiple nodes in a session"""
    
    def __init__(self, session_id: str, user_id: str):
        self.session_id = session_id
        self.user_id = user_id
        self.node_trackers: Dict[str, CostTrackingCallback] = {}
        
    def add_node_tracker(self, node_name: str, tracker: CostTrackingCallback):
        """Add a node's cost tracker to the session aggregator"""
        self.node_trackers[node_name] = tracker
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get aggregated costs for the entire session"""
        total_session_cost = 0.0
        total_session_tokens = 0
        total_calls = 0
        node_summaries = {}
        
        for node_name, tracker in self.node_trackers.items():
            summary = tracker.get_usage_summary()
            node_summaries[node_name] = summary
            total_session_cost += summary['total_cost']
            total_session_tokens += summary['total_tokens']
            total_calls += summary['total_calls']
        
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'total_session_cost': round(total_session_cost, 6),
            'total_session_tokens': total_session_tokens,
            'total_calls': total_calls,
            'nodes_used': list(self.node_trackers.keys()),
            'node_breakdown': node_summaries,
            'most_expensive_node': max(node_summaries.items(), key=lambda x: x[1]['total_cost'])[0] if node_summaries else None
        }

class CostTrackingDatabase:
    """Database integration for cost and token usage tracking"""
    
    def __init__(self, db):
        self.db = db
    
    async def log_session_costs(self, session_summary: Dict[str, Any]):
        """Log session cost summary to database"""
        session_doc = {**session_summary, 'created_at': datetime.utcnow()}
        await self.db.session_costs.insert_one(session_doc)
    
    async def log_node_costs(self, node_summary: Dict[str, Any]):
        """Log individual node costs"""
        node_doc = {**node_summary, 'created_at': datetime.utcnow()}
        await self.db.node_costs.insert_one(node_doc)