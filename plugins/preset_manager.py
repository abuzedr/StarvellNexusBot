# -*- coding: utf-8 -*-

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from StarVellAPI.starvell_config_FINAL_v14 import (
    get_default_basic_attributes,
    get_default_numeric_fields
)

logger = logging.getLogger("plugin.preset_manager")
PRESETS_FILE = Path("plugins") / "data" / "create_lot_presets.json"
PRESETS_FILE.parent.mkdir(parents=True, exist_ok=True) 

DEFAULT_DELIVERY_TIME = {
    "from": {"unit": "MINUTES", "value": 15},
    "to": {"unit": "MINUTES", "value": 60}
}
DEFAULT_POST_PAYMENT = "Спасибо за покупку!"


class PresetManager:
    """
    Управляет кастомными пресетами лотов.
    Хранит все в `presets.json`, используя ID категории (cat_id) как ключ.
    """
    
    def __init__(self):
        self.presets = self._load()

    def _load(self) -> Dict[str, Any]:
        """Загружает пресеты из JSON-файла."""
        if not PRESETS_FILE.exists():
            return {}
        try:
            with open(PRESETS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Ошибка загрузки {PRESETS_FILE}: {e}")
            return {}

    def _save(self):
        """Сохраняет пресеты в JSON-файл."""
        try:
            with open(PRESETS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.presets, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error(f"Ошибка сохранения {PRESETS_FILE}: {e}")

    def get_preset_names(self, id_key: str) -> List[str]:
        """
        Возвращает список имен ВСЕХ пресетов для данной категории (по ID).
        Всегда включает "[ДЕФОЛТ]".
        """
        custom_presets = self.presets.get(id_key, {})
        return ["[ДЕФОЛТ]"] + sorted(list(custom_presets.keys()))

    def get_preset_data(self, id_key: str, slug_key: str, preset_name: str) -> Dict[str, Any]:
        """
        Возвращает данные пресета.
        """
        if preset_name == "[ДЕФОЛТ]":
            logger.info(f"Загружаю [ДЕФОЛТ] пресет по slug_key: {slug_key}")
            return {
                "basic": get_default_basic_attributes(slug_key),
                "numeric_to_ask": get_default_numeric_fields(slug_key),
                "postPaymentMessage": DEFAULT_POST_PAYMENT,
                "deliveryTime": DEFAULT_DELIVERY_TIME
            }
        
        preset_data = self.presets.get(id_key, {}).get(preset_name)
        if preset_data:
            logger.info(f"Загружаю кастомный пресет '{preset_name}' по id_key: {id_key}")
            return {
                "basic": preset_data.get("basic", []),
                "numeric_to_ask": preset_data.get("numeric_to_ask", []),
                "postPaymentMessage": preset_data.get("postPaymentMessage", DEFAULT_POST_PAYMENT),
                "deliveryTime": preset_data.get("deliveryTime", DEFAULT_DELIVERY_TIME)
            }

        logger.warning(f"Кастомный пресет {preset_name} для {id_key} не найден. Возвращаю дефолт.")
        return self.get_preset_data(id_key, slug_key, "[ДЕФОЛТ]")

    def save_preset(self, id_key: str, preset_name: str, data: Dict[str, Any]) -> bool:
        """
        Сохраняет или ПЕРЕЗАПИСЫВАЕТ кастомный пресет, используя id_key.
        """
        if preset_name == "[ДЕФОЛТ]":
            logger.error("Нельзя перезаписать [ДЕФОЛТ] пресет.")
            return False

        if "basic" not in data or "numeric_to_ask" not in data or "postPaymentMessage" not in data or "deliveryTime" not in data:
            logger.error(f"Ошибка сохранения пресета: неверный формат data. Ключи: {data.keys()}")
            return False

        if id_key not in self.presets:
            self.presets[id_key] = {}
        
        self.presets[id_key][preset_name] = data
        self._save()
        logger.info(f"Пресет '{preset_name}' для {id_key} сохранен.")
        return True

    def delete_preset(self, id_key: str, preset_name: str) -> bool:
        """Удаляет кастомный пресет по id_key."""
        if preset_name == "[ДЕФОЛТ]":
            return False
            
        if self.presets.get(id_key, {}).pop(preset_name, None):
            self._save()
            logger.info(f"Пресет '{preset_name}' для {id_key} удален.")
            return True
        
        logger.warning(f"Пресет '{preset_name}' для {id_key} не найден для удаления.")
        return False