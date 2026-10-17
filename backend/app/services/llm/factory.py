from app.config import LLM_PROVIDER, OPENAI_API_KEY, GEMINI_API_KEY
from app.services.llm.provider import BaseLLMProvider
from app.services.llm.heuristic_provider import HeuristicLLMProvider
from app.services.llm.openai_provider import OpenAIProvider
from app.services.llm.gemini_provider import GeminiProvider

def get_llm_provider() -> BaseLLMProvider:
    provider_name = (LLM_PROVIDER or "").lower().strip()
    if provider_name == "openai" and OPENAI_API_KEY:
        return OpenAIProvider(api_key=OPENAI_API_KEY)
    elif provider_name == "gemini" and GEMINI_API_KEY:
        return GeminiProvider(api_key=GEMINI_API_KEY)
    else:
        return HeuristicLLMProvider()

llm_service = get_llm_provider()
