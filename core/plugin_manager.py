import importlib
import logging
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("PluginManager")


class PluginManager:
    """
    1. attach(dp=Dispatcher, bot=Bot, context=dict)
    2. register(cardinal)
    3. Plugin class
    """

    def __init__(self, context: Optional[dict] = None, plugins_dir: str = "plugins") -> None:
        self.context: dict = context or {}
        self.plugins_dir: str = plugins_dir
        self.plugins: Dict[str, Any] = {}
        self.routers = []

    # ------------------------------------------------------------------

    def load_plugins(self) -> Dict[str, Any]:
        path = Path(self.plugins_dir)
        if not path.exists():
            logger.warning("⚠️ Папка %s не найдена, создаю...", self.plugins_dir)
            path.mkdir(parents=True, exist_ok=True)
            return self.plugins

        for file in path.glob("*.py"):
            module_name = file.stem
            if module_name.startswith("_"):
                continue

            try:
                logger.info("🧩 Загружаю плагин: %s", module_name)
                module = importlib.import_module(f"{self.plugins_dir}.{module_name}")

                if hasattr(module, "attach"):
                    nexus = self.context.get("nexus")
                    dp = self.context.get("dispatcher")
                    bot = self.context.get("bot")

                    if dp is None:
                        logger.error("❌ Плагин %s: dp не передан", module_name)
                    else:
                        try:
                            module.attach(dp=dp, bot=bot, context=self.context)
                        except Exception as e:
                            logger.error("❌ Ошибка attach() %s: %s", module_name, e)
                            traceback.print_exc()
                        else:
                            if nexus is not None and hasattr(nexus, "plugins"):
                                for key, plugin_inst in getattr(nexus, "plugins", {}).items():
                                    if key not in self.plugins:
                                        self.plugins[key] = plugin_inst
                                        logger.info("✅ %s загружен (attach)", key)
                    continue

                if hasattr(module, "register"):
                    nexus = self.context.get("nexus")
                    if nexus is not None:
                        try:
                            module.register(nexus)
                        except Exception as e:
                            logger.error("❌ Ошибка register() %s: %s", module_name, e)
                            traceback.print_exc()
                        else:
                            if hasattr(nexus, "plugins"):
                                for key, plugin_inst in getattr(nexus, "plugins", {}).items():
                                    if key not in self.plugins:
                                        self.plugins[key] = plugin_inst
                            self.plugins[module_name] = module
                            logger.info("✅ %s зарегистрирован (register)", module_name)
                    else:
                        logger.error("❌ Плагин %s: nexus не найден в контексте", module_name)
                    continue

                if hasattr(module, "Plugin"):
                    try:
                        plugin = module.Plugin(self.context)  # type: ignore[call-arg]
                    except Exception as e:  # noqa: BLE001
                        logger.error("❌ Ошибка при создании Plugin из %s: %s", module_name, e)
                        traceback.print_exc()
                    else:
                        self.plugins[module_name] = plugin
                        plugin_name = getattr(plugin, "name", module_name)
                        logger.info("✅ %s загружен (class-style)", plugin_name)
                    continue

                logger.warning("⚠️ В %s.py нет attach/register/Plugin — пропускаю", module_name)

            except Exception as e:  # noqa: BLE001
                logger.error("❌ Ошибка при загрузке %s: %s", module_name, e)
                traceback.print_exc()

        logger.info("🔗 Загружено плагинов: %s", len(self.plugins))
        return self.plugins

    # ------------------------------------------------------------------

    def get_plugin(self, name: str) -> Optional[Any]:
        """Получить плагин по имени или по популярным алиасам."""
        return (
            self.plugins.get(name)
            or self.plugins.get(f"{name}_pro")
            or self.plugins.get("create_lot_pro")
            or self.plugins.get("create_lot")
        )

    # ------------------------------------------------------------------

    def unload_plugin(self, name: str) -> None:
        """Выгрузить (отключить) плагин по имени."""
        if name in self.plugins:
            del self.plugins[name]
            logger.info("🧹 Плагин %s выгружен", name)
