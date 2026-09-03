from app.core.config import settings
from app.modules.research.enums import ResearchProviderName
from app.modules.research.providers.base import ResearchProvider
from app.modules.research.providers.mock import MockResearchProvider
from app.modules.research.providers.openai_provider import OpenAIResearchProvider


def get_research_provider(provider_name: ResearchProviderName) -> ResearchProvider:
    if provider_name == ResearchProviderName.OPENAI:
        return OpenAIResearchProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_research_model,
        )
    return MockResearchProvider()
