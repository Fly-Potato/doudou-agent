from pydantic import BaseModel


class PluginConfig(BaseModel):
    """插件配置基类 — 子类继承声明字段后可获得类型校验和自动补全。

    示例：
        from doudou_agent_sdk import Plugin, PluginConfig

        class TodoPlugin(Plugin):
            class Config(PluginConfig):
                db_url: str = "sqlite:///todos.db"
                max_items: int = 100
    """

    pass
