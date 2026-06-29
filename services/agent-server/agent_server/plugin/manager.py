from __future__ import annotations

import logging
from importlib.metadata import EntryPoint, entry_points
from typing import Any

from agent_server.plugin.base import Plugin
from agent_server.plugin.registry import ToolRegistry

logger = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "doudou_agent.plugins"


class PluginManager:
    """通过 entry_points 发现、加载、管理插件生命周期"""

    def __init__(self) -> None:
        self._plugins: list[Plugin] = []
        self._registry = ToolRegistry()

    @property
    def plugins(self) -> list[Plugin]:
        return self._plugins

    @property
    def tool_registry(self) -> ToolRegistry:
        return self._registry

    def discover(self) -> list[type[Plugin]]:
        """发现所有通过 entry_point 注册的插件类"""
        discovered: list[type[Plugin]] = []
        eps: list[EntryPoint] = []

        try:
            eps = list(entry_points(group=ENTRY_POINT_GROUP))
        except TypeError:
            all_eps = entry_points()
            eps = list(all_eps.get(ENTRY_POINT_GROUP, []))

        for ep in eps:
            plugin_cls = ep.load()
            if issubclass(plugin_cls, Plugin):
                discovered.append(plugin_cls)
                logger.info("发现插件: %s (%s)", ep.name, plugin_cls.__name__)

        return discovered

    async def load_enabled(self, plugin_configs: list[dict[str, Any]]) -> list[Plugin]:
        """加载配置中 enabled 的插件"""
        enabled_names = {pc["name"] for pc in plugin_configs if pc.get("enabled", True)}
        configs_by_name = {pc["name"]: pc.get("config", {}) for pc in plugin_configs}

        discovered = self.discover()

        loaded: list[Plugin] = []
        for cls in discovered:
            plugin_instance = cls()
            name = plugin_instance.name
            if name not in enabled_names:
                logger.info("插件 '%s' 不在启用列表中，跳过", name)
                continue

            config = configs_by_name.get(name, {})
            await plugin_instance.on_load(config)

            tools = plugin_instance.register_tools()
            for tool in tools:
                self._registry.register(tool)

            self._plugins.append(plugin_instance)
            loaded.append(plugin_instance)
            logger.info("插件 '%s' 加载成功，注册 %d 个工具", name, len(tools))

        return loaded

    async def shutdown(self) -> None:
        for plugin in self._plugins:
            try:
                await plugin.on_shutdown()
            except Exception:
                logger.exception("插件 '%s' 关闭时出错", plugin.name)
