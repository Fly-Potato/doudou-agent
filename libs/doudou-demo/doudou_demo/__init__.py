from doudou_agent_sdk import Plugin, PluginConfig, Tool


class DemoConfig(PluginConfig):
    """插件配置：支持自定义 greeting 消息"""

    greeting: str = '你好，我是 Demo 插件！'


class DemoPlugin(Plugin):
    """最小插件示例 — 提供一个 ping 工具和一则 Greeting"""

    name = 'doudou-demo'
    version = '0.1.0'
    description = 'doudou-agent 最小插件示例，演示插件开发流程'

    def register_tools(self) -> list[Tool]:
        async def ping(session_id: str, **params) -> dict:
            return {
                'pong': True,
                'message': params.get('message', ''),
            }

        return [
            Tool(
                name='ping',
                description='检查插件可用性，返回确认信息',
                parameters={
                    'type': 'object',
                    'properties': {
                        'message': {
                            'type': 'string',
                            'description': '自定义消息（可选）',
                        },
                    },
                },
                handler=ping,
            ),
        ]

    async def on_load(self, config: DemoConfig | None = None) -> None:
        if config is None:
            config = DemoConfig()
        self._greeting = config.greeting
