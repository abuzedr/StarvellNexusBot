import os
import configparser
from first_setup import first_setup
from Utils.config_loader import load_main_config


def load_or_setup_config():
    config_path = os.path.join("configs", "_main.cfg")

    if not os.path.exists(config_path):
        print("Конфигурация не найдена. Запускаю первоначальную настройку...")
        first_setup()
        return load_or_setup_config()

    config = configparser.RawConfigParser()
    config.read(config_path, encoding="utf-8")

    session_id = ""
    if config.has_option("StarVell", "session_id"):
        session_id = config.get("StarVell", "session_id", fallback="").strip()
    if not session_id and config.has_option("StarVell", "session"):
        session_id = config.get("StarVell", "session", fallback="").strip()
    
    if not session_id:
        print("Не найден session_id. Перезапускаю настройку...")
        first_setup()
        return load_or_setup_config()

    return load_main_config(config_path)
