import os
import json
import logging
from typing import Dict, List, Optional, Union
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import configparser

logger = logging.getLogger("StarVellBot.tg_bot")


class NotificationTypes:
    """
    Класс с типами Telegram уведомлений.
    """
    bot_start = "1"
    """Уведомление о старте бота."""
    new_message = "2"
    """Уведомление о новом сообщении."""
    command = "3"
    """Уведомление о введенной команде."""
    new_order = "4"
    """Уведомление о новом заказе."""
    order_confirmed = "5"
    """Уведомление о подтверждении заказа."""
    review = "5r"
    """Уведомление об отзыве."""
    lots_restore = "6"
    """Уведомление о восстановлении лота."""
    lots_deactivate = "7"
    """Уведомление о деактивации лота."""
    delivery = "8"
    """Уведомление о выдаче товара."""
    lots_raise = "9"
    """Уведомление о поднятии лотов."""
    other = "10"
    """Прочие уведомления (плагины)."""
    announcement = "11"
    """Новости / объявления."""
    ad = "12"
    """Реклама."""
    critical = "13"
    """Не отключаемые критически важные уведомления (только авторизованные юзеры и чаты)."""
    important_announcement = "14"
    """Не отключаемые новости/объявления (все возможные чаты)."""


def load_authorized_users() -> Dict[int, Dict[str, Union[bool, None, str]]]:
    """
    Загружает список авторизованных пользователей.
    
    :return: словарь авторизованных пользователей.
    """
    try:
        if not os.path.exists("storage/authorized_users.json"):
            return {}
        
        with open("storage/authorized_users.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return {int(k): v for k, v in data.items()}
    except Exception as e:
        logger.error(f"Ошибка загрузки авторизованных пользователей: {e}")
        return {}


def load_notification_settings() -> Dict:
    """
    Загружает настройки уведомлений.
    
    :return: словарь настроек уведомлений.
    """
    try:
        if not os.path.exists("storage/notification_settings.json"):
            return {}
        
        with open("storage/notification_settings.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки настроек уведомлений: {e}")
        return {}


def load_answer_templates() -> List[str]:
    """
    Загружает шаблоны ответов.
    
    :return: список шаблонов ответов.
    """
    try:
        if not os.path.exists("storage/answer_templates.json"):
            return []
        
        with open("storage/answer_templates.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки шаблонов ответов: {e}")
        return []


def save_authorized_users(users: Dict[int, Dict]) -> None:
    """
    Сохраняет список авторизованных пользователей.
    
    :param users: словарь авторизованных пользователей.
    """
    try:
        os.makedirs("storage", exist_ok=True)
        with open("storage/authorized_users.json", "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения авторизованных пользователей: {e}")


def save_notification_settings(settings: Dict) -> None:
    """
    Сохраняет настройки уведомлений.
    
    :param settings: словарь настроек уведомлений.
    """
    try:
        os.makedirs("storage", exist_ok=True)
        with open("storage/notification_settings.json", "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения настроек уведомлений: {e}")


def save_answer_templates(templates: List[str]) -> None:
    """
    Сохраняет шаблоны ответов.
    
    :param templates: список шаблонов ответов.
    """
    try:
        os.makedirs("storage", exist_ok=True)
        with open("storage/answer_templates.json", "w", encoding="utf-8") as f:
            json.dump(templates, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения шаблонов ответов: {e}")


def escape(text: str) -> str:
    """
    Экранирует специальные символы для HTML.
    
    :param text: текст для экранирования.
    :return: экранированный текст.
    """
    if not text:
        return ""
    
    return (text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))


def has_brand_mark(watermark: str) -> bool:
    """
    Проверяет, содержит ли вотемарка брендовую метку.
    
    :param watermark: текст вотемарки.
    :return: True, если содержит брендовую метку.
    """
    if not watermark:
        return False
    
    brand_marks = ["[FPC]", "[StarVellBot]", "[SVB]"]
    return any(mark in watermark.upper() for mark in brand_marks)


def split_by_limit(list_of_str: List[str], limit: int = 4096) -> List[List[str]]:
    """
    Разбивает список строк на части по лимиту символов.
    
    :param list_of_str: список строк.
    :param limit: лимит символов.
    :return: список списков строк.
    """
    result = []
    current_chunk = []
    current_length = 0
    
    for item in list_of_str:
        item_length = len(item)
        if current_length + item_length > limit and current_chunk:
            result.append(current_chunk)
            current_chunk = [item]
            current_length = item_length
        else:
            current_chunk.append(item)
            current_length += item_length
    
    if current_chunk:
        result.append(current_chunk)
    
    return result


def bool_to_text(value: Union[bool, int, str, None], on: str = "🟢", off: str = "🔴") -> str:
    """
    Преобразует булево значение в текст с эмодзи.
    
    :param value: значение для преобразования.
    :param on: текст для True.
    :param off: текст для False.
    :return: текст с эмодзи.
    """
    if value in [True, 1, "1", "true", "True", "TRUE"]:
        return on
    return off


def get_offset(element_index: int, max_elements_on_page: int) -> int:
    """
    Вычисляет смещение для пагинации.
    
    :param element_index: индекс элемента.
    :param max_elements_on_page: максимальное количество элементов на странице.
    :return: смещение.
    """
    if element_index < max_elements_on_page:
        return 0
    
    offset = element_index - max_elements_on_page
    if offset < 0:
        offset = 0
    
    return offset


def add_navigation_buttons(keyboard_obj: InlineKeyboardMarkup, curr_offset: int,
                           max_elements_on_page: int,
                           elements_on_page: int, elements_amount: int,
                           callback_text: str,
                           extra: Optional[List] = None) -> InlineKeyboardMarkup:
    """
    Добавляет кнопки навигации к клавиатуре.
    
    :param keyboard_obj: объект клавиатуры.
    :param curr_offset: текущее смещение.
    :param max_elements_on_page: максимальное количество элементов на странице.
    :param elements_on_page: количество элементов на текущей странице.
    :param elements_amount: общее количество элементов.
    :param callback_text: текст callback'а.
    :param extra: дополнительные параметры.
    :return: клавиатура с кнопками навигации.
    """
    if elements_amount <= max_elements_on_page:
        return keyboard_obj
    
    buttons = []
    
    # Кнопка "Назад"
    if curr_offset > 0:
        prev_offset = max(0, curr_offset - max_elements_on_page)
        extra_str = ":" + ":".join(map(str, extra)) if extra else ""
        buttons.append(InlineKeyboardButton(
            text="◀️",
            callback_data=f"{callback_text}:{prev_offset}{extra_str}"
        ))
    
    # Кнопка "Вперед"
    if curr_offset + elements_on_page < elements_amount:
        next_offset = curr_offset + max_elements_on_page
        extra_str = ":" + ":".join(map(str, extra)) if extra else ""
        buttons.append(InlineKeyboardButton(
            text="▶️",
            callback_data=f"{callback_text}:{next_offset}{extra_str}"
        ))
    
    if buttons:
        # Добавляем кнопки навигации в новую строку
        new_keyboard = keyboard_obj.inline_keyboard.copy()
        new_keyboard.append(buttons)
        return InlineKeyboardMarkup(inline_keyboard=new_keyboard)
    
    return keyboard_obj


def generate_profile_text(nexus) -> str:
    """
    Генерирует текст профиля для отображения в Telegram.
    
    :param nexus: экземпляр Nexus.
    :return: текст профиля.
    """
    try:
        if not nexus.account:
            return "❌ Аккаунт не инициализирован"
        
        profile = nexus.account.profile
        if not profile:
            return "❌ Профиль не загружен"
        
        text = f"""<b>👤 Профиль StarVell</b>

<b>Имя:</b> {escape(profile.username)}
<b>ID:</b> <code>{profile.id}</code>
<b>Баланс:</b> <code>{getattr(profile, 'balance', 'N/A')}</code>
<b>Статус:</b> {'🟢 Онлайн' if getattr(profile, 'is_online', False) else '🔴 Офлайн'}

<b>📊 Статистика бота:</b>
• Обработано заказов: <code>{nexus.stats.get('orders_processed', 0)}</code>
• Отправлено сообщений: <code>{nexus.stats.get('messages_sent', 0)}</code>
• Время работы: <code>{nexus.get_uptime()}</code>"""
        
        return text
    except Exception as e:
        logger.error(f"Ошибка генерации текста профиля: {e}")
        return "❌ Ошибка загрузки профиля"


def generate_lot_info_text(lot_obj: configparser.SectionProxy) -> str:
    """
    Генерирует текст информации о лоте.
    
    :param lot_obj: объект секции лота.
    :return: текст информации о лоте.
    """
    try:
        text = f"""<b>📦 Информация о лоте</b>

<b>Название:</b> <code>{escape(lot_obj.name)}</code>
<b>Ответ:</b> <code>{escape(lot_obj.get('response', 'Не настроен'))}</code>
<b>Файл товаров:</b> <code>{lot_obj.get('productsFileName', 'Не привязан')}</code>
<b>ёвыдача:</b> {bool_to_text(lot_obj.get('autoDelivery', '0'))}
<b>Уведомления:</b> {bool_to_text(lot_obj.get('telegramNotification', '0'))}"""
        
        return text
    except Exception as e:
        logger.error(f"Ошибка генерации текста лота: {e}")
        return "❌ Ошибка загрузки информации о лоте"


def format_msg_text(text: str, message) -> str:
    """
    Форматирует текст сообщения с переменными.
    
    :param text: исходный текст.
    :param message: объект сообщения.
    :return: отформатированный текст.
    """
    try:
        import datetime
        
        now = datetime.datetime.now()
        
        replacements = {
            "$date": now.strftime("%d.%m.%Y"),
            "$date_text": now.strftime("%d %B %Y"),
            "$full_date_text": now.strftime("%d %B %Y года"),
            "$time": now.strftime("%H:%M"),
            "$full_time": now.strftime("%H:%M:%S"),
            "$username": getattr(message, 'author', 'Пользователь'),
            "$message_text": getattr(message, 'text', ''),
            "$chat_id": str(getattr(message, 'chat_id', '')),
            "$chat_name": getattr(message, 'chat_name', ''),
            "$photo": "📷 Фото" if getattr(message, 'image', None) else "",
            "$sleep": "⏰ Пауза"
        }
        
        for var, value in replacements.items():
            text = text.replace(var, str(value))
        
        return text
    except Exception as e:
        logger.error(f"Ошибка форматирования текста сообщения: {e}")
        return text


def format_order_text(text: str, order) -> str:
    """
    Форматирует текст заказа с переменными.
    
    :param text: исходный текст.
    :param order: объект заказа.
    :return: отформатированный текст.
    """
    try:
        import datetime
        
        now = datetime.datetime.now()
        
        replacements = {
            "$date": now.strftime("%d.%m.%Y"),
            "$date_text": now.strftime("%d %B %Y"),
            "$full_date_text": now.strftime("%d %B %Y года"),
            "$time": now.strftime("%H:%M"),
            "$full_time": now.strftime("%H:%M:%S"),
            "$username": getattr(order, 'buyer', 'Покупатель'),
            "$order_id": getattr(order, 'id', ''),
            "$order_link": f"https://starvell.com/order/{getattr(order, 'id', '')}",
            "$order_title": getattr(order, 'title', ''),
            "$game": getattr(order, 'game', ''),
            "$category": getattr(order, 'category', ''),
            "$category_fullname": getattr(order, 'category_fullname', ''),
            "$photo": "📷 Фото" if getattr(order, 'image', None) else "",
            "$sleep": "⏰ Пауза"
        }
        
        for var, value in replacements.items():
            text = text.replace(var, str(value))
        
        return text
    except Exception as e:
        logger.error(f"Ошибка форматирования текста заказа: {e}")
        return text