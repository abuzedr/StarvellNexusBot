from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from tg_bot import CBT

# Локализация (заглушка)
def _(text, **kwargs):
    return text


def CLEAR_STATE_BTN() -> InlineKeyboardMarkup:
    """Создает кнопку отмены"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data=CBT.CLEAR_STATE)]
    ])


def REFRESH_BTN() -> InlineKeyboardMarkup:
    """Создает кнопку обновления"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data=CBT.UPDATE_PROFILE)]
    ])


def SETTINGS_SECTIONS() -> InlineKeyboardMarkup:
    """Создает основное меню настроек"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Основные настройки", callback_data=f"{CBT.CATEGORY}:main")],
        [InlineKeyboardButton(text="🔔 Уведомления", callback_data=f"{CBT.CATEGORY}:tg")],
        [InlineKeyboardButton(text="🚫 Черный список", callback_data=f"{CBT.CATEGORY}:bl")],
        [InlineKeyboardButton(text="🤖 Автоответчик", callback_data=f"{CBT.CATEGORY}:ar")],
        [InlineKeyboardButton(text="📦 Автовыдача", callback_data=f"{CBT.CATEGORY}:ad")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data=f"{CBT.CATEGORY}:users")],
        [InlineKeyboardButton(text="🔌 Плагины", callback_data=f"{CBT.CATEGORY}:plugins")],
        [InlineKeyboardButton(text="🌐 Язык", callback_data=f"{CBT.CATEGORY}:lang")],
        [InlineKeyboardButton(text="📁 Файлы", callback_data=f"{CBT.CATEGORY}:files")],
        [InlineKeyboardButton(text="ℹ️ О боте", callback_data="about_bot")]
    ])


def SETTINGS_SECTIONS_2() -> InlineKeyboardMarkup:
    """Создает вторую страницу основного меню настроек"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Отображение сообщений", callback_data=f"{CBT.CATEGORY}:mv")],
        [InlineKeyboardButton(text="👋 Приветствие", callback_data=f"{CBT.CATEGORY}:gr")],
        [InlineKeyboardButton(text="✅ Подтверждение заказов", callback_data=f"{CBT.CATEGORY}:oc")],
        [InlineKeyboardButton(text="⭐ Ответы на отзывы", callback_data=f"{CBT.CATEGORY}:rr")],
        [InlineKeyboardButton(text="🌐 Прокси", callback_data=f"{CBT.CATEGORY}:proxy")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="statistics")],
        [InlineKeyboardButton(text="📋 Логи", callback_data="logs")],
        [InlineKeyboardButton(text="🔄 Обновления", callback_data="updates")],
        [InlineKeyboardButton(text="⚡ Система", callback_data="system")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=CBT.MAIN)]
    ])


def AR_SETTINGS() -> InlineKeyboardMarkup:
    """Создает меню настроек автоответчика"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Команды", callback_data=f"{CBT.CMD_LIST}:0")],
        [InlineKeyboardButton(text="📋 Шаблоны ответов", callback_data=f"{CBT.TMPLT_LIST}:0")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data=f"{CBT.CATEGORY}:ar_settings")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=CBT.MAIN)]
    ])


def AD_SETTINGS() -> InlineKeyboardMarkup:
    """Создает меню настроек автовыдачи"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Лоты с автовыдачей", callback_data=f"{CBT.AD_LOTS_LIST}:0")],
        [InlineKeyboardButton(text="🛒 Лоты StarVell", callback_data=f"{CBT.FP_LOTS_LIST}:0")],
        [InlineKeyboardButton(text="📁 Файлы с товарами", callback_data=f"{CBT.PRODUCTS_FILES_LIST}:0")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data=f"{CBT.CATEGORY}:ad_settings")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=CBT.MAIN)]
    ])


def CONFIGS_UPLOADER() -> InlineKeyboardMarkup:
    """Создает меню загрузки конфигов"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Загрузить основной конфиг", callback_data="upload_main_config")],
        [InlineKeyboardButton(text="📥 Загрузить конфиг автоответов", callback_data="upload_auto_response_config")],
        [InlineKeyboardButton(text="📥 Загрузить конфиг автовыдачи", callback_data="upload_auto_delivery_config")],
        [InlineKeyboardButton(text="📥 Загрузить файл товаров", callback_data="upload_products_file")],
        [InlineKeyboardButton(text="📥 Загрузить плагин", callback_data="upload_plugin")],
        [InlineKeyboardButton(text="📤 Скачать конфиги", callback_data=f"{CBT.CONFIG_LOADER}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=CBT.MAIN)]
    ])


def NOTIFICATION_SETTINGS(chat_id: int) -> InlineKeyboardMarkup:
    """Создает меню настроек уведомлений"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Новые сообщения", callback_data=f"toggle_notification:{chat_id}:new_message")],
        [InlineKeyboardButton(text="🛒 Новые заказы", callback_data=f"toggle_notification:{chat_id}:new_order")],
        [InlineKeyboardButton(text="✅ Подтверждения заказов", callback_data=f"toggle_notification:{chat_id}:order_confirmed")],
        [InlineKeyboardButton(text="⭐ Отзывы", callback_data=f"toggle_notification:{chat_id}:review")],
        [InlineKeyboardButton(text="📦 Автовыдача", callback_data=f"toggle_notification:{chat_id}:delivery")],
        [InlineKeyboardButton(text="📢 Объявления", callback_data=f"toggle_notification:{chat_id}:announcement")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=CBT.MAIN)]
    ])


def QUICK_ACTIONS() -> InlineKeyboardMarkup:
    """Создает меню быстрых действий"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="quick_stats")],
        [InlineKeyboardButton(text="📋 Заказы", callback_data="quick_orders")],
        [InlineKeyboardButton(text="💬 Чаты", callback_data="quick_chats")],
        [InlineKeyboardButton(text="🔄 Перезапуск", callback_data="quick_restart")],
        [InlineKeyboardButton(text="📋 Логи", callback_data="quick_logs")]
    ])


def ADMIN_ACTIONS() -> InlineKeyboardMarkup:
    """Создает меню действий администратора"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Управление пользователями", callback_data=f"{CBT.AUTHORIZED_USERS}:0")],
        [InlineKeyboardButton(text="🚫 Черный список", callback_data=f"{CBT.CATEGORY}:bl")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data=CBT.MAIN)],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🔄 Перезапуск", callback_data="admin_restart")],
        [InlineKeyboardButton(text="⏹️ Остановка", callback_data="admin_stop")]
    ])


def HELP_MENU() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 StarVell", url="https://starvell.com")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=CBT.MAIN)]
    ])


def CONFIRMATION_KB(action: str, data: str = "") -> InlineKeyboardMarkup:
    """Создает клавиатуру подтверждения"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"confirm:{action}:{data}"),
            InlineKeyboardButton(text="❌ Нет", callback_data=f"cancel:{action}:{data}")
        ]
    ])


def PAGINATION_KB(current_page: int, total_pages: int, callback_prefix: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру пагинации"""
    buttons = []
    
    if current_page > 1:
        buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"{callback_prefix}:{current_page - 1}"))
    
    buttons.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="empty"))
    
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"{callback_prefix}:{current_page + 1}"))
    
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def EMPTY_KB() -> InlineKeyboardMarkup:
    """Создает пустую клавиатуру"""
    return InlineKeyboardMarkup(inline_keyboard=[])


def BACK_BTN(callback_data: str = CBT.MAIN) -> InlineKeyboardMarkup:
    """Создает кнопку назад"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback_data)]
    ])


def REFRESH_AND_BACK_BTN(back_callback: str = CBT.MAIN) -> InlineKeyboardMarkup:
    """Создает кнопки обновления и назад"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data=CBT.UPDATE_PROFILE),
            InlineKeyboardButton(text="◀️ Назад", callback_data=back_callback)
        ]
    ])