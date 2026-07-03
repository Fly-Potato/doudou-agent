# tests/test_plugin_manager.py
from __future__ import annotations

from pathlib import Path

import pytest

from plugin.base import Tool
from plugin.manager import PluginManager
from plugin.registry import ToolRegistry

from .conftest import DummyPlugin


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


_PLUGIN_CODE = """
from doudou_agent_sdk import Plugin, Tool

class TestPlugin(Plugin):
    name = "test-plugin"

    def register_tools(self) -> list[Tool]:
        async def hello(session_id: str, **kw):
            return {"msg": "hello"}
        return [
            Tool(
                name="hello",
                description="say hello",
                parameters={"type": "object", "properties": {}},
                handler=hello,
            )
        ]
"""


class TestPluginManager:
    @pytest.mark.asyncio
    async def test_load_builtin_plugins(self, tmp_path: Path) -> None:
        """内置插件从 builtins/ 目录被正确扫描加载"""
        plugin_dir = tmp_path / 'my-builtin'
        plugin_dir.mkdir()
        (plugin_dir / '__init__.py').write_text(_PLUGIN_CODE)

        mgr = PluginManager(builtins_dir=str(tmp_path))
        loaded = await mgr.load_all()
        assert len(loaded) == 1
        assert loaded[0].name == 'test-plugin'
        assert 'hello' in mgr.tool_registry

    @pytest.mark.asyncio
    async def test_builtins_dir_not_exists(self) -> None:
        """builtins/ 目录不存在时不报错"""
        mgr = PluginManager(builtins_dir='C:\\nonexistent_path_for_test')
        loaded = await mgr.load_all()
        assert len(loaded) == 0

    @pytest.mark.asyncio
    async def test_external_plugin_loads_from_dir(self, tmp_path: Path) -> None:
        """外部插件能从包含 __init__.py 的目录成功加载"""
        plugin_dir = tmp_path / 'my-external-test'
        plugin_dir.mkdir()
        (plugin_dir / '__init__.py').write_text(_PLUGIN_CODE)

        mgr = PluginManager(builtins_dir=str(tmp_path / 'empty-builtins'))
        loaded = await mgr.load_all(external_dirs=[str(tmp_path)])
        assert len(loaded) == 1
        assert loaded[0].name == 'test-plugin'
        assert 'hello' in mgr.tool_registry

    @pytest.mark.asyncio
    async def test_skip_dot_prefixed_directory(self, tmp_path: Path) -> None:
        """以 . 开头的目录被跳过"""
        (tmp_path / '.disabled').mkdir()
        mgr = PluginManager(builtins_dir=str(tmp_path))
        loaded = await mgr.load_all()
        assert len(loaded) == 0

    @pytest.mark.asyncio
    async def test_skip_directory_without_init_py(self, tmp_path: Path) -> None:
        """缺少 __init__.py 的目录被跳过"""
        no_init = tmp_path / 'no-init'
        no_init.mkdir()
        mgr = PluginManager(builtins_dir=str(tmp_path))
        loaded = await mgr.load_all()
        assert len(loaded) == 0

    @pytest.mark.asyncio
    async def test_skip_non_directory_entry(self, tmp_path: Path) -> None:
        """目录中的普通文件被跳过"""
        (tmp_path / 'some_file.txt').write_text('not a dir')
        mgr = PluginManager(builtins_dir=str(tmp_path))
        loaded = await mgr.load_all()
        assert len(loaded) == 0
