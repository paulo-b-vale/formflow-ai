# app/utils/langchain_utils.py
from langchain_google_genai import ChatGoogleGenerativeAI
from app.config.settings import settings
import logging
from app.utils.cost_tracker import CostTrackingCallback

logger = logging.getLogger(__name__)

def get_gemini_llm() -> ChatGoogleGenerativeAI:
    """
    Initializes and returns the Gemini LLM client with cost tracking.
    """
    api_key = settings.GEMINI_API_KEY
    logger.info("Initializing Gemini LLM...")

    if not api_key or api_key == "YOUR_GOOGLE_AI_API_KEY_HERE":
        logger.warning("GEMINI_API_KEY is not set. Using MockLLM for local testing.")
        return MockLLM()

    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0.1,
            convert_system_message_to_human=True,
            callbacks=[CostTrackingCallback()] # <-- Cost tracking is integrated here
        )
        logger.info("Successfully initialized real Gemini LLM.")
        return llm
    except Exception as e:
        logger.error(f"Failed to initialize real Gemini LLM: {e}")
        logger.warning("Falling back to MockLLM due to an initialization error.")
        return MockLLM()

class MockLLM:
    """Mock LLM for testing when the real API is not available."""
    def invoke(self, prompt: str):
        prompt_lower = prompt.lower()
        if "patient vitals" in prompt_lower or "vitals check" in prompt_lower:
            content = '{"intent": "fill_form", "confidence": 0.9, "reasoning": "User wants to fill a form", "extracted_entities": {}}'
        elif "show me" in prompt_lower or "find" in prompt_lower:
            content = '{"intent": "query_forms", "confidence": 0.8, "reasoning": "User wants to query forms", "extracted_entities": {}}'
        else:
            content = '{"intent": "unclear", "confidence": 0.3, "reasoning": "Intent unclear", "extracted_entities": {}}'

        class MockResponse:
            def __init__(self, content):
                self.content = content
        return MockResponse(content)

    async def ainvoke(self, prompt: str):
        return self.invoke(prompt)