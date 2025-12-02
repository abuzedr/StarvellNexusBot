import os
import sys

VERSION = "0.1.0-beta"

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    class Fore:
        RED = YELLOW = GREEN = CYAN = MAGENTA = WHITE = ""
    class Style:
        BRIGHT = DIM = RESET_ALL = ""


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


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def main():
    clear()
    print(LOGO)
    print(f"\n{Fore.WHITE}Запуск мастера установки...{Style.RESET_ALL}\n")
    
    from first_setup import first_setup
    first_setup()


if __name__ == "__main__":
    main()
