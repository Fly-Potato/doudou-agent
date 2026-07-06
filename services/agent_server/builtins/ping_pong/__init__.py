from doudou_agent_sdk import Plugin, Tool


class PingPongPlugin(Plugin):
    """内置 ping-pong 示例插件"""

    name = 'ping-pong'
    version = '0.1.0'
    description = '演示插件开发流程的最小示例'

    def register_tools(self) -> list[Tool]:
        async def ping(session_id: str, **params: object) -> dict[str, object]:
            return {
                'pong': True,
                'message': params.get('message', ''),
            }

        return [
            Tool(
                name='ping',
                description='检查插件可用性，返回 pong 确认',
                parameters={
                    'type': 'object',
                    'properties': {
                        'message': {
                            'type': 'string',
                            'description': '回显的自定义消息（可选）',
                        },
                    },
                },
                handler=ping,
            ),
        ]
