from __future__ import annotations

import importlib.util
import inspect
import logging
import sys
from pathlib import Path

from plugin.base import Plugin
from plugin.registry import ToolRegistry

logger = logging.getLogger(__name__)

# 内置插件目录
_DEFAULT_BUILTINS_DIR = str(Path(__file__).resolve().parent.parent / 'builtins')


class PluginManager:
    """插件管理器：扫描目录加载内置和外部插件"""

    def __init__(self, builtins_dir: str | None = None) -> None:
        self._plugins: list[Plugin] = []
        self._registry = ToolRegistry()
        self._builtins_dir = builtins_dir or _DEFAULT_BUILTINS_DIR

    @property
    def plugins(self) -> list[Plugin]:
        return self._plugins

    @property
    def tool_registry(self) -> ToolRegistry:
        return self._registry

    # ── 目录发现 ─────────────────────────────────────

    def discover_from_dir(self, plugin_dir: Path) -> type[Plugin] | None:
        """从插件目录动态加载，返回第一个 Plugin 子类"""
        if not plugin_dir.is_dir():
            return None
        init_file = plugin_dir / '__init__.py'
        if not init_file.is_file():
            return None

        safe_suffix = ''.join(c if c.isalnum() or c == '_' else '_' for c in plugin_dir.name)
        module_name = f'_ext_plugin_{safe_suffix}'

        if module_name not in sys.modules:
            spec = importlib.util.spec_from_file_location(
                module_name,
                str(init_file),
                submodule_search_locations=[str(plugin_dir)],
            )
            if spec is None or spec.loader is None:
                return None
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

        module = sys.modules[module_name]
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if obj is not Plugin and issubclass(obj, Plugin):
                return obj

        logger.warning('目录 %s 中未找到 Plugin 子类', plugin_dir)
        return None

    # ── 加载入口 ────────────────────────────────────────

    async def load_all(self, external_dirs: list[str] | None = None) -> list[Plugin]:
        """加载所有插件：内置（builtins/）→ 外部（目录扫描）"""
        loaded: list[Plugin] = []

        # 1. 内置插件：扫描 builtins/
        builtins_root = Path(self._builtins_dir).resolve()
        if builtins_root.is_dir():
            for subdir in sorted(builtins_root.iterdir()):
                plugin = await self._load_plugin_from_dir(subdir)
                if plugin is not None:
                    loaded.append(plugin)

        # 2. 外部插件：扫描 external_dirs
        if external_dirs:
            for dir_path in external_dirs:
                root = Path(dir_path).resolve()
                if not root.is_dir():
                    logger.warning('外部插件目录 %s 不存在，跳过', root)
                    continue
                for subdir in sorted(root.iterdir()):
                    plugin = await self._load_plugin_from_dir(subdir)
                    if plugin is not None:
                        loaded.append(plugin)

        return loaded

    async def _load_plugin_from_dir(self, plugin_dir: Path) -> Plugin | None:
        """从单个目录尝试加载插件，成功返回 Plugin 实例"""
        name = plugin_dir.name

        if name.startswith('.'):
            return None
        if not plugin_dir.is_dir():
            return None
        if not (plugin_dir / '__init__.py').is_file():
            logger.debug('目录 %s 不是 Python 包（缺少 __init__.py），跳过', plugin_dir)
            return None

        cls = self.discover_from_dir(plugin_dir)
        if cls is None:
            return None

        try:
            inst = cls()
            config = None
            cfg_cls = getattr(cls, 'Config', None)
            if cfg_cls is not None and inspect.isclass(cfg_cls):
                try:
                    from doudou_agent_sdk import PluginConfig

                    if issubclass(cfg_cls, PluginConfig):
                        config = cfg_cls()
                except ImportError:
                    pass

            await inst.on_load(config)

            tools = inst.register_tools()
            for tool in tools:
                self._registry.register(tool)
            self._plugins.append(inst)
            logger.info("插件 '%s' 加载成功，注册 %d 个工具", inst.name, len(tools))
            return inst
        except Exception:
            logger.exception('插件 %s 加载失败', name)
            return None

    # ── 生命周期 ────────────────────────────────────────

    async def shutdown(self) -> None:
        for plugin in self._plugins:
            try:
                await plugin.on_shutdown()
            except Exception:
                logger.exception("插件 '%s' 关闭时出错", plugin.name)
