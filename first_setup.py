import os
import sys
import subprocess
import threading
import configparser
import time

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
except ImportError:
    class Fore:
        RED = YELLOW = GREEN = CYAN = MAGENTA = WHITE = RESET = ""
    class Style:
        BRIGHT = DIM = RESET_ALL = ""

VERSION = "0.1.0-beta"

LOGO = f"""
{Fore.CYAN}    ╔═══════════════════════════════════════════════════════════════════╗
    ║                                                                   ║
    ║      ███████╗████████╗ █████╗ ██████╗ ██╗   ██╗███████╗██╗ ██╗    ║
    ║      ██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██║   ██║██╔════╝██║ ██║    ║
    ║      ███████╗   ██║   ███████║██████╔╝██║   ██║█████╗  ██║ ██║    ║
    ║      ╚════██║   ██║   ██╔══██║██╔══██╗╚██╗ ██╔╝██╔══╝  ██║ ██║    ║
    ║      ███████║   ██║   ██║  ██║██║  ██║ ╚████╔╝ ███████╗██║ ██║    ║
    ║      ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚══════╝╚═╝ ╚═╝    ║
    ║                         B O T                                     ║
    ║                                                                   ║
    ╠═══════════════════════════════════════════════════════════════════╣
    ║                    v{VERSION}  •  @AnastasiaPisun                      ║
    ╚═══════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}"""

PACKAGES = ["aiogram>=3.6.0", "aiohttp", "aiosqlite", "requests", "lxml", "beautifulsoup4", "colorama", "bcrypt"]
deps_ready = False


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def install_deps_background():
    global deps_ready
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "--disable-pip-version-check"] + PACKAGES,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception:
        pass
    deps_ready = True


def create_dirs():
    for d in ["configs", "logs", "storage", "storage/cache", "storage/plugins", "storage/products", "plugins", "plugins/utils"]:
        os.makedirs(d, exist_ok=True)


def ask(prompt: str, required: bool = True, validator=None, hint: str = "") -> str:
    while True:
        if hint:
            print(f"{Style.DIM}{hint}{Style.RESET_ALL}")
        value = input(f"{Fore.GREEN}➤ {prompt}: {Style.RESET_ALL}").strip()
        if not value and required:
            print(f"{Fore.RED}  ✗ Это поле обязательно{Style.RESET_ALL}")
            continue
        if validator and value and not validator(value):
            print(f"{Fore.RED}  ✗ Неверный формат{Style.RESET_ALL}")
            continue
        return value


def first_setup():
    clear()
    print(LOGO)
    
    threading.Thread(target=install_deps_background, daemon=True).start()
    
    print(f"\n{Fore.WHITE}Добро пожаловать! Настроим бота за 2 минуты.{Style.RESET_ALL}")
    print(f"{Style.DIM}Зависимости устанавливаются в фоне...{Style.RESET_ALL}\n")
    
    input(f"{Fore.YELLOW}Нажмите Enter чтобы начать...{Style.RESET_ALL}")
    
    clear()
    print(LOGO)
    create_dirs()
    
    print(f"\n{Fore.MAGENTA}[1/5] SESSION ID STARVELL{Style.RESET_ALL}")
    print(f"{Style.DIM}Как получить: starvell.com → F12 → Application → Cookies → session{Style.RESET_ALL}\n")
    session_id = ask("Session ID", validator=lambda x: len(x) >= 10)
    print(f"{Fore.GREEN}  ✓ Сохранено{Style.RESET_ALL}\n")
    
    print(f"{Fore.MAGENTA}[2/5] TELEGRAM BOT TOKEN{Style.RESET_ALL}")
    print(f"{Style.DIM}Создайте бота: @BotFather → /newbot → скопируйте токен{Style.RESET_ALL}\n")
    bot_token = ask("Bot Token", validator=lambda x: ":" in x and len(x) >= 30)
    print(f"{Fore.GREEN}  ✓ Сохранено{Style.RESET_ALL}\n")
    
    print(f"{Fore.MAGENTA}[3/5] ВАШ TELEGRAM ID{Style.RESET_ALL}")
    print(f"{Style.DIM}Узнать: @userinfobot или @getmyid_bot{Style.RESET_ALL}\n")
    admin_id = ask("Admin ID", validator=lambda x: x.isdigit() and len(x) >= 5)
    print(f"{Fore.GREEN}  ✓ Сохранено{Style.RESET_ALL}\n")
    
    print(f"{Fore.MAGENTA}[4/5] ПАРОЛЬ ДЛЯ БОТА{Style.RESET_ALL}")
    print(f"{Style.DIM}Этот пароль нужен для входа в бота в Telegram{Style.RESET_ALL}\n")
    password = ask("Пароль", validator=lambda x: len(x) >= 3)
    print(f"{Fore.GREEN}  ✓ Сохранено{Style.RESET_ALL}\n")
    
    github_token = ask("GitHub Token", required=False)
    if github_token:
        print(f"{Fore.GREEN}  ✓ Сохранено{Style.RESET_ALL}\n")
    else:
        print(f"{Style.DIM}  ✓ Пропущено{Style.RESET_ALL}\n")
    
    config = configparser.RawConfigParser()
    config["StarVell"] = {"session_id": session_id}
    config["Telegram"] = {"bot_token": bot_token, "admin_id": admin_id, "notifications": "true", "password": password}
    config["Proxy"] = {"enable": "0", "check": "1", "login": "", "password": "", "ip": "", "port": ""}
    config["Other"] = {"language": "ru", "log_level": "INFO"}
    config["Updates"] = {"github_token": github_token, "auto_update": "0"}
    
    with open("configs/_main.cfg", "w", encoding="utf-8") as f:
        config.write(f)
    
    while not deps_ready:
        print(f"\r{Fore.YELLOW}⏳ Завершаем установку зависимостей...{Style.RESET_ALL}", end="")
        time.sleep(0.5)
    
    clear()
    print(LOGO)
    
    gh_status = f"{Fore.GREEN}{github_token[:10]}...{Style.RESET_ALL}" if github_token else f"{Style.DIM}не указан{Style.RESET_ALL}"
    
    print(f"""
{Fore.GREEN}╔═══════════════════════════════════════════════════════════════╗
║                    УСТАНОВКА ЗАВЕРШЕНА!                       ║
╚═══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}

{Fore.WHITE}Ваши настройки:{Style.RESET_ALL}
  {Fore.CYAN}•{Style.RESET_ALL} Session:  {Fore.GREEN}{session_id}{Style.RESET_ALL}
  {Fore.CYAN}•{Style.RESET_ALL} Token:    {Fore.GREEN}{bot_token}{Style.RESET_ALL}
  {Fore.CYAN}•{Style.RESET_ALL} Admin ID: {Fore.GREEN}{admin_id}{Style.RESET_ALL}
  {Fore.CYAN}•{Style.RESET_ALL} Пароль:   {Fore.GREEN}{password}{Style.RESET_ALL}
  {Fore.CYAN}•{Style.RESET_ALL} GitHub:   {gh_status}

{Fore.YELLOW}Запуск:{Style.RESET_ALL}  python main.py

{Style.DIM}Конфиг: configs/_main.cfg{Style.RESET_ALL}
""")


def reconfigure():
    clear()
    print(LOGO)
    print(f"{Fore.YELLOW}Перенастройка бота...{Style.RESET_ALL}\n")
    first_setup()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--reconfigure":
        reconfigure()
    else:
        first_setup()
