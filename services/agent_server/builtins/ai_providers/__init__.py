from agent.llm.openai import OpenAICompatibleProvider
from plugin.base import Plugin, Tool


class DeepSeekProvider(OpenAICompatibleProvider):
    id = 'deepseek'
    base_url = 'https://api.deepseek.com/v1'


class AIProvidersPlugin(Plugin):
    """内置 AI 服务商接入：提供 LLM Provider 注册"""

    name = 'ai-providers'
    version = '0.1.0'
    description = '内置 AI 服务商接入：DeepSeek'

    def register_tools(self) -> list[Tool]:
        return []

    def register_providers(self) -> list[OpenAICompatibleProvider]:
        return [DeepSeekProvider()]
