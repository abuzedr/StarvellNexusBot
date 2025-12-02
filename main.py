import asyncio
import logging
import logging.config
import os
import sys
import hashlib
from contextlib import suppress

REQUIRED_PACKAGES = ["lxml", "bcrypt", "colorama", "aiogram"]


def check_dependencies() -> None:
    missing = []
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"[!] Не хватает: {', '.join(missing)}")
        print(f"    pip install {' '.join(missing)}")
        sys.exit(1)


check_dependencies()

from colorama import Fore, Style, init as colorama_init
colorama_init(autoreset=True)

from Utils.updater import Updater

VERSION = "0.1.0-beta"

logo = r"""
+------------------------------------------------+
|                                                |
|                S T A R V E L L                 |
|                     B O T                      |
|                                                |
+------------------------------------------------+
                         [ @AnastasiaPisun ]
"""

print(f"{Style.RESET_ALL}{Fore.CYAN}{logo}{Style.RESET_ALL}")
print(f"{Fore.RED}{Style.BRIGHT}v{VERSION}{Style.RESET_ALL}\n")

import config_loader as cfg_loader
from nexus import Nexus
from tg_bot.aio_bot import AioTGBot
from core.plugin_manager import PluginManager
from StarVellAPI.account import Account as StarVellAPI
from aiogram.types import BotCommand

def setup_logging(level: str = "INFO"):
    try:
        from Utils.logger import get_logger_config
        logging.config.dictConfig(get_logger_config(level))
    except Exception:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s │ %(message)s", datefmt="%H:%M:%S")
    logging.raiseExceptions = False

setup_logging("INFO")
logger = logging.getLogger("StarVell.Main")


async def start_aiogram_bot(nexus: Nexus, cfg, context: dict) -> None:
    def cfg_get(section: str, option: str, fallback=None):
        if isinstance(cfg, dict):
            return cfg.get(section, {}).get(option, fallback)
        try:
            return cfg.get(section, option, fallback=fallback)
        except Exception:
            return fallback

    notifications_enabled = str(cfg_get("Telegram", "notifications", "true")).lower() in {"1", "true", "yes", "on"}
    if not notifications_enabled:
        logger.info("🤖 Telegram-бот отключён в конфигурации.")
        return

    token = (cfg_get("Telegram", "bot_token", "") or "").strip()
    admin_id_str = (cfg_get("Telegram", "admin_id", "0") or "0").strip()
    password = (cfg_get("Telegram", "password", "") or "admin").strip()

    # Поддержка нескольких админов через запятую
    admin_ids = []
    for part in admin_id_str.replace(" ", "").split(","):
        try:
            if part:
                admin_ids.append(int(part))
        except ValueError:
            pass
    
    main_admin_id = admin_ids[0] if admin_ids else 0

    if not token or main_admin_id == 0:
        logger.warning("⚠️ Не задан Telegram токен или admin_id — бот не будет запущен.")
        return

    password_md5 = hashlib.md5(password.encode()).hexdigest()
    aio_bot = AioTGBot(token, main_admin_id, nexus, password_md5, admin_ids=admin_ids)
    nexus.telegram = aio_bot

    context["dispatcher"] = aio_bot.dp
    context["bot"] = aio_bot.bot

    try:
        plugin_manager = PluginManager(context)
        nexus.plugin_manager = plugin_manager
        plugin_manager.load_plugins()

        commands = [
            BotCommand(command="start", description="Главное меню"),
            BotCommand(command="update", description="Проверка обновлений"),
        ]
        await aio_bot.bot.set_my_commands(commands)
        
        logger.info("✅ Telegram бот готов")
    except Exception as e:
        logger.error("💥 Плагины: %s", e)

    await aio_bot.run()


async def main() -> None:
    MAIN_CFG = cfg_loader.load_or_setup_config()

    try:
        log_level = MAIN_CFG.get("Other", {}).get("log_level", "INFO").upper()
    except Exception:
        log_level = "INFO"
    logging.getLogger().setLevel(log_level)
    
    github_token = MAIN_CFG.get("Updates", {}).get("github_token", "")
    updater = Updater(VERSION, github_token if github_token else None)
    
    print(f"{Fore.CYAN}🔍 Проверка обновлений...{Style.RESET_ALL}")
    update_info = await updater.check_updates()
    
    if update_info.get("available"):
        print(f"\n{Fore.YELLOW}{'='*50}")
        print(f"🆕 НАЙДЕНО ОБНОВЛЕНИЕ: v{VERSION} → v{update_info['version']}")
        print(f"{'='*50}{Style.RESET_ALL}")
        
        if update_info.get("changelog"):
            print(f"{Fore.WHITE}Изменения:{Style.RESET_ALL}")
            print(f"{Style.DIM}{update_info['changelog'][:300]}{Style.RESET_ALL}\n")
        
        print(f"{Fore.GREEN}📥 Скачиваю обновление...{Style.RESET_ALL}")
        
        if await updater.auto_update():
            print(f"\n{Fore.GREEN}{'='*50}")
            print(f"✅ ОБНОВЛЕНИЕ УСТАНОВЛЕНО!")
            print(f"🔄 Перезапуск через 3 секунды...")
            print(f"{'='*50}{Style.RESET_ALL}\n")
            await asyncio.sleep(3)
            Updater.restart_bot()
        else:
            print(f"{Fore.RED}❌ Ошибка обновления. Продолжаю с текущей версией.{Style.RESET_ALL}\n")
    elif update_info.get("error"):
        logger.debug(f"Проверка обновлений: {update_info['error']}")
        print(f"{Fore.GREEN}✓ Версия актуальна (v{VERSION}){Style.RESET_ALL}\n")
    else:
        print(f"{Fore.GREEN}✓ Версия актуальна (v{VERSION}){Style.RESET_ALL}\n")

    starvell_section = MAIN_CFG.get("StarVell", {})
    session_id = (starvell_section.get("session") or starvell_section.get("session_id") or "").strip()
    
    try:
        api = StarVellAPI(session_id=session_id) if session_id else None
    except Exception as e:
        logger.warning("⚠️ StarVellAPI: %s", e)
        api = None

    from Utils.exceptions import StarVellBotException

    nexus = None
    try:
        nexus = Nexus(MAIN_CFG, {}, {}, {}, VERSION).init()
    except StarVellBotException as e:
        logger.warning("⚠️ %s", e)
        nexus = Nexus(MAIN_CFG, {}, {}, {}, VERSION)
        nexus.account = None
    except Exception as e:
        logger.error("💥 Nexus: %s", e)
        nexus = Nexus(MAIN_CFG, {}, {}, {}, VERSION)
        nexus.account = None

    if not hasattr(nexus, "plugins") or nexus.plugins is None:
        nexus.plugins = {}

    context: dict = {"config": MAIN_CFG, "nexus": nexus, "api": api}
    tg_task = None

    try:
        tg_task = asyncio.create_task(start_aiogram_bot(nexus, MAIN_CFG, context))
        
        runner_task = asyncio.create_task(run_event_runner(nexus))

        done, pending = await asyncio.wait(
            [tg_task, runner_task],
            return_when=asyncio.FIRST_EXCEPTION
        )
        
        for task in pending:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.critical("💥 %s", e, exc_info=True)


async def run_event_runner(nexus: Nexus):
    """Запускает Runner для получения событий StarVell"""
    logger.info("🔄 Event Runner: ожидание активной сессии...")
    
    while True:
        try:
            account = getattr(nexus, "account", None)
            is_initiated = getattr(account, "is_initiated", False) if account else False
            
            if not is_initiated:
                await asyncio.sleep(5)
                continue
            
            if hasattr(account, "runner") and account.runner:
                account.runner = None
            nexus.runner = None
            
            logger.info("🚀 Event Runner: запуск...")
            await nexus.run()
            
        except asyncio.CancelledError:
            logger.info("🛑 Event Runner: остановлен")
            break
        except Exception as e:
            logger.error(f"💥 Event Runner: {e}")
            await asyncio.sleep(10)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Программа принудительно завершена.")
