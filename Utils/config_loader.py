import configparser
import os
from .exceptions import ConfigParseError

def load_main_config(config_path: str) -> dict:
    if not os.path.exists(config_path):
        raise ConfigParseError(f"Файл конфигурации не найден: {config_path}")
    
    config = configparser.RawConfigParser()
    try:
        config.read(config_path, encoding='utf-8')
    except Exception as e:
        raise ConfigParseError(f"Ошибка чтения конфигурации: {e}")
    
    result = {}
    for section in config.sections():
        result[section] = {}
        for key, value in config[section].items():
            result[section][key] = value.strip() if isinstance(value, str) else value
    
    return result

def load_auto_response_config(config_path: str) -> dict:
    return load_main_config(config_path)

def load_raw_auto_response_config(config_path: str) -> dict:
    return load_main_config(config_path)

def load_auto_delivery_config(config_path: str) -> dict:
    return load_main_config(config_path)

def save_main_config(config_path: str, config_dict: dict) -> bool:
    try:
        config = configparser.RawConfigParser()
        
        for section, options in config_dict.items():
            if not config.has_section(section):
                config.add_section(section)
            for key, value in options.items():
                config.set(section, key, str(value))
        
        with open(config_path, 'w', encoding='utf-8') as f:
            config.write(f)
        return True
    except Exception as e:
        raise ConfigParseError(f"Ошибка сохранения конфигурации: {e}")