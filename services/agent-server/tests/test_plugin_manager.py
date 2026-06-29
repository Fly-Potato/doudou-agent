# tests/test_plugin_manager.py
from __future__ import annotations

from unittest.mock import patch

import pytest

from agent_server.plugin.base import Tool
from agent_server.plugin.manager import PluginManager
from agent_server.plugin.registry import ToolRegistry
from tests.conftest import DummyPlugin


class SimplePlugin(DummyPlugin):
    """覆盖 name 用于测试区分"""

    @property
    def name(self) -> str:
        return 'simple'


class TestToolRegistry:
    def test_register_and_get(self) -> None:
        registry = ToolRegistry()
        tool = Tool(
            name='test_tool',
            description='测试工具',
            parameters={'type': 'object', 'properties': {}},
            handler=lambda session_id, **kw: None,
        )
        registry.register(tool)
        assert registry.get('test_tool') is tool
        assert len(registry) == 1

    def test_duplicate_tool_warns(self, caplog) -> None:
        registry = ToolRegistry()
        tool_a = Tool(
            name='dup',
            description='a',
            parameters={'type': 'object', 'properties': {}},
            handler=lambda session_id, **kw: None,
        )
        tool_b = Tool(
            name='dup',
            description='b',
            parameters={'type': 'object', 'properties': {}},
            handler=lambda session_id, **kw: None,
        )
        registry.register(tool_a)
        registry.register(tool_b)
        assert '被覆盖' in caplog.text
        assert registry.get('dup') is tool_b

    def test_list_definitions(self) -> None:
        registry = ToolRegistry()
        tool = Tool(
            name='echo',
            description='回显',
            parameters={'type': 'object', 'properties': {'x': {'type': 'string'}}},
            handler=lambda session_id, **kw: None,
        )
        registry.register(tool)
        defs = registry.list_definitions()
        assert len(defs) == 1
        assert defs[0]['type'] == 'function'
        assert defs[0]['function']['name'] == 'echo'

    def test_contains(self) -> None:
        registry = ToolRegistry()
        tool = Tool(
            name='a',
            description='',
            parameters={'type': 'object', 'properties': {}},
            handler=lambda session_id, **kw: None,
        )
        registry.register(tool)
        assert 'a' in registry
        assert 'b' not in registry


class TestPluginManager:
    @pytest.mark.asyncio
    async def test_load_enabled_plugin(self) -> None:
        with patch.object(PluginManager, 'discover', return_value=[DummyPlugin]):
            mgr = PluginManager()
            loaded = await mgr.load_enabled([{'name': 'dummy', 'enabled': True, 'config': {}}])
            assert len(loaded) == 1
            assert loaded[0].name == 'dummy'
            assert loaded[0]._load_called
            assert len(mgr.tool_registry) == 1

    @pytest.mark.asyncio
    async def test_skip_disabled_plugin(self) -> None:
        with patch.object(PluginManager, 'discover', return_value=[DummyPlugin]):
            mgr = PluginManager()
            loaded = await mgr.load_enabled([{'name': 'dummy', 'enabled': False}])
            assert len(loaded) == 0
            assert len(mgr.tool_registry) == 0

    @pytest.mark.asyncio
    async def test_plugin_not_in_config_is_skipped(self) -> None:
        with patch.object(PluginManager, 'discover', return_value=[SimplePlugin]):
            mgr = PluginManager()
            loaded = await mgr.load_enabled([{'name': 'other_plugin', 'enabled': True}])
            assert len(loaded) == 0
