"""
Клавиатуры для aiogram бота StarVellBot
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Optional, List

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

if TYPE_CHECKING:
    from nexus import Nexus

from tg_bot import utils, CBT


def power_off(instance_id: int, state: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для выключения бота.
    
    :param instance_id: ID экземпляра бота.
    :param state: текущее состояние подтверждения.
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    if state == 0:
        kb.button(text="❌ Отмена", callback_data="CANCEL_SHUTTING_DOWN")
        kb.button(text="✅ Да, выключить", callback_data=f"SHUT_DOWN:1:{instance_id}")
    elif state < 6:
        kb.button(text="❌ Отмена", callback_data="CANCEL_SHUTTING_DOWN")
        kb.button(text="✅ Подтвердить", callback_data=f"SHUT_DOWN:{state + 1}:{instance_id}")
    else:
        kb.button(text="🔄 Перезапуск...", callback_data="EMPTY")
    
    kb.adjust(2)
    return kb.as_markup()


def language_settings(c: Nexus) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру настроек языка.
    
    :param c: экземпляр Nexus.
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    languages = [
        ("🇷🇺 Русский", "ru"),
        ("🇺🇸 English", "en"),
        ("🇺🇦 Українська", "uk")
    ]
    
    current_lang = c.main_cfg.get("Other", {}).get("language", "ru")
    
    for name, code in languages:
        if code == current_lang:
            name = f"✅ {name}"
        kb.button(text=name, callback_data=f"{CBT.LANG}:{code}")
    
    kb.button(text="◀️ Назад", callback_data=CBT.MAIN)
    kb.adjust(1)
    return kb.as_markup()


def main_settings(c: Nexus) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру основных настроек.
    
    :param c: экземпляр Nexus.
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    def l(s):
        return utils.bool_to_text(c.main_cfg.get(s, {}).get("enabled", "0"))
    
    kb.button(text=f"Автоответчик: {l('AutoResponse')}", callback_data=f"{CBT.SWITCH}:AutoResponse:enabled")
    kb.button(text=f"Автовыдача: {l('AutoDelivery')}", callback_data=f"{CBT.SWITCH}:AutoDelivery:enabled")
    kb.button(text=f"Уведомления: {l('Notifications')}", callback_data=f"{CBT.SWITCH}:Notifications:enabled")
    kb.button(text=f"Автоподнятие лотов: {l('AutoRaise')}", callback_data=f"{CBT.SWITCH}:AutoRaise:enabled")
    kb.button(text=f"Автовосстановление: {l('AutoRestore')}", callback_data=f"{CBT.SWITCH}:AutoRestore:enabled")
    kb.button(text="◀️ Назад", callback_data=CBT.MAIN)
    
    kb.adjust(1)
    return kb.as_markup()


def new_message_view_settings(c: Nexus) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру настроек отображения новых сообщений.
    
    :param c: экземпляр Nexus.
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    def l(s):
        return utils.bool_to_text(c.main_cfg.get("NewMessageView", {}).get(s, "0"))
    
    kb.button(text=f"Показывать имя чата: {l('showChatName')}", callback_data=f"{CBT.SWITCH}:NewMessageView:showChatName")
    kb.button(text=f"Показывать время: {l('showTime')}", callback_data=f"{CBT.SWITCH}:NewMessageView:showTime")
    kb.button(text=f"Показывать фото: {l('showPhoto')}", callback_data=f"{CBT.SWITCH}:NewMessageView:showPhoto")
    kb.button(text="◀️ Назад", callback_data=CBT.MAIN)
    
    kb.adjust(1)
    return kb.as_markup()


def greeting_settings(c: Nexus) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру настроек приветствия.
    
    :param c: экземпляр Nexus.
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    def l(s):
        return utils.bool_to_text(c.main_cfg.get("Greetings", {}).get(s, "0"))
    
    kb.button(text=f"Приветствие: {l('enabled')}", callback_data=f"{CBT.SWITCH}:Greetings:enabled")
    kb.button(text="📝 Изменить текст", callback_data=CBT.EDIT_GREETINGS_TEXT)
    kb.button(text="⏰ Изменить кулдаун", callback_data=CBT.EDIT_GREETINGS_COOLDOWN)
    kb.button(text="◀️ Назад", callback_data=CBT.MAIN)
    
    kb.adjust(1)
    return kb.as_markup()


def order_confirm_reply_settings(c: Nexus) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру настроек подтверждения заказа.
    
    :param c: экземпляр Nexus.
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    def l(s):
        return utils.bool_to_text(c.main_cfg.get("OrderConfirm", {}).get(s, "0"))
    
    kb.button(text=f"Подтверждение: {l('enabled')}", callback_data=f"{CBT.SWITCH}:OrderConfirm:enabled")
    kb.button(text="📝 Изменить текст", callback_data=CBT.EDIT_ORDER_CONFIRM_REPLY_TEXT)
    kb.button(text="◀️ Назад", callback_data=CBT.MAIN)
    
    kb.adjust(1)
    return kb.as_markup()


def authorized_users(c: Nexus, offset: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру авторизованных пользователей.
    
    :param c: экземпляр Nexus.
    :param offset: смещение.
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    def l(s):
        return utils.bool_to_text(c.main_cfg.get("Telegram", {}).get(s, "0"))
    
    kb.button(text=f"Авторизация: {l('authEnabled')}", callback_data=f"{CBT.SWITCH}:Telegram:authEnabled")
    kb.button(text="👥 Управление пользователями", callback_data=f"{CBT.AUTHORIZED_USERS}:0")
    kb.button(text="◀️ Назад", callback_data=CBT.MAIN)
    
    kb.adjust(1)
    return kb.as_markup()


def authorized_user_settings(c: Nexus, user_id: int, offset: int, user_link: bool) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру настроек конкретного пользователя.
    
    :param c: экземпляр Nexus.
    :param user_id: ID пользователя.
    :param offset: смещение.
    :param user_link: показывать ли ссылку на пользователя.
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    if user_link:
        kb.button(text="👤 Профиль пользователя", url=f"tg://user?id={user_id}")
    
    kb.button(text="❌ Удалить", callback_data=f"delete_user:{user_id}:{offset}")
    kb.button(text="◀️ Назад", callback_data=f"{CBT.AUTHORIZED_USERS}:{offset}")
    
    kb.adjust(1)
    return kb.as_markup()


def proxy(c: Nexus, offset: int, proxies: dict[str, bool]) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру настроек прокси.
    
    :param c: экземпляр Nexus.
    :param offset: смещение.
    :param proxies: словарь прокси.
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    kb.button(text="➕ Добавить прокси", callback_data=f"{CBT.ADD_PROXY}:{offset}")
    
    for proxy_id, proxy_info in proxies.items():
        status = "🟢" if proxy_info else "🔴"
        kb.button(text=f"{status} Прокси #{proxy_id}", callback_data=f"{CBT.CHOOSE_PROXY}:{offset}:{proxy_id}")
    
    kb.button(text="◀️ Назад", callback_data=CBT.MAIN)
    kb.adjust(1)
    return kb.as_markup()


def review_reply_settings(c: Nexus) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру настроек ответов на отзывы.
    
    :param c: экземпляр Nexus.
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    def l(s):
        return utils.bool_to_text(c.main_cfg.get("ReviewReply", {}).get(s, "0"))
    
    kb.button(text=f"Ответы на отзывы: {l('enabled')}", callback_data=f"{CBT.SWITCH}:ReviewReply:enabled")
    
    for stars in range(1, 6):
        kb.button(text=f"⭐ {stars} звезд", callback_data=f"{CBT.SEND_REVIEW_REPLY_TEXT}:{stars}")
    
    kb.button(text="◀️ Назад", callback_data=CBT.MAIN)
    kb.adjust(1)
    return kb.as_markup()


def notifications_settings(c: Nexus, chat_id: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру настроек уведомлений.
    
    :param c: экземпляр Nexus.
    :param chat_id: ID чата.
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    def l(nt):
        return utils.bool_to_text(c.telegram.is_notification_enabled(chat_id, nt))
    
    kb.button(text=f"Новые сообщения: {l(utils.NotificationTypes.new_message)}", 
              callback_data=f"{CBT.SWITCH_TG_NOTIFICATIONS}:{chat_id}:{utils.NotificationTypes.new_message}")
    kb.button(text=f"Новые заказы: {l(utils.NotificationTypes.new_order)}", 
              callback_data=f"{CBT.SWITCH_TG_NOTIFICATIONS}:{chat_id}:{utils.NotificationTypes.new_order}")
    kb.button(text=f"Подтверждения заказов: {l(utils.NotificationTypes.order_confirmed)}", 
              callback_data=f"{CBT.SWITCH_TG_NOTIFICATIONS}:{chat_id}:{utils.NotificationTypes.order_confirmed}")
    kb.button(text=f"Отзывы: {l(utils.NotificationTypes.review)}", 
              callback_data=f"{CBT.SWITCH_TG_NOTIFICATIONS}:{chat_id}:{utils.NotificationTypes.review}")
    kb.button(text=f"Автовыдача: {l(utils.NotificationTypes.delivery)}", 
              callback_data=f"{CBT.SWITCH_TG_NOTIFICATIONS}:{chat_id}:{utils.NotificationTypes.delivery}")
    kb.button(text="◀️ Назад", callback_data=CBT.MAIN)
    
    kb.adjust(1)
    return kb.as_markup()


def announcements_settings(c: Nexus, chat_id: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру настроек объявлений.
    
    :param c: экземпляр Nexus.
    :param chat_id: ID чата.
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    def l(nt):
        return utils.bool_to_text(c.telegram.is_notification_enabled(chat_id, nt))
    
    kb.button(text=f"Объявления: {l(utils.NotificationTypes.announcement)}", 
              callback_data=f"{CBT.SWITCH_TG_NOTIFICATIONS}:{chat_id}:{utils.NotificationTypes.announcement}")
    kb.button(text=f"Реклама: {l(utils.NotificationTypes.ad)}", 
              callback_data=f"{CBT.SWITCH_TG_NOTIFICATIONS}:{chat_id}:{utils.NotificationTypes.ad}")
    kb.button(text="◀️ Назад", callback_data=CBT.MAIN)
    
    kb.adjust(1)
    return kb.as_markup()


def blacklist_settings(c: Nexus) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру настроек черного списка.
    
    :param c: экземпляр Nexus.
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    def l(s):
        return utils.bool_to_text(c.main_cfg.get("BlockList", {}).get(s, "0"))
    
    kb.button(text=f"Черный список: {l('enabled')}", callback_data=f"{CBT.SWITCH}:BlockList:enabled")
    kb.button(text="➕ Добавить в ЧС", callback_data=CBT.BAN)
    kb.button(text="➖ Удалить из ЧС", callback_data=CBT.UNBAN)
    kb.button(text="📋 Показать список", callback_data="show_blacklist")
    kb.button(text="🗑️ Очистить ЧС", callback_data="clear_blacklist")
    kb.button(text="◀️ Назад", callback_data=CBT.MAIN)
    
    kb.adjust(1)
    return kb.as_markup()


def commands_list(nexus: Nexus, offset: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру списка команд автоответчика.
    
    :param nexus: экземпляр Nexus.
    :param offset: смещение.
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    kb.button(text="➕ Добавить команду", callback_data=CBT.ADD_CMD)
    kb.button(text="◀️ Назад", callback_data=f"{CBT.CATEGORY}:ar")
    
    kb.adjust(1)
    return kb.as_markup()


def edit_command(nexus: Nexus, command_index: int, offset: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру редактирования команды.
    
    :param nexus: экземпляр Nexus.
    :param command_index: индекс команды.
    :param offset: смещение.
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    kb.button(text="📝 Изменить ответ", callback_data=f"{CBT.EDIT_CMD_RESPONSE_TEXT}:{command_index}:{offset}")
    kb.button(text="🔔 Изменить уведомление", callback_data=f"{CBT.EDIT_CMD_NOTIFICATION_TEXT}:{command_index}:{offset}")
    kb.button(text="🔔 Вкл/Выкл уведомления", callback_data=f"{CBT.SWITCH_CMD_NOTIFICATION}:{command_index}:{offset}")
    kb.button(text="❌ Удалить", callback_data=f"{CBT.DEL_CMD}:{command_index}:{offset}")
    kb.button(text="◀️ Назад", callback_data=f"{CBT.CMD_LIST}:{offset}")
    
    kb.adjust(1)
    return kb.as_markup()


def products_files_list(offset: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру списка файлов с товарами.
    
    :param offset: смещение.
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    kb.button(text="➕ Создать файл", callback_data=CBT.CREATE_PRODUCTS_FILE)
    kb.button(text="◀️ Назад", callback_data=f"{CBT.CATEGORY}:ad")
    
    kb.adjust(1)
    return kb.as_markup()


def products_file_edit(file_number: int, offset: int, confirmation: bool = False) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру редактирования файла с товарами.
    
    :param file_number: номер файла.
    :param offset: смещение.
    :param confirmation: режим подтверждения.
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    if confirmation:
        kb.button(text="✅ Да, удалить", callback_data=f"confirm_del_products_file:{file_number}:{offset}")
        kb.button(text="❌ Отмена", callback_data=f"{CBT.EDIT_PRODUCTS_FILE}:{file_number}:{offset}")
    else:
        kb.button(text="➕ Добавить товары", callback_data=f"{CBT.ADD_PRODUCTS_TO_FILE}:{file_number}:0:{offset}:0")
        kb.button(text="📥 Скачать", callback_data=f"download_products_file:{file_number}:{offset}")
        kb.button(text="❌ Удалить", callback_data=f"del_products_file:{file_number}:{offset}")
        kb.button(text="◀️ Назад", callback_data=f"{CBT.PRODUCTS_FILES_LIST}:{offset}")
    
    kb.adjust(1)
    return kb.as_markup()


def lots_list(nexus: Nexus, offset: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру списка лотов с автовыдачей.
    
    :param nexus: экземпляр Nexus.
    :param offset: смещение.
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    kb.button(text="➕ Добавить лот", callback_data=f"{CBT.ADD_AD_TO_LOT_MANUALLY}:{offset}")
    kb.button(text="◀️ Назад", callback_data=f"{CBT.CATEGORY}:ad")
    
    kb.adjust(1)
    return kb.as_markup()


def funpay_lots_list(c: Nexus, offset: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру списка лотов FunPay.
    
    :param c: экземпляр Nexus.
    :param offset: смещение.
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    kb.button(text="🔄 Обновить", callback_data=f"update_funpay_lots:{offset}")
    kb.button(text="◀️ Назад", callback_data=f"{CBT.CATEGORY}:ad")
    
    kb.adjust(1)
    return kb.as_markup()


def edit_lot(nexus: Nexus, lot_number: int, offset: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру редактирования лота.
    
    :param nexus: экземпляр Nexus.
    :param lot_number: номер лота.
    :param offset: смещение.
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    def l(s):
        sections = nexus.AD_CFG.sections()
        if lot_number < len(sections):
            return utils.bool_to_text(nexus.AD_CFG.get(sections[lot_number], {}).get(s, "0"))
        return "🔴"
    
    kb.button(text="📝 Изменить текст выдачи", callback_data=f"{CBT.EDIT_LOT_DELIVERY_TEXT}:{lot_number}:{offset}")
    kb.button(text="📁 Привязать файл товаров", callback_data=f"{CBT.BIND_PRODUCTS_FILE}:{lot_number}:{offset}")
    kb.button(text=f"Автовыдача: {l('autoDelivery')}", callback_data=f"switch_lot:autoDelivery:{lot_number}:{offset}")
    kb.button(text=f"Уведомления: {l('telegramNotification')}", callback_data=f"switch_lot:telegramNotification:{lot_number}:{offset}")
    kb.button(text="🧪 Тест автовыдачи", callback_data=f"test_auto_delivery:{lot_number}:{offset}")
    kb.button(text="❌ Удалить", callback_data=f"{CBT.DEL_AD_LOT}:{lot_number}:{offset}")
    kb.button(text="◀️ Назад", callback_data=f"{CBT.AD_LOTS_LIST}:{offset}")
    
    kb.adjust(1)
    return kb.as_markup()


def new_order(order_id: str, username: str, node_id: int,
              confirmation: bool = False, no_refund: bool = False) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для нового заказа.
    
    :param order_id: ID заказа.
    :param username: имя пользователя.
    :param node_id: ID чата.
    :param confirmation: режим подтверждения.
    :param no_refund: убрать кнопку возврата.
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    if confirmation:
        kb.button(text="✅ Да, вернуть деньги", callback_data=f"{CBT.REFUND_CONFIRMED}:{order_id}:{node_id}:{username}")
        kb.button(text="❌ Отмена", callback_data=f"{CBT.REFUND_CANCELLED}:{order_id}:{node_id}:{username}")
    else:
        kb.button(text="💬 Ответить", callback_data=f"{CBT.SEND_FP_MESSAGE}:{node_id}:{username}")
        if not no_refund:
            kb.button(text="💰 Вернуть деньги", callback_data=f"{CBT.REQUEST_REFUND}:{order_id}:{node_id}:{username}")
        kb.button(text="📋 Подробнее", callback_data=f"{CBT.BACK_TO_ORDER_KB}:{node_id}:{username}:{order_id}:{int(no_refund)}")
    
    kb.adjust(1)
    return kb.as_markup()


def reply(node_id: int, username: str, again: bool = False, extend: bool = False) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру ответа на сообщение.
    
    :param node_id: ID чата.
    :param username: имя пользователя.
    :param again: режим "еще раз".
    :param extend: добавить кнопку "расширить".
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    if again:
        kb.button(text="💬 Ответить еще раз", callback_data=f"{CBT.SEND_FP_MESSAGE}:{node_id}:{username}")
    
    if extend:
        kb.button(text="📋 Расширить", callback_data=f"{CBT.EXTEND_CHAT}:{node_id}:{username}")
    
    kb.button(text="◀️ Назад", callback_data=f"{CBT.BACK_TO_REPLY_KB}:{node_id}:{username}:{int(again)}:{int(extend)}")
    
    kb.adjust(1)
    return kb.as_markup()


def templates_list(c: Nexus, offset: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру списка шаблонов ответов.
    
    :param c: экземпляр Nexus.
    :param offset: смещение.
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    templates = utils.load_answer_templates()
    
    # Показываем шаблоны на текущей странице
    start_idx = offset
    end_idx = min(offset + 5, len(templates))  # 5 шаблонов на страницу
    
    for i in range(start_idx, end_idx):
        template = templates[i]
        preview = template[:30] + "..." if len(template) > 30 else template
        kb.button(text=f"📝 {preview}", callback_data=f"{CBT.EDIT_TMPLT}:{i}:{offset}")
    
    # Добавляем навигацию
    if len(templates) > 5:
        nav_buttons = []
        if offset > 0:
            nav_buttons.append(("◀️", f"{CBT.TMPLT_LIST}:{max(0, offset-5)}"))
        if offset + 5 < len(templates):
            nav_buttons.append(("▶️", f"{CBT.TMPLT_LIST}:{offset+5}"))
        
        for text, callback in nav_buttons:
            kb.button(text=text, callback_data=callback)
    
    kb.button(text="➕ Добавить шаблон", callback_data=f"{CBT.ADD_TMPLT}:{offset}")
    kb.button(text="◀️ Назад", callback_data=f"{CBT.CATEGORY}:ar")
    
    kb.adjust(1)
    return kb.as_markup()


def edit_template(nexus: Nexus, template_index: int, offset: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру редактирования шаблона.
    
    :param nexus: экземпляр Nexus.
    :param template_index: индекс шаблона.
    :param offset: смещение.
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    kb.button(text="📝 Изменить", callback_data=f"{CBT.EDIT_TMPLT}:{template_index}:{offset}")
    kb.button(text="❌ Удалить", callback_data=f"{CBT.DEL_TMPLT}:{template_index}:{offset}")
    kb.button(text="◀️ Назад", callback_data=f"{CBT.TMPLT_LIST}:{offset}")
    
    kb.adjust(1)
    return kb.as_markup()


def templates_list_ans_mode(nexus: Nexus, offset: int, node_id: int, username: str, prev_page: int,
                            extra: Optional[List] = None) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру списка шаблонов в режиме ответа.
    
    :param nexus: экземпляр Nexus.
    :param offset: смещение.
    :param node_id: ID чата.
    :param username: имя пользователя.
    :param prev_page: предыдущая страница.
    :param extra: дополнительные параметры.
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    templates = utils.load_answer_templates()
    
    # Показываем шаблоны на текущей странице
    start_idx = offset
    end_idx = min(offset + 5, len(templates))
    
    for i in range(start_idx, end_idx):
        template = templates[i]
        preview = template[:30] + "..." if len(template) > 30 else template
        extra_str = ":" + ":".join(map(str, extra)) if extra else ""
        kb.button(text=f"📝 {preview}", callback_data=f"{CBT.SEND_TMPLT}:{i}:{node_id}:{username}:{prev_page}{extra_str}")
    
    # Добавляем навигацию
    if len(templates) > 5:
        extra_str = ":" + ":".join(map(str, extra)) if extra else ""
        nav_buttons = []
        if offset > 0:
            nav_buttons.append(("◀️", f"{CBT.TMPLT_LIST_ANS_MODE}:{node_id}:{username}:{prev_page}:{max(0, offset-5)}{extra_str}"))
        if offset + 5 < len(templates):
            nav_buttons.append(("▶️", f"{CBT.TMPLT_LIST_ANS_MODE}:{node_id}:{username}:{prev_page}:{offset+5}{extra_str}"))
        
        for text, callback in nav_buttons:
            kb.button(text=text, callback_data=callback)
    
    kb.button(text="◀️ Назад", callback_data=f"{CBT.BACK_TO_REPLY_KB}:{node_id}:{username}:1:0")
    
    kb.adjust(1)
    return kb.as_markup()


def plugins_list(nexus: Nexus, offset: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру списка плагинов.
    
    :param nexus: экземпляр Nexus.
    :param offset: смещение.
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    kb.button(text="➕ Загрузить плагин", callback_data=f"{CBT.UPLOAD_PLUGIN}:{offset}")
    kb.button(text="◀️ Назад", callback_data=CBT.MAIN)
    
    kb.adjust(1)
    return kb.as_markup()


def edit_plugin(nexus: Nexus, uuid: str, offset: int, ask_to_delete: bool = False) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру редактирования плагина.
    
    :param nexus: экземпляр Nexus.
    :param uuid: UUID плагина.
    :param offset: смещение.
    :param ask_to_delete: режим подтверждения удаления.
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    if ask_to_delete:
        kb.button(text="✅ Да, удалить", callback_data=f"{CBT.CONFIRM_DELETE_PLUGIN}:{uuid}:{offset}")
        kb.button(text="❌ Отмена", callback_data=f"{CBT.CANCEL_DELETE_PLUGIN}:{uuid}:{offset}")
    else:
        kb.button(text="⚙️ Настройки", callback_data=f"{CBT.PLUGIN_SETTINGS}:{uuid}:{offset}")
        kb.button(text="📋 Команды", callback_data=f"{CBT.PLUGIN_COMMANDS}:{uuid}:{offset}")
        kb.button(text="🔄 Вкл/Выкл", callback_data=f"{CBT.TOGGLE_PLUGIN}:{uuid}:{offset}")
        kb.button(text="❌ Удалить", callback_data=f"{CBT.DELETE_PLUGIN}:{uuid}:{offset}")
        kb.button(text="◀️ Назад", callback_data=f"{CBT.PLUGINS_LIST}:{offset}")
    
    kb.adjust(1)
    return kb.as_markup()


def LINKS_KB(language: Optional[str] = None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🌐 StarVell", url="https://starvell.com")
    kb.adjust(1)
    return kb.as_markup()


# ===== Дополнительные helper функции =====

def create_inline_keyboard(buttons: List[List[tuple[str, str]]]) -> InlineKeyboardMarkup:
    """
    Универсальный конструктор inline клавиатуры.
    
    :param buttons: список рядов кнопок [(text, callback_data), ...]
    :return: клавиатура.
    
    Пример:
    kb = create_inline_keyboard([
        [("Кнопка 1", "callback_1"), ("Кнопка 2", "callback_2")],
        [("Кнопка 3", "callback_3")]
    ])
    """
    kb = InlineKeyboardBuilder()
    
    for row in buttons:
        for text, callback_data in row:
            if callback_data.startswith("http://") or callback_data.startswith("https://"):
                kb.button(text=text, url=callback_data)
            else:
                kb.button(text=text, callback_data=callback_data)
    
    # Устанавливаем количество кнопок в ряду
    row_widths = [len(row) for row in buttons]
    if row_widths:
        kb.adjust(*row_widths)
    
    return kb.as_markup()


def add_back_button(kb: InlineKeyboardBuilder, callback_data: str = CBT.MAIN) -> InlineKeyboardBuilder:
    """
    Добавляет кнопку "Назад" к существующей клавиатуре.
    
    :param kb: билдер клавиатуры.
    :param callback_data: callback для кнопки назад.
    :return: билдер клавиатуры.
    """
    kb.button(text="◀️ Назад", callback_data=callback_data)
    return kb


def add_cancel_button(kb: InlineKeyboardBuilder, callback_data: str = "CLEAR_STATE") -> InlineKeyboardBuilder:
    """
    Добавляет кнопку "Отмена" к существующей клавиатуре.
    
    :param kb: билдер клавиатуры.
    :param callback_data: callback для кнопки отмены.
    :return: билдер клавиатуры.
    """
    kb.button(text="❌ Отмена", callback_data=callback_data)
    return kb


def pagination_keyboard(
    offset: int,
    total_items: int,
    items_per_page: int,
    callback_prefix: str,
    additional_buttons: Optional[List[tuple[str, str]]] = None
) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с пагинацией.
    
    :param offset: текущее смещение.
    :param total_items: общее количество элементов.
    :param items_per_page: элементов на страницу.
    :param callback_prefix: префикс для callback_data навигации.
    :param additional_buttons: дополнительные кнопки [(text, callback), ...].
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    # Добавляем дополнительные кнопки
    if additional_buttons:
        for text, callback in additional_buttons:
            kb.button(text=text, callback_data=callback)
    
    # Навигация
    nav_buttons = []
    if offset > 0:
        prev_offset = max(0, offset - items_per_page)
        nav_buttons.append(("◀️ Назад", f"{callback_prefix}:{prev_offset}"))
    
    # Показываем текущую страницу
    current_page = (offset // items_per_page) + 1
    total_pages = (total_items + items_per_page - 1) // items_per_page
    nav_buttons.append((f"📄 {current_page}/{total_pages}", "EMPTY"))
    
    if offset + items_per_page < total_items:
        next_offset = offset + items_per_page
        nav_buttons.append(("Вперёд ▶️", f"{callback_prefix}:{next_offset}"))
    
    for text, callback in nav_buttons:
        kb.button(text=text, callback_data=callback)
    
    kb.adjust(1)
    return kb.as_markup()


def confirmation_keyboard(
    confirm_callback: str,
    cancel_callback: str = "CANCEL",
    confirm_text: str = "✅ Подтвердить",
    cancel_text: str = "❌ Отмена"
) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру подтверждения действия.
    
    :param confirm_callback: callback для подтверждения.
    :param cancel_callback: callback для отмены.
    :param confirm_text: текст кнопки подтверждения.
    :param cancel_text: текст кнопки отмены.
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    kb.button(text=cancel_text, callback_data=cancel_callback)
    kb.button(text=confirm_text, callback_data=confirm_callback)
    
    kb.adjust(2)
    return kb.as_markup()


def yes_no_keyboard(
    yes_callback: str,
    no_callback: str,
    yes_text: str = "✅ Да",
    no_text: str = "❌ Нет"
) -> InlineKeyboardMarkup:
    """
    Создает простую клавиатуру Да/Нет.
    
    :param yes_callback: callback для "Да".
    :param no_callback: callback для "Нет".
    :param yes_text: текст кнопки "Да".
    :param no_text: текст кнопки "Нет".
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    kb.button(text=no_text, callback_data=no_callback)
    kb.button(text=yes_text, callback_data=yes_callback)
    
    kb.adjust(2)
    return kb.as_markup()


def settings_toggle_keyboard(
    items: List[tuple[str, str, bool]],
    callback_prefix: str,
    back_callback: str = CBT.MAIN
) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с переключателями настроек.
    
    :param items: список кортежей (название, ключ, текущее_значение).
    :param callback_prefix: префикс для callback_data.
    :param back_callback: callback для кнопки "Назад".
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    for name, key, value in items:
        status = "🟢" if value else "🔴"
        kb.button(text=f"{name}: {status}", callback_data=f"{callback_prefix}:{key}")
    
    kb.button(text="◀️ Назад", callback_data=back_callback)
    kb.adjust(1)
    
    return kb.as_markup()


def menu_keyboard(
    items: List[tuple[str, str]],
    columns: int = 1,
    back_callback: Optional[str] = None
) -> InlineKeyboardMarkup:
    """
    Создает простое меню с кнопками.
    
    :param items: список кортежей (текст, callback_data).
    :param columns: количество колонок.
    :param back_callback: callback для кнопки "Назад" (опционально).
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    
    for text, callback in items:
        if callback.startswith("http://") or callback.startswith("https://"):
            kb.button(text=text, url=callback)
        else:
            kb.button(text=text, callback_data=callback)
    
    if back_callback:
        kb.button(text="◀️ Назад", callback_data=back_callback)
    
    kb.adjust(columns)
    return kb.as_markup()


def empty_keyboard() -> InlineKeyboardMarkup:
    """
    Создает пустую inline клавиатуру.
    
    :return: пустая клавиатура.
    """
    return InlineKeyboardMarkup(inline_keyboard=[])


def single_button_keyboard(text: str, callback_data: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с одной кнопкой.
    
    :param text: текст кнопки.
    :param callback_data: callback_data кнопки.
    :return: клавиатура.
    """
    kb = InlineKeyboardBuilder()
    kb.button(text=text, callback_data=callback_data)
    return kb.as_markup()