# 🚀 Enhanced Agents System - Implementation Guide

This guide shows how to implement the enhanced agent features for better debugging and user experience.

## 🎯 Key Improvements Implemented

### **1. 🧠 Enhanced Confidence & Reasoning System**

**What it does:**
- Tracks confidence at multiple levels with detailed explanations
- Provides step-by-step reasoning chains
- Offers different explanations for users vs developers

**Example Usage:**
```python
from app.agents.reasoning import confidence_tracker, ConfidenceLevel

# Start reasoning chain
chain = confidence_tracker.start_reasoning_chain(
    decision_id="form_prediction_001",
    decision_type="form_prediction",
    initial_input={"user_message": "Preciso reportar acidente"}
)

# Add reasoning steps
confidence_tracker.add_reasoning_step(
    chain=chain,
    step_type="keyword_analysis",
    description="Analisando palavras-chave",
    input_data={"message": "Preciso reportar acidente"},
    output_data={"keywords": ["reportar", "acidente"]},
    confidence=0.92,
    reasoning="Palavras indicam claramente um relatório de incidente",
    evidence=["'reportar' = ação de documentar", "'acidente' = evento negativo"]
)

# Get user-friendly explanation
user_explanation = chain.get_detailed_explanation()
# Get developer debug info
dev_explanation = confidence_tracker.get_confidence_explanation(chain, for_user=False)
```

**Benefits:**
- ✅ Users understand why the AI made certain choices
- ✅ Developers can debug confidence issues
- ✅ Different confidence levels trigger different behaviors
- ✅ Detailed audit trail for all decisions

---

### **2. 📝 Centralized Prompt Management**

**What it does:**
- Manages all prompts in one place with versioning
- Tracks prompt performance automatically
- Enables A/B testing and optimization
- Provides structured templates with examples

**Example Usage:**
```python
from app.agents.prompts import PromptManager, PromptTemplate, PromptType

# Initialize system
prompt_manager = PromptManager()

# Execute prompt with tracking
result = prompt_manager.execute_prompt(
    template_id="field_extraction_multi_v2",
    llm_function=your_llm_function,
    user_message="João Silva, telefone (11) 99999-9999",
    unfilled_fields="nome, telefone, email"
)

# Get performance metrics
performance = prompt_manager.get_prompt_performance("field_extraction_multi_v2")
print(f"Success rate: {performance['success_rate']:.1%}")
print(f"Avg execution time: {performance['average_execution_time']:.2f}s")
```

**Benefits:**
- ✅ Version control for prompts
- ✅ Performance tracking and optimization
- ✅ Consistent prompt structure across the system
- ✅ Easy A/B testing of different approaches

---

### **3. 🔍 Advanced Execution Tracing**

**What it does:**
- Traces every step of agent execution
- Provides hierarchical view of operations
- Tracks timing, inputs, outputs, and errors
- Enables detailed performance analysis

**Example Usage:**
```python
from app.agents.observability import execution_tracer, TraceEventType, trace_execution

# Use decorator for automatic tracing
@trace_execution(TraceEventType.FIELD_EXTRACTION, "Extract User Fields")
async def extract_fields(user_message):
    # Your extraction logic here
    return extracted_fields

# Or use context manager
with execution_tracer.context.trace_execution(TraceEventType.LLM_CALL, "Form Prediction") as trace:
    response = await llm.invoke(prompt)
    trace.output_data["form_id"] = response.form_id

# Analyze performance
performance = execution_tracer.analyze_performance(session_id)
debug_info = execution_tracer.get_debug_info(session_id)
```

**Benefits:**
- ✅ Complete visibility into agent execution
- ✅ Performance bottleneck identification
- ✅ Error tracking and debugging
- ✅ Hierarchical operation view

---

## 🔧 Integration with Existing System

### **Step 1: Update Form Filler Agent**

```python
# In enhanced_form_filler_agent.py

from app.agents.reasoning import confidence_tracker
from app.agents.observability import execution_tracer, TraceEventType, trace_execution

class EnhancedFormFillerAgent:

    @trace_execution(TraceEventType.FIELD_EXTRACTION, "Multi-Field Extraction")
    async def _extract_multiple_fields_from_message(self, user_message: str):
        # Start reasoning chain
        chain = confidence_tracker.start_reasoning_chain(
            decision_id=f"field_extraction_{uuid.uuid4()}",
            decision_type="field_extraction",
            initial_input={"user_message": user_message}
        )

        # Add reasoning step for field identification
        confidence_tracker.add_reasoning_step(
            chain=chain,
            step_type="field_identification",
            description="Identificando campos na mensagem",
            input_data={"message": user_message},
            output_data={"potential_fields": potential_fields},
            confidence=identification_confidence,
            reasoning="Baseado em padrões de texto e contexto"
        )

        # Your existing extraction logic...

        # Complete reasoning chain
        confidence_tracker.complete_reasoning_chain(chain, extracted_fields)

        return extracted_fields
```

### **Step 2: Update Router Node**

```python
# In agents/nodes/router.py

from app.agents.prompts.templates import PromptLibrary

class RouterNode(BaseNode):

    def __init__(self, session_manager: SessionManager = None):
        super().__init__(NodeType.ROUTER, "router")
        self.prompt_library = PromptLibrary(prompt_manager)

    async def _classify_intent(self, user_message: str) -> str:
        # Use managed prompt instead of hardcoded string
        template_id = self.prompt_library.get_intent_classification_prompt()

        result = prompt_manager.execute_prompt(
            template_id,
            self.llm.ainvoke,
            user_message=user_message
        )

        # Track performance automatically
        return self._parse_intent_response(result.parsed_response)
```

### **Step 3: Update Form Predictor**

```python
# In enhanced_form_predictor_node.py

async def _predict_form_with_confidence(self, user_message: str, available_forms: list):
    # Use enhanced prompt template
    template_id = "form_prediction_enhanced_v2"

    with execution_tracer.context.trace_execution(TraceEventType.LLM_CALL, "Form Prediction") as trace:
        result = prompt_manager.execute_prompt(
            template_id,
            self.llm.ainvoke,
            user_message=user_message,
            available_forms=self._format_forms_for_prompt(available_forms)
        )

        # Parse structured response with reasoning
        response_data = json.loads(result.raw_response)

        # Extract confidence and reasoning
        confidence_score = response_data.get("confidence_score", 0.5)
        reasoning_steps = response_data.get("reasoning_steps", [])

        # Create reasoning chain from LLM response
        chain = confidence_tracker.start_reasoning_chain(
            decision_id=f"form_prediction_{uuid.uuid4()}",
            decision_type="form_prediction",
            initial_input={"user_message": user_message}
        )

        for step_data in reasoning_steps:
            confidence_tracker.add_reasoning_step(
                chain=chain,
                step_type=step_data["step"],
                description=step_data["finding"],
                input_data={"step_input": step_data.get("input", {})},
                output_data={"step_output": step_data.get("output", {})},
                confidence=step_data["confidence"],
                reasoning=step_data["finding"]
            )

        final_result = {
            "form_template_id": response_data["form_id"],
            "confidence_score": confidence_score,
            "reasoning": response_data["explanation"],
            "requires_clarification": response_data.get("requires_clarification", False)
        }

        confidence_tracker.complete_reasoning_chain(chain, final_result)

        return final_result
```

## 🎨 User Experience Improvements

### **Enhanced Bot Responses**

**Before:**
```
Bot: "I found a form for you. Please answer: What's your name?"
```

**After:**
```
Bot: "🟢 Identifiquei que você quer preencher um relatório de incidente de construção (92% de confiança).
      💭 Baseado em: palavras 'acidente' e 'construção' na sua mensagem

      🎯 Já identifiquei algumas informações:
        • Tipo: acidente
        • Local: construção

      Pergunta 1: Qual é seu nome completo?
      Campo opcional (você pode pular dizendo 'pular')"
```

### **Confidence-Aware Interactions**

```python
def generate_response_with_confidence(self, confidence_score: float, message: str):
    level = ConfidenceLevel.from_score(confidence_score)

    if level == ConfidenceLevel.VERY_HIGH:
        return f"✅ {message}"
    elif level == ConfidenceLevel.HIGH:
        return f"🟢 {message} (confiança: {confidence_score:.1%})"
    elif level == ConfidenceLevel.MEDIUM:
        return f"🟡 {message} (confiança moderada: {confidence_score:.1%})"
    else:
        return f"🔴 {message} (baixa confiança: {confidence_score:.1%}) - você poderia ser mais específico?"
```

## 🔧 Developer Tools

### **Debug Dashboard Integration**

```python
# Add to your FastAPI app
from app.agents.observability import execution_tracer

@app.get("/debug/session/{session_id}")
async def get_debug_info(session_id: str):
    debug_info = execution_tracer.get_debug_info(session_id)
    return debug_info

@app.get("/debug/performance/{session_id}")
async def get_performance_analysis(session_id: str):
    performance = execution_tracer.analyze_performance(session_id)
    return performance

@app.get("/debug/confidence-stats")
async def get_confidence_stats():
    stats = confidence_tracker.get_confidence_stats()
    return stats
```

### **Prompt Performance Monitoring**

```python
# Monitor prompt performance
@app.get("/admin/prompts/performance")
async def get_prompt_performance():
    performance_data = {}
    for template_id in prompt_manager.templates:
        performance_data[template_id] = prompt_manager.get_prompt_performance(template_id)
    return performance_data
```

## 📊 Benefits Summary

| Feature | Developer Benefit | User Benefit |
|---------|------------------|--------------|
| **Confidence Scoring** | Debug low-confidence decisions | Understand AI certainty |
| **Reasoning Chains** | Trace decision logic | Get explanations for choices |
| **Prompt Management** | Version control, A/B testing | Consistent, optimized responses |
| **Execution Tracing** | Performance analysis, debugging | Faster, more reliable system |
| **Multi-field Extraction** | Less complex conversation logic | Natural conversation flow |

## 🚀 Getting Started

1. **Run the demo:**
   ```bash
   python demo_enhanced_agents.py
   ```

2. **Integrate step by step:**
   - Start with confidence tracking in form prediction
   - Add prompt management for key templates
   - Implement tracing for debugging
   - Enhance user responses with confidence indicators

3. **Monitor and optimize:**
   - Use debug endpoints to monitor performance
   - Analyze confidence patterns to improve prompts
   - A/B test different prompt versions
   - Track user satisfaction improvements

## 🎯 Next Steps

- [ ] Add visual debugging dashboard
- [ ] Implement automatic prompt optimization
- [ ] Create confidence-based user interface adaptations
- [ ] Add machine learning-based confidence calibration
- [ ] Implement real-time monitoring alerts

---

**The enhanced system provides significantly better debugging capabilities for developers and much more transparent, confidence-aware interactions for users!**