from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton


class KB:
    @staticmethod
    def main_menu(t) -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        b.button(text=t("btn_status"), callback_data="menu:status")
        b.button(text=t("btn_stats"), callback_data="menu:stats")
        b.button(text=t("btn_templates"), callback_data="menu:templates")
        b.button(text=t("btn_autoresponse"), callback_data="menu:ar")
        b.button(text=t("btn_autodelivery"), callback_data="menu:ad")
        b.button(text=t("btn_plugins"), callback_data="menu:plugins")
        b.button(text=t("btn_notifications"), callback_data="menu:notif")
        b.button(text=t("btn_settings"), callback_data="menu:settings")
        b.adjust(2, 2, 2, 2)
        return b
    
    @staticmethod
    def autoresponse_menu(t, enabled: bool, greeting_enabled: bool) -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        e_icon = "✅" if enabled else "❌"
        g_icon = "✅" if greeting_enabled else "❌"
        b.button(text=f"{e_icon} Автоответ", callback_data="ar:toggle")
        b.button(text=f"{g_icon} Приветствие", callback_data="ar:greeting_toggle")
        b.button(text="✏️ Изменить приветствие", callback_data="ar:edit_greeting")
        b.button(text="🔑 Ключевые слова", callback_data="ar:keywords")
        b.button(text="📝 Автоответ на отзывы", callback_data="ar:reviews")
        b.button(text=t("btn_back"), callback_data="back:main")
        b.adjust(2, 2, 1, 1)
        return b
    
    @staticmethod
    def keywords_menu(t, keywords: dict) -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        for kw in list(keywords.keys())[:10]:
            b.button(text=f"🗑 {kw}", callback_data=f"ar:kw_del:{kw[:20]}")
        b.button(text="➕ Добавить", callback_data="ar:kw_add")
        b.button(text=t("btn_back"), callback_data="menu:ar")
        b.adjust(2)
        return b

    @staticmethod
    def plugins_menu(t, plugins: list) -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        for plugin in plugins[:10]:
            key = plugin.get("key", "")
            name = plugin.get("name", key or "???")
            enabled = "✅" if plugin.get("enabled", True) else "⏸"
            b.button(text=f"{enabled} {name}", callback_data=f"plg:v:{key[:30]}")
        if not plugins:
            b.button(text="📭 Нет плагинов", callback_data="noop")
        b.button(text=t("btn_back"), callback_data="back:main")
        b.adjust(1)
        return b
    
    @staticmethod
    def plugin_view(t, plugin_name: str, enabled: bool, has_commands: bool = False, has_settings: bool = False) -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        toggle_text = "⏸ Выключить" if enabled else "▶️ Включить"
        b.button(text=toggle_text, callback_data=f"plg:tog:{plugin_name[:30]}")
        if has_commands:
            b.button(text="📜 Команды", callback_data=f"plg:cmd:{plugin_name[:30]}")
        if has_settings:
            b.button(text="⚙️ Настройки", callback_data=f"plg:set:{plugin_name[:30]}")
        b.button(text="🗑 Удалить", callback_data=f"plg:del:{plugin_name[:30]}")
        b.button(text=t("btn_back"), callback_data="menu:plugins")
        b.adjust(1, 2, 1, 1) if has_commands and has_settings else b.adjust(1)
        return b
    
    @staticmethod
    def plugin_delete_confirm(t, plugin_name: str) -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        b.button(text="✅ Да, удалить", callback_data=f"plg:del_yes:{plugin_name[:30]}")
        b.button(text="❌ Отмена", callback_data=f"plg:v:{plugin_name[:30]}")
        b.adjust(2)
        return b
    
    @staticmethod
    def back_to_plugin(t, plugin_name: str) -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        b.button(text=t("btn_back"), callback_data=f"plg:v:{plugin_name[:30]}")
        return b
    
    @staticmethod
    def plugin_settings(t, plugin_name: str, buttons: list) -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        for btn in buttons[:10]:
            btn_text = btn.get("text", "???")
            btn_cb = btn.get("callback", "noop")
            b.button(text=btn_text, callback_data=btn_cb)
        b.button(text=t("btn_back"), callback_data=f"plg:v:{plugin_name[:30]}")
        b.adjust(2)
        return b

    @staticmethod
    def language(t) -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        b.button(text=t("lang_ru"), callback_data="lang:ru")
        b.button(text=t("lang_en"), callback_data="lang:en")
        b.button(text=t("btn_back"), callback_data="back:main")
        b.adjust(2, 1)
        return b

    @staticmethod
    def settings(t, is_main_admin: bool = False) -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        b.button(text=t("btn_session"), callback_data="set:session")
        b.button(text=t("btn_language"), callback_data="set:lang")
        if is_main_admin:
            b.button(text="👥 Админы", callback_data="set:admins")
        b.button(text=t("btn_back"), callback_data="back:main")
        b.adjust(2, 1, 1) if is_main_admin else b.adjust(2, 1)
        return b

    @staticmethod
    def admins_menu(t, admins: list, main_admin_id: int) -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        for uid in admins[:10]:
            is_main = "👑" if uid == main_admin_id else "👤"
            b.button(text=f"{is_main} {uid}", callback_data=f"adm:view:{uid}")
        b.button(text="➕ Добавить админа", callback_data="adm:add")
        b.button(text=t("btn_back"), callback_data="menu:settings")
        b.adjust(1)
        return b

    @staticmethod
    def admin_view(t, user_id: int, is_main: bool) -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        if not is_main:
            b.button(text="🗑 Удалить", callback_data=f"adm:del:{user_id}")
        b.button(text=t("btn_back"), callback_data="set:admins")
        b.adjust(1)
        return b

    @staticmethod
    def notifications(t, orders_on: bool, chats_on: bool) -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        o_icon = "✅" if orders_on else "❌"
        c_icon = "✅" if chats_on else "❌"
        b.button(text=f"{o_icon} {t('notify_orders')}", callback_data="notif:orders")
        b.button(text=f"{c_icon} {t('notify_chats')}", callback_data="notif:chats")
        b.button(text=t("btn_back"), callback_data="back:main")
        b.adjust(2, 1)
        return b

    @staticmethod
    def templates_menu(t) -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        b.button(text=t("btn_add"), callback_data="tpl:add")
        b.button(text=t("btn_list"), callback_data="tpl:list:1")
        b.button(text=t("btn_delete"), callback_data="tpl:del:1")
        b.button(text=t("btn_back"), callback_data="back:main")
        b.adjust(2, 1, 1)
        return b

    @staticmethod
    def templates_list(t, templates: list, page: int, total_pages: int) -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        for tpl in templates:
            preview = (tpl.get("content") or "")[:30] + "..." if len(tpl.get("content", "")) > 30 else tpl.get("content", "")
            b.button(text=f"#{tpl['id']} {preview}", callback_data=f"tpl:view:{tpl['id']}")
        nav = []
        if page > 1:
            nav.append(InlineKeyboardButton(text=t("btn_prev"), callback_data=f"tpl:list:{page-1}"))
        if page < total_pages:
            nav.append(InlineKeyboardButton(text=t("btn_next"), callback_data=f"tpl:list:{page+1}"))
        if nav:
            b.row(*nav)
        b.button(text=t("btn_back"), callback_data="menu:templates")
        b.adjust(1)
        return b

    @staticmethod
    def templates_delete(t, templates: list, page: int, total_pages: int) -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        for tpl in templates:
            preview = (tpl.get("content") or "")[:25] + "..."
            b.button(text=f"🗑 #{tpl['id']}", callback_data=f"tpl:rm:{tpl['id']}:{page}")
        nav = []
        if page > 1:
            nav.append(InlineKeyboardButton(text=t("btn_prev"), callback_data=f"tpl:del:{page-1}"))
        if page < total_pages:
            nav.append(InlineKeyboardButton(text=t("btn_next"), callback_data=f"tpl:del:{page+1}"))
        if nav:
            b.row(*nav)
        b.button(text=t("btn_back"), callback_data="menu:templates")
        b.adjust(1)
        return b

    @staticmethod
    def template_select(t, templates: list, chat_id: str, page: int = 1, total_pages: int = 1) -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        for tpl in templates:
            preview = (tpl.get("content") or "")[:25] + "..."
            b.button(text=preview, callback_data=f"tpl:send:{tpl['id']}:{chat_id}")
        nav = []
        if page > 1:
            nav.append(InlineKeyboardButton(text=t("btn_prev"), callback_data=f"tpl:sel:{chat_id}:{page-1}"))
        if page < total_pages:
            nav.append(InlineKeyboardButton(text=t("btn_next"), callback_data=f"tpl:sel:{chat_id}:{page+1}"))
        if nav:
            b.row(*nav)
        b.button(text=t("btn_cancel"), callback_data=f"chat:cancel:{chat_id}")
        b.adjust(1)
        return b

    @staticmethod
    def ad_menu(t) -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        b.button(text=t("btn_add"), callback_data="ad:add")
        b.button(text=t("btn_list"), callback_data="ad:list")
        b.button(text=t("btn_back"), callback_data="back:main")
        b.adjust(2, 1)
        return b

    @staticmethod
    def ad_list(t, items: list) -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        for name, count in items:
            b.button(text=f"📦 {name} ({count})", callback_data=f"ad:item:{name[:20]}")
        b.button(text=t("btn_back"), callback_data="menu:ad")
        b.adjust(1)
        return b

    @staticmethod
    def ad_item(t, name: str) -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        b.button(text=t("btn_add"), callback_data=f"ad:add_to:{name[:20]}")
        b.button(text=t("btn_delete"), callback_data=f"ad:del:{name[:20]}")
        b.button(text=t("btn_back"), callback_data="ad:list")
        b.adjust(2, 1)
        return b

    @staticmethod
    def ad_delete_confirm(t, name: str) -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        b.button(text=t("btn_yes"), callback_data=f"ad:del_yes:{name[:20]}")
        b.button(text=t("btn_no"), callback_data=f"ad:item:{name[:20]}")
        b.adjust(2)
        return b

    @staticmethod
    def cancel(t, cb_data: str = "cancel") -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        b.button(text=t("btn_cancel"), callback_data=cb_data)
        return b

    @staticmethod
    def back(t, cb_data: str = "back:main") -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        b.button(text=t("btn_back"), callback_data=cb_data)
        return b

    @staticmethod
    def chat_notification(t, chat_id: str, url: str) -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        if url:
            b.button(text=t("btn_open"), url=url)
        b.button(text=t("btn_reply"), callback_data=f"chat:reply:{chat_id}")
        b.button(text=t("btn_template"), callback_data=f"chat:tpl:{chat_id}")
        if url:
            b.adjust(1, 2)
        else:
            b.adjust(2)
        return b

    @staticmethod
    def order_notification(t, order_id: str, url: str) -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        if url:
            b.button(text=t("btn_open"), url=url)
        b.button(text=t("btn_refund"), callback_data=f"order:refund:{order_id}")
        b.adjust(1, 1)
        return b

    @staticmethod
    def order_refund_confirm(t, order_id: str) -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        b.button(text=t("btn_yes"), callback_data=f"order:refund_yes:{order_id}")
        b.button(text=t("btn_no"), callback_data=f"order:refund_no:{order_id}")
        b.adjust(2)
        return b

    @staticmethod
    def order_view(t, order_id: str, url: str) -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        if url:
            b.button(text=t("btn_open"), url=url)
        return b

    @staticmethod
    def review_notification(t, review_id: str) -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        b.button(text="✉️ Ответить на отзыв", callback_data=f"review:reply:{review_id}")
        b.adjust(1)
        return b

    @staticmethod
    def review_reply_cancel(t, review_id: str) -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        b.button(text=t("btn_cancel"), callback_data=f"review:cancel:{review_id}")
        return b

    @staticmethod
    def review_auto_reply_menu(t, enabled: bool, replies: dict = None) -> InlineKeyboardBuilder:
        """Меню автоответа на отзывы - отдельно для каждой звезды"""
        b = InlineKeyboardBuilder()
        replies = replies or {}
        
        icon = "✅" if enabled else "❌"
        b.button(text=f"{icon} Автоответ на отзывы", callback_data="ar:reviews_toggle")
        
        # Кнопки для каждой звезды (1-5) с индикатором настроен/нет
        for stars in range(5, 0, -1):  # 5, 4, 3, 2, 1
            star_emoji = "⭐" * stars
            has_reply = bool(replies.get(str(stars)))
            status = "✓" if has_reply else "○"
            b.button(text=f"{status} {star_emoji}", callback_data=f"ar:rev_star:{stars}")
        
        # По умолчанию
        has_default = bool(replies.get("default"))
        default_status = "✓" if has_default else "○"
        b.button(text=f"{default_status} 📌 По умолчанию", callback_data="ar:rev_star:default")
        
        b.button(text=t("btn_back"), callback_data="menu:ar")
        b.adjust(1, 1, 1, 1, 1, 1, 1, 1)
        return b

    @staticmethod
    def review_star_edit(t, stars: str, current_text: str = "") -> InlineKeyboardBuilder:
        """Меню редактирования ответа для конкретной звезды"""
        b = InlineKeyboardBuilder()
        
        has_text = bool(current_text)
        
        b.button(text="✏️ Редактировать", callback_data=f"ar:rev_edit:{stars}")
        if has_text:
            b.button(text="🗑 Удалить", callback_data=f"ar:rev_del:{stars}")
        b.button(text=t("btn_back"), callback_data="ar:reviews")
        
        b.adjust(2 if has_text else 1, 1)
        return b

    @staticmethod
    def update_menu(t, auto_update: bool, has_update: bool = False) -> InlineKeyboardBuilder:
        b = InlineKeyboardBuilder()
        if has_update:
            b.button(text="📥 Обновить сейчас", callback_data="upd:now")
        icon = "✅" if auto_update else "❌"
        b.button(text=f"{icon} Автообновление", callback_data="upd:toggle")
        b.button(text="🔄 Проверить обновления", callback_data="upd:check")
        b.button(text=t("btn_back"), callback_data="back:main")
        if has_update:
            b.adjust(1, 1, 1, 1)
        else:
            b.adjust(1, 1, 1)
        return b

