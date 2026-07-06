from agent.llm.base import LLMProvider
from agent.llm.openai import OpenAIProvider
from config import LLMConfig


def create_provider(config: LLMConfig) -> LLMProvider:
    if config.type == 'openai':
        return OpenAIProvider(
            model=config.model,
            base_url=config.base_url,
        )
    raise ValueError(f'不支持的 LLM 类型: {config.type}')


__all__ = ['LLMProvider', 'create_provider']
