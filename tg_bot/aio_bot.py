import asyncio
import logging
import time
import hashlib
import math

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from tg_bot.locale import Locale
from tg_bot.kb import KB
from tg_bot.database import Database
from tg_bot.states import AuthFlow, SettingsFlow, TemplatesFlow, AutodeliveryFlow, ChatReplyFlow, OrderFlow, AutoResponseFlow, ReviewFlow, ReviewAutoReplyFlow

logger = logging.getLogger("StarVell.TG")

PAGE_SIZE = 5


class AioTGBot:
    def __init__(self, token: str, admin_id: int, nexus=None, password_md5: str = None, admin_ids: list = None):
        self.token = token
        self.admin_id = admin_id  # Главный админ
        self.admin_ids = set(admin_ids or [admin_id])  # Все админы
        self.nexus = nexus
        self.password_md5 = password_md5 or hashlib.md5("admin".encode()).hexdigest()
        
        self.bot = Bot(token=token, default=DefaultBotProperties(parse_mode="HTML"))
        self.dp = Dispatcher(storage=MemoryStorage())
        self.db = Database()
        self.loop = None
        
        self._load_admins()
        self._setup_handlers()

    def _load_admins(self):
        """Загружает список админов из storage"""
        import json
        import os
        try:
            path = "storage/admins.json"
            if os.path.exists(path):
                with open(path, "r") as f:
                    data = json.load(f)
                    for uid in data.get("admins", []):
                        self.admin_ids.add(int(uid))
        except Exception:
            pass

    def _save_admins(self):
        """Сохраняет список админов"""
        import json
        import os
        os.makedirs("storage", exist_ok=True)
        with open("storage/admins.json", "w") as f:
            json.dump({"admins": list(self.admin_ids)}, f)

    def _is_admin(self, user_id: int) -> bool:
        """Проверяет является ли пользователь админом"""
        return user_id in self.admin_ids

    def _is_main_admin(self, user_id: int) -> bool:
        """Проверяет является ли пользователь главным админом"""
        return user_id == self.admin_id

    async def init_db(self):
        await self.db.init()

    def _t(self, lang: str, key: str, **kwargs) -> str:
        return Locale.t(lang, key, **kwargs)

    def _setup_handlers(self):
        router = Router()

        @router.message(CommandStart())
        async def cmd_start(msg: Message, state: FSMContext):
            await state.clear()
            if not self._is_admin(msg.from_user.id):
                return
            user = await self.db.get_user(msg.from_user.id)
            lang = user.get("language") or "ru"
            now = int(time.time())
            
            if user.get("blocked_until", 0) > now:
                await msg.answer(self._t(lang, "blocked"))
                return

            if user.get("authorized"):
                await msg.answer(
                    self._t(lang, "main_menu"),
                    reply_markup=KB.main_menu(lambda k: self._t(lang, k)).as_markup()
                )
            else:
                await state.set_state(AuthFlow.waiting_password)
                await msg.answer(self._t(lang, "enter_password"))

        @router.message(AuthFlow.waiting_password, F.text)
        async def on_password(msg: Message, state: FSMContext):
            if not self._is_admin(msg.from_user.id):
                return
            user = await self.db.get_user(msg.from_user.id)
            lang = user.get("language") or "ru"
            
            provided = hashlib.md5(msg.text.strip().encode()).hexdigest()
            if provided.lower() == self.password_md5.lower():
                await self.db.reset_failed(msg.from_user.id)
                await self.db.set_authorized(msg.from_user.id, True)
                await state.set_state(AuthFlow.choosing_language)
                try:
                    await msg.delete()
                except Exception:
                    pass
                m = await msg.answer(
                    self._t(lang, "choose_language"),
                    reply_markup=KB.language(lambda k: self._t(lang, k)).as_markup()
                )
                await state.update_data(last_msg_id=m.message_id)
            else:
                attempts = await self.db.increment_failed(msg.from_user.id)
                left = max(0, 5 - attempts)
                if attempts >= 5:
                    await self.db.set_blocked_until(msg.from_user.id, int(time.time()) + 86400)
                    await msg.answer(self._t(lang, "blocked_24h"))
                    await state.clear()
                else:
                    await msg.answer(self._t(lang, "wrong_password", left=left))

        @router.callback_query(F.data.startswith("lang:"))
        async def on_language(cb: CallbackQuery, state: FSMContext):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            lang_code = cb.data.split(":")[1]
            await self.db.set_language(cb.from_user.id, lang_code)
            await state.clear()
            await cb.message.edit_text(
                self._t(lang_code, "main_menu"),
                reply_markup=KB.main_menu(lambda k: self._t(lang_code, k)).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data == "back:main")
        async def back_main(cb: CallbackQuery, state: FSMContext):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            await state.clear()
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            await cb.message.edit_text(
                self._t(lang, "main_menu"),
                reply_markup=KB.main_menu(lambda k: self._t(lang, k)).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data == "menu:status")
        async def menu_status(cb: CallbackQuery):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            stats = {"orders_processed": 0, "messages_sent": 0, "uptime_formatted": "0ч 0м"}
            session_status = self._t(lang, "status_inactive")
            
            if self.nexus:
                stats = self.nexus.get_stats()
                if hasattr(self.nexus, "account") and self.nexus.account:
                    if getattr(self.nexus.account, "is_initiated", False):
                        session_status = self._t(lang, "status_active")
            
            text = "\n".join([
                self._t(lang, "status_title"),
                "",
                self._t(lang, "status_uptime", uptime=stats.get("uptime_formatted", "0ч 0м")),
                self._t(lang, "status_orders", orders=stats.get("orders_processed", 0)),
                self._t(lang, "status_messages", messages=stats.get("messages_sent", 0)),
                self._t(lang, "status_session", status=session_status),
            ])
            
            await cb.message.edit_text(
                text,
                reply_markup=KB.back(lambda k: self._t(lang, k)).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data == "menu:stats")
        async def menu_stats(cb: CallbackQuery):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            await cb.message.edit_text(
                self._t(lang, "stats_loading"),
                reply_markup=KB.back(lambda k: self._t(lang, k)).as_markup()
            )
            
            text = "\n".join([
                self._t(lang, "stats_title"),
                "",
                self._t(lang, "stats_day"),
                self._t(lang, "stats_completed", count=0, sum="0.00"),
                "",
                self._t(lang, "stats_week"),
                self._t(lang, "stats_completed", count=0, sum="0.00"),
                "",
                self._t(lang, "stats_all"),
                self._t(lang, "stats_completed", count=0, sum="0.00"),
            ])
            
            await cb.message.edit_text(
                text,
                reply_markup=KB.back(lambda k: self._t(lang, k)).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data == "menu:settings")
        async def menu_settings(cb: CallbackQuery, state: FSMContext):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            await state.clear()
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            is_main = self._is_main_admin(cb.from_user.id)
            await cb.message.edit_text(
                self._t(lang, "settings_title"),
                reply_markup=KB.settings(lambda k: self._t(lang, k), is_main).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data == "set:session")
        async def set_session(cb: CallbackQuery, state: FSMContext):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            await state.set_state(SettingsFlow.changing_session)
            await state.update_data(last_msg_id=cb.message.message_id)
            await cb.message.edit_text(
                self._t(lang, "session_prompt"),
                reply_markup=KB.cancel(lambda k: self._t(lang, k), "menu:settings").as_markup()
            )
            await cb.answer()

        @router.message(SettingsFlow.changing_session, F.text)
        async def on_session_change(msg: Message, state: FSMContext):
            if not self._is_admin(msg.from_user.id):
                return
            user = await self.db.get_user(msg.from_user.id)
            lang = user.get("language") or "ru"
            data = await state.get_data()
            last_msg_id = data.get("last_msg_id")
            
            new_session = msg.text.strip()
            try:
                await msg.delete()
            except Exception:
                pass
            
            text = self._t(lang, "session_error", error="Nexus not available")
            if self.nexus:
                try:
                    self.nexus.reinit_account(new_session)
                    text = self._t(lang, "session_updated")
                except Exception as e:
                    text = self._t(lang, "session_error", error=str(e))
            
            await state.clear()
            if last_msg_id:
                try:
                    await msg.bot.edit_message_text(
                        text,
                        chat_id=msg.chat.id,
                        message_id=last_msg_id,
                        reply_markup=KB.settings(lambda k: self._t(lang, k)).as_markup()
                    )
                except Exception:
                    await msg.answer(text, reply_markup=KB.settings(lambda k: self._t(lang, k)).as_markup())
            else:
                await msg.answer(text, reply_markup=KB.settings(lambda k: self._t(lang, k)).as_markup())

        @router.callback_query(F.data == "set:lang")
        async def set_lang(cb: CallbackQuery, state: FSMContext):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            await cb.message.edit_text(
                self._t(lang, "choose_language"),
                reply_markup=KB.language(lambda k: self._t(lang, k)).as_markup()
            )
            await cb.answer()

        # ============================
        # УПРАВЛЕНИЕ АДМИНАМИ
        # ============================
        @router.callback_query(F.data == "set:admins")
        async def set_admins(cb: CallbackQuery):
            if not self._is_main_admin(cb.from_user.id):
                await cb.answer("⛔ Только главный админ", show_alert=True)
                return
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            text = f"👥 <b>Управление админами</b>\n\n📊 Всего: {len(self.admin_ids)}"
            await cb.message.edit_text(
                text,
                reply_markup=KB.admins_menu(lambda k: self._t(lang, k), list(self.admin_ids), self.admin_id).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data.startswith("adm:view:"))
        async def admin_view(cb: CallbackQuery):
            if not self._is_main_admin(cb.from_user.id):
                await cb.answer()
                return
            user_id = int(cb.data.split(":")[2])
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            is_main = user_id == self.admin_id
            role = "👑 Главный админ" if is_main else "👤 Админ"
            
            text = f"👤 <b>ID:</b> <code>{user_id}</code>\n📊 Роль: {role}"
            await cb.message.edit_text(
                text,
                reply_markup=KB.admin_view(lambda k: self._t(lang, k), user_id, is_main).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data == "adm:add")
        async def admin_add(cb: CallbackQuery, state: FSMContext):
            if not self._is_main_admin(cb.from_user.id):
                await cb.answer()
                return
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            await state.set_state(SettingsFlow.adding_admin)
            await state.update_data(last_msg_id=cb.message.message_id)
            
            await cb.message.edit_text(
                "👤 <b>Добавить админа</b>\n\n"
                "Отправьте ID пользователя Telegram.\n\n"
                "<i>💡 Пользователь может узнать свой ID через @userinfobot</i>",
                reply_markup=KB.cancel(lambda k: self._t(lang, k), "set:admins").as_markup()
            )
            await cb.answer()

        @router.message(SettingsFlow.adding_admin, F.text)
        async def on_admin_add(msg: Message, state: FSMContext):
            if not self._is_main_admin(msg.from_user.id):
                return
            
            data = await state.get_data()
            last_msg_id = data.get("last_msg_id")
            user = await self.db.get_user(msg.from_user.id)
            lang = user.get("language") or "ru"
            
            try:
                await msg.delete()
            except Exception:
                pass
            
            try:
                new_admin_id = int(msg.text.strip())
            except ValueError:
                if last_msg_id:
                    await msg.bot.edit_message_text(
                        "❌ Неверный формат ID. Введите число.",
                        chat_id=msg.chat.id,
                        message_id=last_msg_id,
                        reply_markup=KB.cancel(lambda k: self._t(lang, k), "set:admins").as_markup()
                    )
                return
            
            self.admin_ids.add(new_admin_id)
            self._save_admins()
            
            await state.clear()
            
            text = f"✅ Админ <code>{new_admin_id}</code> добавлен!\n\n👥 <b>Управление админами</b>\n📊 Всего: {len(self.admin_ids)}"
            if last_msg_id:
                await msg.bot.edit_message_text(
                    text,
                    chat_id=msg.chat.id,
                    message_id=last_msg_id,
                    reply_markup=KB.admins_menu(lambda k: self._t(lang, k), list(self.admin_ids), self.admin_id).as_markup()
                )

        @router.callback_query(F.data.startswith("adm:del:"))
        async def admin_delete(cb: CallbackQuery):
            if not self._is_main_admin(cb.from_user.id):
                await cb.answer()
                return
            
            user_id = int(cb.data.split(":")[2])
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            if user_id == self.admin_id:
                await cb.answer("⛔ Нельзя удалить главного админа", show_alert=True)
                return
            
            self.admin_ids.discard(user_id)
            self._save_admins()
            
            text = f"✅ Админ <code>{user_id}</code> удалён!\n\n👥 <b>Управление админами</b>\n📊 Всего: {len(self.admin_ids)}"
            await cb.message.edit_text(
                text,
                reply_markup=KB.admins_menu(lambda k: self._t(lang, k), list(self.admin_ids), self.admin_id).as_markup()
            )
            await cb.answer("🗑 Удалён")

        @router.callback_query(F.data == "menu:notif")
        async def menu_notifications(cb: CallbackQuery):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            orders_on = bool(user.get("notify_orders", 1))
            chats_on = bool(user.get("notify_chats", 1))
            await cb.message.edit_text(
                self._t(lang, "notifications_title"),
                reply_markup=KB.notifications(lambda k: self._t(lang, k), orders_on, chats_on).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data == "notif:orders")
        async def toggle_orders(cb: CallbackQuery):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            await self.db.toggle_notify_orders(cb.from_user.id)
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            orders_on = bool(user.get("notify_orders", 1))
            chats_on = bool(user.get("notify_chats", 1))
            await cb.message.edit_reply_markup(
                reply_markup=KB.notifications(lambda k: self._t(lang, k), orders_on, chats_on).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data == "notif:chats")
        async def toggle_chats(cb: CallbackQuery):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            await self.db.toggle_notify_chats(cb.from_user.id)
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            orders_on = bool(user.get("notify_orders", 1))
            chats_on = bool(user.get("notify_chats", 1))
            await cb.message.edit_reply_markup(
                reply_markup=KB.notifications(lambda k: self._t(lang, k), orders_on, chats_on).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data == "menu:templates")
        async def menu_templates(cb: CallbackQuery, state: FSMContext):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            await state.clear()
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            count = await self.db.count_templates()
            text = self._t(lang, "templates_title")
            if count:
                text += "\n" + self._t(lang, "templates_total", count=count)
            else:
                text += "\n" + self._t(lang, "templates_empty")
            await cb.message.edit_text(
                text,
                reply_markup=KB.templates_menu(lambda k: self._t(lang, k)).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data == "tpl:add")
        async def tpl_add(cb: CallbackQuery, state: FSMContext):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            await state.set_state(TemplatesFlow.adding)
            await state.update_data(last_msg_id=cb.message.message_id)
            await cb.message.edit_text(
                self._t(lang, "template_prompt"),
                reply_markup=KB.cancel(lambda k: self._t(lang, k), "menu:templates").as_markup()
            )
            await cb.answer()

        @router.message(TemplatesFlow.adding, F.text)
        async def on_template_add(msg: Message, state: FSMContext):
            if not self._is_admin(msg.from_user.id):
                return
            user = await self.db.get_user(msg.from_user.id)
            lang = user.get("language") or "ru"
            data = await state.get_data()
            last_msg_id = data.get("last_msg_id")
            
            content = msg.text.strip()
            await self.db.add_template(content)
            
            try:
                await msg.delete()
            except Exception:
                pass
            
            await state.clear()
            count = await self.db.count_templates()
            text = self._t(lang, "template_saved") + "\n\n" + self._t(lang, "templates_title")
            if count:
                text += "\n" + self._t(lang, "templates_total", count=count)
            
            if last_msg_id:
                try:
                    await msg.bot.edit_message_text(
                        text,
                        chat_id=msg.chat.id,
                        message_id=last_msg_id,
                        reply_markup=KB.templates_menu(lambda k: self._t(lang, k)).as_markup()
                    )
                except Exception:
                    await msg.answer(text, reply_markup=KB.templates_menu(lambda k: self._t(lang, k)).as_markup())
            else:
                await msg.answer(text, reply_markup=KB.templates_menu(lambda k: self._t(lang, k)).as_markup())

        @router.callback_query(F.data.startswith("tpl:list:"))
        async def tpl_list(cb: CallbackQuery):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            page = int(cb.data.split(":")[2])
            count = await self.db.count_templates()
            total_pages = max(1, math.ceil(count / PAGE_SIZE))
            page = max(1, min(page, total_pages))
            templates = await self.db.list_templates(offset=(page-1)*PAGE_SIZE, limit=PAGE_SIZE)
            
            text = self._t(lang, "templates_title")
            if count:
                text += "\n" + self._t(lang, "templates_total", count=count)
            else:
                text += "\n" + self._t(lang, "templates_empty")
            
            await cb.message.edit_text(
                text,
                reply_markup=KB.templates_list(lambda k: self._t(lang, k), templates, page, total_pages).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data.startswith("tpl:del:"))
        async def tpl_del_list(cb: CallbackQuery):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            page = int(cb.data.split(":")[2])
            count = await self.db.count_templates()
            total_pages = max(1, math.ceil(count / PAGE_SIZE))
            page = max(1, min(page, total_pages))
            templates = await self.db.list_templates(offset=(page-1)*PAGE_SIZE, limit=PAGE_SIZE)
            
            text = self._t(lang, "templates_title") + "\n" + self._t(lang, "btn_delete")
            await cb.message.edit_text(
                text,
                reply_markup=KB.templates_delete(lambda k: self._t(lang, k), templates, page, total_pages).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data.startswith("tpl:rm:"))
        async def tpl_remove(cb: CallbackQuery):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            parts = cb.data.split(":")
            tpl_id = int(parts[2])
            page = int(parts[3]) if len(parts) > 3 else 1
            
            await self.db.delete_template(tpl_id)
            
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            count = await self.db.count_templates()
            total_pages = max(1, math.ceil(count / PAGE_SIZE))
            page = max(1, min(page, total_pages))
            templates = await self.db.list_templates(offset=(page-1)*PAGE_SIZE, limit=PAGE_SIZE)
            
            text = self._t(lang, "template_deleted") + "\n\n" + self._t(lang, "templates_title")
            if count:
                text += "\n" + self._t(lang, "templates_total", count=count)
            
            await cb.message.edit_text(
                text,
                reply_markup=KB.templates_delete(lambda k: self._t(lang, k), templates, page, total_pages).as_markup()
            )
            await cb.answer()

        # ============================
        def _load_ar_config():
            import json
            try:
                with open("configs/auto_response.json", "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {"enabled": False, "greeting_enabled": False, "greeting_message": "", "keywords": {}}
        
        def _save_ar_config(cfg):
            import json
            try:
                with open("configs/auto_response.json", "w", encoding="utf-8") as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=4)
            except Exception:
                pass

        @router.callback_query(F.data == "menu:ar")
        async def menu_ar(cb: CallbackQuery, state: FSMContext):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            await state.clear()
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            cfg = _load_ar_config()
            await cb.message.edit_text(
                self._t(lang, "ar_title"),
                reply_markup=KB.autoresponse_menu(lambda k: self._t(lang, k), cfg.get("enabled", False), cfg.get("greeting_enabled", False)).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data == "ar:toggle")
        async def ar_toggle(cb: CallbackQuery):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            cfg = _load_ar_config()
            cfg["enabled"] = not cfg.get("enabled", False)
            _save_ar_config(cfg)
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            await cb.message.edit_reply_markup(
                reply_markup=KB.autoresponse_menu(lambda k: self._t(lang, k), cfg["enabled"], cfg.get("greeting_enabled", False)).as_markup()
            )
            await cb.answer("✅" if cfg["enabled"] else "❌")

        @router.callback_query(F.data == "ar:greeting_toggle")
        async def ar_greeting_toggle(cb: CallbackQuery):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            cfg = _load_ar_config()
            cfg["greeting_enabled"] = not cfg.get("greeting_enabled", False)
            _save_ar_config(cfg)
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            await cb.message.edit_reply_markup(
                reply_markup=KB.autoresponse_menu(lambda k: self._t(lang, k), cfg.get("enabled", False), cfg["greeting_enabled"]).as_markup()
            )
            await cb.answer("✅" if cfg["greeting_enabled"] else "❌")

        @router.callback_query(F.data == "ar:edit_greeting")
        async def ar_edit_greeting(cb: CallbackQuery, state: FSMContext):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            await state.set_state(AutoResponseFlow.editing_greeting)
            await state.update_data(last_msg_id=cb.message.message_id)
            cfg = _load_ar_config()
            current = cfg.get("greeting_message", "")
            await cb.message.edit_text(
                self._t(lang, "ar_greeting_prompt") + f"\n\n<i>Текущее:</i> {current[:200]}",
                reply_markup=KB.cancel(lambda k: self._t(lang, k), "menu:ar").as_markup()
            )
            await cb.answer()

        @router.message(AutoResponseFlow.editing_greeting, F.text)
        async def on_ar_greeting(msg: Message, state: FSMContext):
            if not self._is_admin(msg.from_user.id):
                return
            cfg = _load_ar_config()
            cfg["greeting_message"] = msg.text.strip()
            _save_ar_config(cfg)
            user = await self.db.get_user(msg.from_user.id)
            lang = user.get("language") or "ru"
            data = await state.get_data()
            last_msg_id = data.get("last_msg_id")
            try:
                await msg.delete()
            except Exception:
                pass
            await state.clear()
            if last_msg_id:
                try:
                    await msg.bot.edit_message_text(
                        self._t(lang, "ar_greeting_updated") + "\n\n" + self._t(lang, "ar_title"),
                        chat_id=msg.chat.id,
                        message_id=last_msg_id,
                        reply_markup=KB.autoresponse_menu(lambda k: self._t(lang, k), cfg.get("enabled", False), cfg.get("greeting_enabled", False)).as_markup()
                    )
                except Exception:
                    await msg.answer(self._t(lang, "ar_greeting_updated"))

        @router.callback_query(F.data == "ar:keywords")
        async def ar_keywords(cb: CallbackQuery):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            cfg = _load_ar_config()
            await cb.message.edit_text(
                "🔑 <b>Ключевые слова</b>\n\nПри обнаружении слова в сообщении — автоматический ответ.",
                reply_markup=KB.keywords_menu(lambda k: self._t(lang, k), cfg.get("keywords", {})).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data == "ar:kw_add")
        async def ar_kw_add(cb: CallbackQuery, state: FSMContext):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            await state.set_state(AutoResponseFlow.adding_keyword)
            await state.update_data(last_msg_id=cb.message.message_id)
            await cb.message.edit_text(
                self._t(lang, "ar_kw_prompt"),
                reply_markup=KB.cancel(lambda k: self._t(lang, k), "ar:keywords").as_markup()
            )
            await cb.answer()

        @router.message(AutoResponseFlow.adding_keyword, F.text)
        async def on_ar_keyword(msg: Message, state: FSMContext):
            if not self._is_admin(msg.from_user.id):
                return
            keyword = msg.text.strip().lower()
            user = await self.db.get_user(msg.from_user.id)
            lang = user.get("language") or "ru"
            data = await state.get_data()
            last_msg_id = data.get("last_msg_id")
            await state.set_state(AutoResponseFlow.adding_keyword_reply)
            await state.update_data(keyword=keyword, last_msg_id=last_msg_id)
            try:
                await msg.delete()
            except Exception:
                pass
            if last_msg_id:
                try:
                    await msg.bot.edit_message_text(
                        self._t(lang, "ar_kw_reply_prompt") + f"\n\n<b>Слово:</b> <code>{keyword}</code>",
                        chat_id=msg.chat.id,
                        message_id=last_msg_id,
                        reply_markup=KB.cancel(lambda k: self._t(lang, k), "ar:keywords").as_markup()
                    )
                except Exception:
                    pass

        @router.message(AutoResponseFlow.adding_keyword_reply, F.text)
        async def on_ar_keyword_reply(msg: Message, state: FSMContext):
            if not self._is_admin(msg.from_user.id):
                return
            data = await state.get_data()
            keyword = data.get("keyword")
            reply = msg.text.strip()
            cfg = _load_ar_config()
            cfg.setdefault("keywords", {})[keyword] = reply
            _save_ar_config(cfg)
            user = await self.db.get_user(msg.from_user.id)
            lang = user.get("language") or "ru"
            last_msg_id = data.get("last_msg_id")
            try:
                await msg.delete()
            except Exception:
                pass
            await state.clear()
            if last_msg_id:
                try:
                    await msg.bot.edit_message_text(
                        self._t(lang, "ar_kw_added") + "\n\n🔑 <b>Ключевые слова</b>",
                        chat_id=msg.chat.id,
                        message_id=last_msg_id,
                        reply_markup=KB.keywords_menu(lambda k: self._t(lang, k), cfg.get("keywords", {})).as_markup()
                    )
                except Exception:
                    await msg.answer(self._t(lang, "ar_kw_added"))

        @router.callback_query(F.data.startswith("ar:kw_del:"))
        async def ar_kw_del(cb: CallbackQuery):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            keyword = cb.data.split(":")[2]
            cfg = _load_ar_config()
            if keyword in cfg.get("keywords", {}):
                del cfg["keywords"][keyword]
                _save_ar_config(cfg)
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            await cb.message.edit_reply_markup(
                reply_markup=KB.keywords_menu(lambda k: self._t(lang, k), cfg.get("keywords", {})).as_markup()
            )
            await cb.answer(self._t(lang, "ar_kw_deleted"))

        # ============================
        def _get_plugin_info(plugin, key: str) -> dict:
            import os
            from datetime import datetime
            
            updated = getattr(plugin, "updated", None)
            if not updated:
                try:
                    plugin_file = f"plugins/{key}.py"
                    if os.path.exists(plugin_file):
                        mtime = os.path.getmtime(plugin_file)
                        updated = datetime.fromtimestamp(mtime).strftime("%d.%m.%Y %H:%M")
                    else:
                        updated = "—"
                except Exception:
                    updated = "—"
            
            return {
                "key": key,
                "name": getattr(plugin, "name", key),
                "version": getattr(plugin, "version", "1.0.0"),
                "author": getattr(plugin, "author", "Unknown"),
                "description": getattr(plugin, "description", "Нет описания"),
                "enabled": getattr(plugin, "enabled", True),
                "commands": getattr(plugin, "commands", []),
                "buttons": getattr(plugin, "buttons", []),
                "updated": updated,
            }

        @router.callback_query(F.data == "menu:plugins")
        async def menu_plugins(cb: CallbackQuery, state: FSMContext):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            await state.clear()
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            plugins_list = []
            if self.nexus and hasattr(self.nexus, "plugin_manager"):
                pm = self.nexus.plugin_manager
                if hasattr(pm, "plugins"):
                    for name, plugin in pm.plugins.items():
                        info = _get_plugin_info(plugin, name)
                        plugins_list.append(info)
            
            count = len(plugins_list)
            text = f"🔌 <b>Плагины</b>\n\n📦 Загружено: <b>{count}</b>"
            
            await cb.message.edit_text(
                text,
                reply_markup=KB.plugins_menu(lambda k: self._t(lang, k), plugins_list).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data.startswith("plg:v:"))
        async def plugin_view(cb: CallbackQuery):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            plugin_name = cb.data.split(":")[2]
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            plugin = None
            if self.nexus and hasattr(self.nexus, "plugin_manager"):
                pm = self.nexus.plugin_manager
                if hasattr(pm, "plugins") and plugin_name in pm.plugins:
                    plugin = pm.plugins[plugin_name]
            
            if not plugin:
                await cb.answer("Плагин не найден")
                return
            
            info = _get_plugin_info(plugin, plugin_name)
            status = "✅ Активен" if info["enabled"] else "⏸ Выключен"
            
            text = (
                f"🔌 <b>{info['name']}</b>\n\n"
                f"👤 Автор: {info['author']}\n"
                f"📦 Версия: {info['version']}\n"
                f"🕐 Обновлён: {info['updated']}\n"
                f"📊 Статус: {status}\n\n"
                f"{info['description']}"
            )
            
            has_commands = len(info["commands"]) > 0
            has_settings = len(info["buttons"]) > 0
            
            await cb.message.edit_text(
                text,
                reply_markup=KB.plugin_view(lambda k: self._t(lang, k), plugin_name, info["enabled"], has_commands, has_settings).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data.startswith("plg:tog:"))
        async def plugin_toggle(cb: CallbackQuery):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            plugin_name = cb.data.split(":")[2]
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            if self.nexus and hasattr(self.nexus, "plugin_manager"):
                pm = self.nexus.plugin_manager
                if hasattr(pm, "plugins") and plugin_name in pm.plugins:
                    plugin = pm.plugins[plugin_name]
                    current = getattr(plugin, "enabled", True)
                    plugin.enabled = not current
                    
                    info = _get_plugin_info(plugin, plugin_name)
                    status = "✅ Активен" if info["enabled"] else "⏸ Выключен"
                    
                    text = (
                        f"🔌 <b>{info['name']}</b>\n\n"
                        f"👤 Автор: {info['author']}\n"
                        f"📦 Версия: {info['version']}\n"
                        f"🕐 Обновлён: {info['updated']}\n"
                        f"📊 Статус: {status}\n\n"
                        f"{info['description']}"
                    )
                    
                    has_commands = len(info["commands"]) > 0
                    has_settings = len(info["buttons"]) > 0
                    
                    await cb.message.edit_text(
                        text,
                        reply_markup=KB.plugin_view(lambda k: self._t(lang, k), plugin_name, info["enabled"], has_commands, has_settings).as_markup()
                    )
                    await cb.answer("✅ Включён" if plugin.enabled else "⏸ Выключен")
                    return
            
            await cb.answer("Плагин не найден")

        @router.callback_query(F.data.startswith("plg:cmd:"))
        async def plugin_commands(cb: CallbackQuery):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            plugin_name = cb.data.split(":")[2]
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            plugin = None
            if self.nexus and hasattr(self.nexus, "plugin_manager"):
                pm = self.nexus.plugin_manager
                if hasattr(pm, "plugins") and plugin_name in pm.plugins:
                    plugin = pm.plugins[plugin_name]
            
            if not plugin:
                await cb.answer("Плагин не найден")
                return
            
            commands = getattr(plugin, "commands", [])
            name = getattr(plugin, "name", plugin_name)
            
            if not commands:
                await cb.answer("У плагина нет команд")
                return
            
            text = f"📜 <b>Команды {name}</b>\n\n"
            for cmd in commands:
                text += f"/{cmd.get('command', '?')}  —  {cmd.get('description', '')}\n\n"
            
            await cb.message.edit_text(
                text,
                reply_markup=KB.back_to_plugin(lambda k: self._t(lang, k), plugin_name).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data.startswith("plg:set:"))
        async def plugin_settings(cb: CallbackQuery):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            plugin_name = cb.data.split(":")[2]
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            plugin = None
            if self.nexus and hasattr(self.nexus, "plugin_manager"):
                pm = self.nexus.plugin_manager
                if hasattr(pm, "plugins") and plugin_name in pm.plugins:
                    plugin = pm.plugins[plugin_name]
            
            if not plugin:
                await cb.answer("Плагин не найден")
                return
            
            buttons = getattr(plugin, "buttons", [])
            
            if not buttons:
                await cb.answer("У плагина нет настроек")
                return
            
            text = f"⚙️ <b>Настройки плагина {plugin_name}</b>"
            
            await cb.message.edit_text(
                text,
                reply_markup=KB.plugin_settings(lambda k: self._t(lang, k), plugin_name, buttons).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data.startswith("plg:del:"))
        async def plugin_delete(cb: CallbackQuery):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            plugin_name = cb.data.split(":")[2]
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            text = f"🗑 <b>Удалить плагин {plugin_name}?</b>\n\n⚠️ Это действие нельзя отменить!"
            
            await cb.message.edit_text(
                text,
                reply_markup=KB.plugin_delete_confirm(lambda k: self._t(lang, k), plugin_name).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data.startswith("plg:del_yes:"))
        async def plugin_delete_confirm(cb: CallbackQuery):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            plugin_name = cb.data.split(":")[2]
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            deleted = False
            if self.nexus and hasattr(self.nexus, "plugin_manager"):
                pm = self.nexus.plugin_manager
                if hasattr(pm, "plugins") and plugin_name in pm.plugins:
                    del pm.plugins[plugin_name]
                    deleted = True
            
            if deleted:
                await cb.answer("✅ Плагин удалён")
                plugins_list = []
                if self.nexus and hasattr(self.nexus, "plugin_manager"):
                    pm = self.nexus.plugin_manager
                    if hasattr(pm, "plugins"):
                        for name, plugin in pm.plugins.items():
                            info = _get_plugin_info(plugin, name)
                            plugins_list.append(info)
                
                count = len(plugins_list)
                text = f"🔌 <b>Плагины</b>\n\n📦 Загружено: <b>{count}</b>"
                
                await cb.message.edit_text(
                    text,
                    reply_markup=KB.plugins_menu(lambda k: self._t(lang, k), plugins_list).as_markup()
                )
            else:
                await cb.answer("Плагин не найден")

        @router.callback_query(F.data == "noop")
        async def noop(cb: CallbackQuery):
            await cb.answer()

        # ============================
        @router.callback_query(F.data == "menu:ad")
        async def menu_ad(cb: CallbackQuery, state: FSMContext):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            await state.clear()
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            await cb.message.edit_text(
                self._t(lang, "ad_title"),
                reply_markup=KB.ad_menu(lambda k: self._t(lang, k)).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data == "ad:add")
        async def ad_add(cb: CallbackQuery, state: FSMContext):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            await state.set_state(AutodeliveryFlow.entering_name)
            await state.update_data(last_msg_id=cb.message.message_id)
            await cb.message.edit_text(
                self._t(lang, "ad_name_prompt"),
                reply_markup=KB.cancel(lambda k: self._t(lang, k), "menu:ad").as_markup()
            )
            await cb.answer()

        @router.message(AutodeliveryFlow.entering_name, F.text)
        async def on_ad_name(msg: Message, state: FSMContext):
            if not self._is_admin(msg.from_user.id):
                return
            user = await self.db.get_user(msg.from_user.id)
            lang = user.get("language") or "ru"
            data = await state.get_data()
            last_msg_id = data.get("last_msg_id")
            
            name = msg.text.strip()
            await state.update_data(ad_name=name)
            await state.set_state(AutodeliveryFlow.waiting_file)
            
            try:
                await msg.delete()
            except Exception:
                pass
            
            if last_msg_id:
                try:
                    await msg.bot.edit_message_text(
                        self._t(lang, "ad_file_prompt"),
                        chat_id=msg.chat.id,
                        message_id=last_msg_id,
                        reply_markup=KB.cancel(lambda k: self._t(lang, k), "menu:ad").as_markup()
                    )
                except Exception:
                    m = await msg.answer(
                        self._t(lang, "ad_file_prompt"),
                        reply_markup=KB.cancel(lambda k: self._t(lang, k), "menu:ad").as_markup()
                    )
                    await state.update_data(last_msg_id=m.message_id)

        @router.message(AutodeliveryFlow.waiting_file, F.document)
        async def on_ad_file(msg: Message, state: FSMContext):
            if not self._is_admin(msg.from_user.id):
                return
            user = await self.db.get_user(msg.from_user.id)
            lang = user.get("language") or "ru"
            data = await state.get_data()
            name = data.get("ad_name", "")
            last_msg_id = data.get("last_msg_id")
            
            import io
            buf = io.BytesIO()
            try:
                await msg.bot.download(msg.document, destination=buf)
            except Exception:
                return
            
            raw = buf.getvalue().decode("utf-8", errors="ignore")
            values = []
            for line in raw.splitlines():
                s = line.strip()
                if not s:
                    continue
                if ":" in s:
                    left, right = s.split(":", 1)
                    left = left.strip()
                    try:
                        cnt = int(right.strip())
                    except Exception:
                        cnt = 1
                    for _ in range(max(0, cnt)):
                        if left:
                            values.append(left)
            else:
                    values.append(s)
            
            added = await self.db.add_autodelivery(name, values)
            
            try:
                await msg.delete()
            except Exception:
                pass
            
            await state.clear()
            text = self._t(lang, "ad_added", count=added, name=name)
            
            if last_msg_id:
                try:
                    await msg.bot.edit_message_text(
                        text,
                        chat_id=msg.chat.id,
                        message_id=last_msg_id,
                        reply_markup=KB.ad_menu(lambda k: self._t(lang, k)).as_markup()
                    )
                except Exception:
                    await msg.answer(text, reply_markup=KB.ad_menu(lambda k: self._t(lang, k)).as_markup())
            else:
                await msg.answer(text, reply_markup=KB.ad_menu(lambda k: self._t(lang, k)).as_markup())

        @router.callback_query(F.data == "ad:list")
        async def ad_list(cb: CallbackQuery):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            items = await self.db.list_autodelivery()
            
            text = self._t(lang, "ad_title")
            if not items:
                text += "\n" + self._t(lang, "ad_empty")
            
            await cb.message.edit_text(
                text,
                reply_markup=KB.ad_list(lambda k: self._t(lang, k), items).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data.startswith("ad:item:"))
        async def ad_item(cb: CallbackQuery, state: FSMContext):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            name = cb.data.split(":", 2)[2]
            await state.update_data(ad_current=name)
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            count = await self.db.count_autodelivery(name)
            
            text = self._t(lang, "ad_item", name=name, left=count)
            await cb.message.edit_text(
                text,
                reply_markup=KB.ad_item(lambda k: self._t(lang, k), name).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data.startswith("ad:del:"))
        async def ad_del_confirm(cb: CallbackQuery, state: FSMContext):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            name = cb.data.split(":", 2)[2]
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            text = self._t(lang, "ad_delete_confirm", name=name)
            await cb.message.edit_text(
                text,
                reply_markup=KB.ad_delete_confirm(lambda k: self._t(lang, k), name).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data.startswith("ad:del_yes:"))
        async def ad_del_yes(cb: CallbackQuery):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            name = cb.data.split(":", 2)[2]
            deleted = await self.db.delete_autodelivery(name)
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            items = await self.db.list_autodelivery()
            text = self._t(lang, "ad_deleted", count=deleted) + "\n\n" + self._t(lang, "ad_title")
            
            await cb.message.edit_text(
                text,
                reply_markup=KB.ad_list(lambda k: self._t(lang, k), items).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data.startswith("chat:reply:"))
        async def chat_reply_start(cb: CallbackQuery, state: FSMContext):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            chat_id = cb.data.split(":", 2)[2]
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            await state.set_state(ChatReplyFlow.waiting_text)
            await state.update_data(
                reply_chat_id=chat_id,
                original_msg_id=cb.message.message_id,
                original_text=cb.message.html_text or cb.message.text or ""
            )
            
            await cb.message.edit_text(
                self._t(lang, "reply_prompt"),
                reply_markup=KB.cancel(lambda k: self._t(lang, k), f"chat:cancel:{chat_id}").as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data.startswith("chat:cancel:"))
        async def chat_reply_cancel(cb: CallbackQuery, state: FSMContext):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            data = await state.get_data()
            chat_id = cb.data.split(":", 2)[2]
            original_text = data.get("original_text", "")
            
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            await state.clear()
            
            if original_text:
                url = f"https://starvell.com/chat/{chat_id}"
                await cb.message.edit_text(
                    original_text,
                    reply_markup=KB.chat_notification(lambda k: self._t(lang, k), chat_id, url).as_markup()
                )
            else:
                await cb.message.edit_text(
                    self._t(lang, "reply_cancelled"),
                    reply_markup=KB.back(lambda k: self._t(lang, k)).as_markup()
                )
            await cb.answer()

        @router.message(ChatReplyFlow.waiting_text, F.text)
        async def on_chat_reply(msg: Message, state: FSMContext):
            if not self._is_admin(msg.from_user.id):
                return
            data = await state.get_data()
            chat_id = data.get("reply_chat_id")
            original_msg_id = data.get("original_msg_id")
            original_text = data.get("original_text", "")
            
            user = await self.db.get_user(msg.from_user.id)
            lang = user.get("language") or "ru"
            
            content = msg.html_text if msg.entities else msg.text
            
            try:
                await msg.delete()
            except Exception:
                pass
            
            success = False
            if self.nexus and hasattr(self.nexus, "account") and self.nexus.account:
                try:
                    self.nexus.account.send_message(chat_id, content)
                    success = True
                except Exception as e:
                    error_text = self._t(lang, "reply_error", error=str(e))
            else:
                error_text = self._t(lang, "reply_error", error="Account not available")
            
            await state.clear()
            
            if success:
                text = self._t(lang, "reply_sent")
                if original_text:
                    text = original_text + "\n\n" + text
                url = f"https://starvell.com/chat/{chat_id}"
                if original_msg_id:
                    try:
                        await msg.bot.edit_message_text(
                            text,
                            chat_id=msg.chat.id,
                            message_id=original_msg_id,
                            reply_markup=KB.chat_notification(lambda k: self._t(lang, k), chat_id, url).as_markup()
                        )
                    except Exception:
                        await msg.answer(text)
                else:
                    await msg.answer(text)
            else:
                if original_msg_id:
                    try:
                        await msg.bot.edit_message_text(
                            error_text,
                            chat_id=msg.chat.id,
                            message_id=original_msg_id,
                            reply_markup=KB.back(lambda k: self._t(lang, k)).as_markup()
                        )
                    except Exception:
                        await msg.answer(error_text)
                else:
                    await msg.answer(error_text)

        @router.callback_query(F.data.startswith("chat:tpl:"))
        async def chat_tpl_select(cb: CallbackQuery, state: FSMContext):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            chat_id = cb.data.split(":", 2)[2]
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            count = await self.db.count_templates()
            if count == 0:
                await cb.answer(self._t(lang, "templates_empty"), show_alert=True)
                return
            
            await state.set_state(ChatReplyFlow.choosing_template)
            await state.update_data(
                reply_chat_id=chat_id,
                original_msg_id=cb.message.message_id,
                original_text=cb.message.html_text or cb.message.text or ""
            )
            
            templates = await self.db.list_templates(limit=PAGE_SIZE)
            total_pages = max(1, math.ceil(count / PAGE_SIZE))
            
            await cb.message.edit_text(
                self._t(lang, "template_select"),
                reply_markup=KB.template_select(lambda k: self._t(lang, k), templates, chat_id, 1, total_pages).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data.startswith("tpl:send:"))
        async def tpl_send(cb: CallbackQuery, state: FSMContext):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            parts = cb.data.split(":")
            tpl_id = int(parts[2])
            chat_id = parts[3]
            
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            tpl = await self.db.get_template(tpl_id)
            if not tpl:
                await cb.answer(self._t(lang, "templates_empty"), show_alert=True)
                return
            
            content = tpl.get("content", "")
            data = await state.get_data()
            original_text = data.get("original_text", "")
            
            success = False
            if self.nexus and hasattr(self.nexus, "account") and self.nexus.account:
                try:
                    self.nexus.account.send_message(chat_id, content)
                    success = True
                except Exception:
                    pass
            
            await state.clear()
            
            if success:
                text = self._t(lang, "reply_sent")
                if original_text:
                    text = original_text + "\n\n" + text
            else:
                text = self._t(lang, "reply_error", error="Failed to send")
            
            url = f"https://starvell.com/chat/{chat_id}"
            await cb.message.edit_text(
                text,
                reply_markup=KB.chat_notification(lambda k: self._t(lang, k), chat_id, url).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data.startswith("order:refund:"))
        async def order_refund_start(cb: CallbackQuery, state: FSMContext):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            order_id = cb.data.split(":", 2)[2]
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            await state.set_state(OrderFlow.confirming_refund)
            await state.update_data(
                order_id=order_id,
                original_msg_id=cb.message.message_id,
                original_text=cb.message.html_text or cb.message.text or ""
            )
            
            await cb.message.edit_text(
                self._t(lang, "order_refund_confirm", id=order_id),
                reply_markup=KB.order_refund_confirm(lambda k: self._t(lang, k), order_id).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data.startswith("order:refund_no:"))
        async def order_refund_no(cb: CallbackQuery, state: FSMContext):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            data = await state.get_data()
            order_id = cb.data.split(":", 2)[2]
            original_text = data.get("original_text", "")
            
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            await state.clear()
            
            url = f"https://starvell.com/order/{order_id}"
            if original_text:
                await cb.message.edit_text(
                    original_text,
                    reply_markup=KB.order_notification(lambda k: self._t(lang, k), order_id, url).as_markup()
                )
            await cb.answer()

        @router.callback_query(F.data.startswith("order:refund_yes:"))
        async def order_refund_yes(cb: CallbackQuery, state: FSMContext):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            order_id = cb.data.split(":", 2)[2]
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            await state.clear()
            
            url = f"https://starvell.com/order/{order_id}"
            await cb.message.edit_text(
                self._t(lang, "order_refund_ok"),
                reply_markup=KB.order_view(lambda k: self._t(lang, k), order_id, url).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data == "cancel")
        async def on_cancel(cb: CallbackQuery, state: FSMContext):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            await state.clear()
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            await cb.message.edit_text(
                self._t(lang, "main_menu"),
                reply_markup=KB.main_menu(lambda k: self._t(lang, k)).as_markup()
            )
            await cb.answer()

        # ============================
        # ОТЗЫВЫ
        # ============================
        @router.callback_query(F.data.startswith("review:reply:"))
        async def review_reply_start(cb: CallbackQuery, state: FSMContext):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            review_id = cb.data.split(":", 2)[2]
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            await state.set_state(ReviewFlow.replying)
            await state.update_data(
                review_id=review_id,
                original_msg_id=cb.message.message_id,
                original_text=cb.message.html_text or cb.message.text or ""
            )
            
            await cb.message.edit_text(
                "✏️ <b>Ответ на отзыв</b>\n\nВведите текст ответа:",
                reply_markup=KB.review_reply_cancel(lambda k: self._t(lang, k), review_id).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data.startswith("review:cancel:"))
        async def review_reply_cancel(cb: CallbackQuery, state: FSMContext):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            data = await state.get_data()
            original_text = data.get("original_text", "")
            review_id = cb.data.split(":", 2)[2]
            
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            await state.clear()
            
            if original_text:
                await cb.message.edit_text(
                    original_text,
                    reply_markup=KB.review_notification(lambda k: self._t(lang, k), review_id).as_markup()
                )
            await cb.answer()

        @router.message(ReviewFlow.replying, F.text)
        async def on_review_reply(msg: Message, state: FSMContext):
            if not self._is_admin(msg.from_user.id):
                return
            data = await state.get_data()
            review_id = data.get("review_id")
            original_msg_id = data.get("original_msg_id")
            original_text = data.get("original_text", "")
            
            user = await self.db.get_user(msg.from_user.id)
            lang = user.get("language") or "ru"
            
            content = msg.text.strip()
            
            try:
                await msg.delete()
            except Exception:
                pass
            
            success = False
            if self.nexus and hasattr(self.nexus, "account") and self.nexus.account:
                try:
                    if hasattr(self.nexus.account, "reply_to_review"):
                        self.nexus.account.reply_to_review(review_id, content)
                        success = True
                except Exception as e:
                    pass
            
            await state.clear()
            
            if success:
                text = "✅ Ответ на отзыв отправлен!"
                if original_text:
                    text = original_text + "\n\n" + text
            else:
                text = "❌ Не удалось отправить ответ (API может не поддерживать)"
            
            if original_msg_id:
                try:
                    await msg.bot.edit_message_text(
                        text,
                        chat_id=msg.chat.id,
                        message_id=original_msg_id,
                        reply_markup=KB.back(lambda k: self._t(lang, k)).as_markup()
                    )
                except Exception:
                    await msg.answer(text)
            else:
                await msg.answer(text)

        # ============================
        # НАСТРОЙКИ АВТООТВЕТА НА ОТЗЫВЫ
        # ============================
        @router.callback_query(F.data == "ar:reviews")
        async def ar_reviews_menu(cb: CallbackQuery):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            cfg = _load_ar_config()
            
            enabled = cfg.get("review_auto_reply_enabled", False)
            replies = cfg.get("review_replies", {})
            default = cfg.get("review_default_reply", "")
            
            # Добавляем default в replies для отображения
            display_replies = dict(replies)
            display_replies["default"] = default
            
            status = "✅ Включено" if enabled else "❌ Выключено"
            
            # Формируем текст со статусом каждой звезды
            lines = [
                "📝 <b>Автоответ на отзывы</b>\n",
                f"📊 Статус: {status}\n",
                "────────────────────",
            ]
            
            for stars in range(5, 0, -1):
                reply = replies.get(str(stars), "")
                star_emoji = "⭐" * stars
                if reply:
                    preview = reply[:40] + "..." if len(reply) > 40 else reply
                    lines.append(f"✓ {star_emoji}\n   <i>{preview}</i>")
                else:
                    lines.append(f"○ {star_emoji} — <i>не задано</i>")
            
            lines.append("────────────────────")
            if default:
                preview = default[:40] + "..." if len(default) > 40 else default
                lines.append(f"✓ 📌 По умолчанию\n   <i>{preview}</i>")
            else:
                lines.append(f"○ 📌 По умолчанию — <i>не задано</i>")
            
            lines.append("\n<i>💡 Переменные: {author}, {rating}, {stars}</i>")
            
            text = "\n".join(lines)
            
            await cb.message.edit_text(
                text,
                reply_markup=KB.review_auto_reply_menu(lambda k: self._t(lang, k), enabled, display_replies).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data == "ar:reviews_toggle")
        async def ar_reviews_toggle(cb: CallbackQuery):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            cfg = _load_ar_config()
            cfg["review_auto_reply_enabled"] = not cfg.get("review_auto_reply_enabled", False)
            _save_ar_config(cfg)
            
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            enabled = cfg["review_auto_reply_enabled"]
            replies = cfg.get("review_replies", {})
            display_replies = dict(replies)
            display_replies["default"] = cfg.get("review_default_reply", "")
            
            await cb.message.edit_reply_markup(
                reply_markup=KB.review_auto_reply_menu(lambda k: self._t(lang, k), enabled, display_replies).as_markup()
            )
            await cb.answer("✅ Включено" if enabled else "❌ Выключено")

        @router.callback_query(F.data.startswith("ar:rev_star:"))
        async def ar_review_star_view(cb: CallbackQuery):
            """Просмотр настройки для конкретной звезды"""
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            
            star_key = cb.data.split(":")[2]  # 1, 2, 3, 4, 5 или default
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            cfg = _load_ar_config()
            
            if star_key == "default":
                current_text = cfg.get("review_default_reply", "")
                title = "📌 По умолчанию"
                description = "Этот ответ используется если для конкретной звезды не задан шаблон."
            else:
                replies = cfg.get("review_replies", {})
                current_text = replies.get(star_key, "")
                stars_int = int(star_key)
                title = "⭐" * stars_int
                description = f"Ответ на отзывы с оценкой {stars_int} из 5"
            
            if current_text:
                text = (
                    f"📝 <b>{title}</b>\n\n"
                    f"<i>{description}</i>\n\n"
                    f"────────────────────\n"
                    f"📄 Текущий шаблон:\n\n"
                    f"<code>{current_text}</code>\n"
                    f"────────────────────"
                )
            else:
                text = (
                    f"📝 <b>{title}</b>\n\n"
                    f"<i>{description}</i>\n\n"
                    f"────────────────────\n"
                    f"⚠️ Шаблон не задан\n"
                    f"────────────────────"
                )
            
            await cb.message.edit_text(
                text,
                reply_markup=KB.review_star_edit(lambda k: self._t(lang, k), star_key, current_text).as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data.startswith("ar:rev_edit:"))
        async def ar_review_edit(cb: CallbackQuery, state: FSMContext):
            """Редактирование шаблона для звезды"""
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            
            star_key = cb.data.split(":")[2]  # 1, 2, 3, 4, 5 или default
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            await state.set_state(ReviewAutoReplyFlow.editing_star)
            await state.update_data(star_key=star_key, last_msg_id=cb.message.message_id)
            
            if star_key == "default":
                title = "📌 По умолчанию"
            else:
                title = "⭐" * int(star_key)
            
            text = (
                f"✏️ <b>Редактирование: {title}</b>\n\n"
                f"Введите текст ответа на отзыв.\n\n"
                f"💡 <b>Доступные переменные:</b>\n"
                f"• <code>{{author}}</code> — имя автора отзыва\n"
                f"• <code>{{rating}}</code> — оценка (число)\n"
                f"• <code>{{stars}}</code> — оценка в виде ⭐⭐⭐⭐⭐"
            )
            
            await cb.message.edit_text(
                text,
                reply_markup=KB.cancel(lambda k: self._t(lang, k), f"ar:rev_star:{star_key}").as_markup()
            )
            await cb.answer()

        @router.callback_query(F.data.startswith("ar:rev_del:"))
        async def ar_review_delete(cb: CallbackQuery):
            """Удаление шаблона для звезды"""
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            
            star_key = cb.data.split(":")[2]
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            cfg = _load_ar_config()
            
            if star_key == "default":
                cfg["review_default_reply"] = ""
            else:
                replies = cfg.get("review_replies", {})
                if star_key in replies:
                    del replies[star_key]
                cfg["review_replies"] = replies
            
            _save_ar_config(cfg)
            
            # Возвращаемся в главное меню отзывов
            enabled = cfg.get("review_auto_reply_enabled", False)
            replies = cfg.get("review_replies", {})
            display_replies = dict(replies)
            display_replies["default"] = cfg.get("review_default_reply", "")
            
            await cb.message.edit_text(
                "✅ Шаблон удалён!\n\n📝 <b>Автоответ на отзывы</b>",
                reply_markup=KB.review_auto_reply_menu(lambda k: self._t(lang, k), enabled, display_replies).as_markup()
            )
            await cb.answer("🗑 Удалено")

        @router.message(ReviewAutoReplyFlow.editing_star, F.text)
        async def on_review_star_edit(msg: Message, state: FSMContext):
            """Сохранение шаблона для звезды"""
            if not self._is_admin(msg.from_user.id):
                return
            
            data = await state.get_data()
            star_key = data.get("star_key", "default")
            last_msg_id = data.get("last_msg_id")
            
            cfg = _load_ar_config()
            
            if star_key == "default":
                cfg["review_default_reply"] = msg.text.strip()
            else:
                replies = cfg.get("review_replies", {})
                replies[star_key] = msg.text.strip()
                cfg["review_replies"] = replies
            
            _save_ar_config(cfg)
            
            user = await self.db.get_user(msg.from_user.id)
            lang = user.get("language") or "ru"
            
            try:
                await msg.delete()
            except Exception:
                pass
            
            await state.clear()
            
            # Возвращаемся в главное меню
            enabled = cfg.get("review_auto_reply_enabled", False)
            replies = cfg.get("review_replies", {})
            display_replies = dict(replies)
            display_replies["default"] = cfg.get("review_default_reply", "")
            
            if star_key == "default":
                title = "📌 По умолчанию"
            else:
                title = "⭐" * int(star_key)
            
            text = f"✅ Шаблон для {title} сохранён!\n\n📝 <b>Автоответ на отзывы</b>"
            
            if last_msg_id:
                try:
                    await msg.bot.edit_message_text(
                        text,
                        chat_id=msg.chat.id,
                        message_id=last_msg_id,
                        reply_markup=KB.review_auto_reply_menu(lambda k: self._t(lang, k), enabled, display_replies).as_markup()
                    )
                except Exception:
                    await msg.answer(text)

        def _load_update_settings():
            import json
            try:
                with open("configs/auto_response.json", "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    return cfg.get("auto_update", True)
            except Exception:
                return True
        
        def _save_update_settings(enabled: bool):
            import json
            try:
                with open("configs/auto_response.json", "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            except Exception:
                cfg = {}
            cfg["auto_update"] = enabled
            try:
                with open("configs/auto_response.json", "w", encoding="utf-8") as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=4)
            except Exception:
                pass

        @router.message(Command("update"))
        async def cmd_update(msg: Message):
            if not self._is_admin(msg.from_user.id):
                return
            user = await self.db.get_user(msg.from_user.id)
            lang = user.get("language") or "ru"
            
            from Utils.updater import Updater
            from main import VERSION
            
            auto_update = _load_update_settings()
            
            await msg.answer("🔍 Проверяю обновления...")
            
            updater = Updater(VERSION)
            result = await updater.check_updates()
            
            if result.get("available"):
                new_ver = result.get("version", "?")
                changelog = result.get("changelog", "")
                text = (
                    f"🆕 <b>Доступно обновление!</b>\n\n"
                    f"📦 Текущая: <code>{VERSION}</code>\n"
                    f"📦 Новая: <code>{new_ver}</code>\n"
                )
                if changelog:
                    text += f"\n📝 <b>Изменения:</b>\n<i>{changelog[:300]}</i>"
                
                await msg.answer(
                    text,
                    reply_markup=KB.update_menu(lambda k: self._t(lang, k), auto_update, has_update=True).as_markup()
                )
            else:
                error = result.get("error", "")
                if error:
                    text = f"❌ Ошибка проверки: {error}"
                else:
                    text = f"✅ <b>Версия актуальна</b>\n\n📦 Версия: <code>{VERSION}</code>"
                
                await msg.answer(
                    text,
                    reply_markup=KB.update_menu(lambda k: self._t(lang, k), auto_update, has_update=False).as_markup()
                )

        @router.callback_query(F.data == "upd:toggle")
        async def upd_toggle(cb: CallbackQuery):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            current = _load_update_settings()
            _save_update_settings(not current)
            
            await cb.message.edit_reply_markup(
                reply_markup=KB.update_menu(lambda k: self._t(lang, k), not current, has_update=False).as_markup()
            )
            await cb.answer("✅ Включено" if not current else "❌ Выключено")

        @router.callback_query(F.data == "upd:check")
        async def upd_check(cb: CallbackQuery):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            from Utils.updater import Updater
            from main import VERSION
            
            auto_update = _load_update_settings()
            
            await cb.answer("🔍 Проверяю...")
            
            updater = Updater(VERSION)
            result = await updater.check_updates()
            
            if result.get("available"):
                new_ver = result.get("version", "?")
                changelog = result.get("changelog", "")
                text = (
                    f"🆕 <b>Доступно обновление!</b>\n\n"
                    f"📦 Текущая: <code>{VERSION}</code>\n"
                    f"📦 Новая: <code>{new_ver}</code>\n"
                )
                if changelog:
                    text += f"\n📝 <b>Изменения:</b>\n<i>{changelog[:300]}</i>"
                
                await cb.message.edit_text(
                    text,
                    reply_markup=KB.update_menu(lambda k: self._t(lang, k), auto_update, has_update=True).as_markup()
                )
            else:
                error = result.get("error", "")
                if error:
                    text = f"❌ Ошибка: {error}"
                else:
                    text = f"✅ <b>Версия актуальна</b>\n\n📦 Версия: <code>{VERSION}</code>"
                
                await cb.message.edit_text(
                    text,
                    reply_markup=KB.update_menu(lambda k: self._t(lang, k), auto_update, has_update=False).as_markup()
                )

        @router.callback_query(F.data == "upd:now")
        async def upd_now(cb: CallbackQuery):
            if not self._is_admin(cb.from_user.id):
                await cb.answer()
                return
            user = await self.db.get_user(cb.from_user.id)
            lang = user.get("language") or "ru"
            
            from Utils.updater import Updater
            from main import VERSION
            
            await cb.message.edit_text("📥 <b>Скачиваю обновление...</b>")
            
            updater = Updater(VERSION)
            result = await updater.check_updates()
            
            if not result.get("available"):
                await cb.message.edit_text("✅ Версия уже актуальна")
                return
            
            success = await updater.auto_update()
            
            if success:
                await cb.message.edit_text(
                    f"✅ <b>Обновление установлено!</b>\n\n"
                    f"📦 Новая версия: <code>{updater.latest_version}</code>\n\n"
                    f"🔄 Бот перезапускается..."
                )
                await asyncio.sleep(2)
                Updater.restart_bot()
            else:
                await cb.message.edit_text(
                    "❌ <b>Ошибка обновления</b>\n\n"
                    "Попробуйте позже или обновите вручную.",
                    reply_markup=KB.update_menu(lambda k: self._t(lang, k), True, has_update=True).as_markup()
                )
            await cb.answer()

        self.dp.include_router(router)

    async def send_notification(self, text: str, reply_markup=None):
        try:
            await self.bot.send_message(
                self.admin_id, 
                text, 
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")

    async def send_notification_with_buttons(self, text: str, entity_id: str, entity_type: str):
        for admin_id in self.admin_ids:
            try:
                user = await self.db.get_user(admin_id)
                lang = user.get("language") or "ru"
                
                kb = None
                if entity_type == "message":
                    url = f"https://starvell.com/chat/{entity_id}"
                    kb = KB.chat_notification(lambda k: self._t(lang, k), entity_id, url)
                elif entity_type == "order":
                    url = f"https://starvell.com/order/{entity_id}"
                    kb = KB.order_notification(lambda k: self._t(lang, k), entity_id, url)
                elif entity_type == "review":
                    kb = KB.review_notification(lambda k: self._t(lang, k), entity_id)
                
                await self.bot.send_message(
                    admin_id,
                    text,
                    reply_markup=kb.as_markup() if kb else None,
                    disable_web_page_preview=True
                )
            except Exception as e:
                logger.warning(f"Failed to send notification to {admin_id}: {e}")

    async def send_chat_notification(self, username: str, text: str, chat_id: str):
        user = await self.db.get_user(self.admin_id)
        if not user.get("notify_chats", 1):
            return
        lang = user.get("language") or "ru"
        
        safe_text = text[:500] + "..." if len(text) > 500 else text
        msg_text = self._t(lang, "chat_new", username=username, text=safe_text)
        url = f"https://starvell.com/chat/{chat_id}"
        
        await self.bot.send_message(
            self.admin_id,
            msg_text,
            reply_markup=KB.chat_notification(lambda k: self._t(lang, k), chat_id, url).as_markup()
        )

    async def send_order_notification(self, order: dict):
        user = await self.db.get_user(self.admin_id)
        if not user.get("notify_orders", 1):
            return
        lang = user.get("language") or "ru"
        
        order_id = order.get("id", "-")
        buyer_data = order.get("user") or {}
        buyer = buyer_data.get("username") or str(buyer_data.get("id", "-"))
        offer = order.get("offerDetails") or {}
        game = (offer.get("game") or {}).get("name", "-")
        category = (offer.get("category") or {}).get("name", "-")
        
        desc = (offer.get("descriptions") or {}).get("rus") or {}
        product = desc.get("briefDescription") or desc.get("description") or (offer.get("offer") or {}).get("name") or "-"
        qty = order.get("quantity", 1)
        price = order.get("totalPrice") or order.get("basePrice") or 0
        try:
            price = f"{int(price)/100:.2f}"
        except Exception:
            price = "0.00"
        
        msg_text = self._t(lang, "order_new",
            id=order_id,
            buyer=buyer,
            game=game,
            category=category,
            product=product[:100],
            qty=qty,
            price=price
        )
        
        url = f"https://starvell.com/order/{order_id}"
        await self.bot.send_message(
            self.admin_id,
            msg_text,
            reply_markup=KB.order_notification(lambda k: self._t(lang, k), order_id, url).as_markup()
        )

    async def run(self):
        self.loop = asyncio.get_event_loop()
        await self.init_db()
        logger.info("Telegram bot polling started")
        await self.dp.start_polling(self.bot)
