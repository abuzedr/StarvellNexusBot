import os
import logging
import asyncio
import hashlib
from contextlib import suppress

from Utils import config_loader
from nexus import Nexus
from tg_bot.aio_bot import AioTGBot
from core.plugin_manager import PluginManager
from StarVellAPI.account import Account as StarVellAPI
from aiogram.types import BotCommand

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("StarVell.Main")

CFG_PATH = "configs/_main.cfg"


def ensure_configs() -> dict:
    if not os.path.exists(CFG_PATH):
        os.makedirs("configs", exist_ok=True)
        import configparser
        cfg = configparser.ConfigParser()
        cfg["StarVell"] = {"session": ""}
        cfg["Telegram"] = {"bot_token": "", "admin_id": "0", "notifications": "true", "password": "admin"}
        cfg["Other"] = {"language": "ru", "log_level": "INFO"}
        with open(CFG_PATH, "w", encoding="utf-8") as f:
            cfg.write(f)
        logger.info("🆕 Создан конфиг configs/_main.cfg")
    return config_loader.load_main_config(CFG_PATH)


async def start_aiogram_bot(nexus: Nexus, cfg: dict, context: dict) -> None:
    tg_cfg = cfg.get("Telegram", {})
    token = (tg_cfg.get("bot_token") or "").strip()
    admin_id_str = (tg_cfg.get("admin_id") or "0").strip()
    password = (tg_cfg.get("password") or "admin").strip()

    try:
        admin_id = int(admin_id_str)
    except Exception:
        admin_id = 0

    if not token or admin_id == 0:
        logger.warning("⚠️ Не задан Telegram токен или admin_id")
        return

    password_md5 = hashlib.md5(password.encode()).hexdigest()
    aio_bot = AioTGBot(token, admin_id, nexus, password_md5)
    nexus.telegram = aio_bot

    context["dispatcher"] = aio_bot.dp
    context["bot"] = aio_bot.bot

    try:
        plugin_manager = PluginManager(context)
        nexus.plugin_manager = plugin_manager
        plugin_manager.load_plugins()
        logger.info("✅ Плагины загружены")

        commands = [
            BotCommand(command="start", description="Главное меню"),
            BotCommand(command="status", description="Статус бота"),
        ]
        await aio_bot.bot.set_my_commands(commands)
        logger.info("✅ Telegram-команды зарегистрированы")

        nexus._send_tg("🤖 Telegram-бот подключён")
        logger.info("✅ Telegram подключён")

    except Exception as e:
        logger.error("💥 Ошибка: %s", e, exc_info=True)

    logger.info("🚀 Запуск aiogram...")
    await aio_bot.run()


async def main():
    print("🚀 Запуск StarVell Bot...\n")

    cfg = ensure_configs()

    try:
        nexus = Nexus(cfg, {}, {}, {}, "1.0.0").init()
        logger.info("✅ Nexus инициализирован")
    except Exception as e:
        logger.warning("⚠️ Ошибка инициализации: %s", e)
        nexus = Nexus(cfg, {}, {}, {}, "1.0.0")
        nexus.running = False

    if not hasattr(nexus, "plugins"):
        nexus.plugins = {}

    starvell_section = cfg.get("StarVell", {})
    session_id = (starvell_section.get("session") or starvell_section.get("session_id") or "").strip()

    if not session_id:
        logger.warning("⚠️ Не указан session_id")

    api = StarVellAPI(session_id=session_id) if session_id else None

    context = {
        "cfg": cfg,
        "nexus": nexus,
        "api": api,
    }

    tg_task = asyncio.create_task(start_aiogram_bot(nexus, cfg, context))
    logger.info("🤖 Telegram запускается")

    if nexus and nexus.account and getattr(nexus.account, "is_initiated", False):
        logger.info("🔧 Запуск Nexus...")
        try:
            await nexus.run()
        except asyncio.CancelledError:
            logger.info("🛑 Остановка по Ctrl+C")
        except Exception as e:
            logger.error("💥 Ошибка: %s", e, exc_info=True)
        finally:
            if not tg_task.done():
                tg_task.cancel()
                with suppress(asyncio.CancelledError):
                    await tg_task
    else:
        logger.warning("⚠️ Сессия не активна")
        print("⚠️ Обновите сессию через /start в Telegram.")
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            logger.info("🛑 Завершение")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Завершение по Ctrl+C")
    except Exception as e:
        logger.critical("💥 Фатальная ошибка: %s", e, exc_info=True)
