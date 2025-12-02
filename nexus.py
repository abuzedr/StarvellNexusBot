import asyncio
import time
import logging
import json
import os
from pathlib import Path

from StarVellAPI.account import Account
from StarVellAPI.updater.runner import Runner
from StarVellAPI.common.enums import EventTypes
from Utils.exceptions import StarVellBotException

logger = logging.getLogger("Nexus.core")


class Nexus:

    def __init__(self, main_cfg, ad_cfg, ar_cfg, raw_ar_cfg, version, telegram_bot=None):
        self.main_cfg = main_cfg
        self.ad_cfg = ad_cfg
        self.ar_cfg = ar_cfg
        self.raw_ar_cfg = raw_ar_cfg
        self.version = version

        self.account = None
        self.runner = None
        self.running = False
        self.plugins = {}
        self.blacklist = set()

        self.stats = {
            "orders_processed": 0,
            "messages_sent": 0,
            "start_time": time.time(),
        }

        self.telegram = telegram_bot
        self._tg_ready = telegram_bot is not None
        self._my_username = ""

        self._read_messages = set()
        self._read_store_path = "storage/read_cache.json"
        self._load_read_store()

    # ============================================================
    # ============================================================

    def init(self):
        try:
            self.init_account()

            if self.telegram:
                self._tg_ready = True

            return self
        except Exception as e:
            raise StarVellBotException(f"Ошибка инициализации: {e}")

    def init_account(self):
        if not isinstance(self.main_cfg, dict):
            raise StarVellBotException(f"Неверный тип конфига: {type(self.main_cfg)}")
        
        starvell_section = self.main_cfg.get("StarVell", {})
        session_id = (starvell_section.get("session") or starvell_section.get("session_id") or "").strip()

        if not session_id:
            raise StarVellBotException("Не указан session_id")

        self.account = Account(session_id=session_id)

        prof = self.account.get_profile()
        if not prof or "user" not in prof:
            raise StarVellBotException("Ошибка авторизации")

        self._my_username = prof["user"].get("username") or ""
        logger.info(f"✅ Авторизован: {self._my_username}")


    # ============================================================
    # ============================================================

    async def run(self):
        logger.info("🔁 Runner запущен")

        try:
            self.running = True
            self.runner = Runner(self.account)

            async for event in self.runner.listen(delay=6.0):
                await self._handle_event(event)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"💥 Runner: {e}")
        finally:
            self.running = False

    # ============================================================
    # ============================================================

    async def _handle_event(self, event):
        try:
            event_type = str(getattr(event, "type", "")).lower()

            if event_type in ("new_message", EventTypes.NEW_MESSAGE):
                await self._handle_new_message(event)
            elif event_type in ("new_order", "order"):
                await self._handle_new_order(event)
            elif event_type in ("new_review", "review"):
                await self._handle_new_review(event)

        except Exception as e:
            logger.error(f"Ошибка обработки события: {e}")

    async def _handle_new_message(self, event):
        """Новое сообщение"""
        msg = getattr(event, "message", None)
        if not msg:
            return

        msg_id = str(getattr(msg, "id", "") or "")
        chat_id = getattr(msg, "chat_id", "") or ""
        content = getattr(msg, "content", "") or ""
        author = getattr(msg, "author", "") or "Пользователь"
        is_system = getattr(msg, "is_system", None)

        if not msg_id or is_system or not content.strip():
            return

        if self._my_username and author.lower() == self._my_username.lower():
            return

        key = f"{chat_id}:{msg_id}"

        uptime = time.time() - self.stats.get("start_time", time.time())
        if uptime < 5:
            self._read_messages.add(key)
            self._persist_read_store()
            return

        if key in self._read_messages:
            return

        text = f"💬 <b>{self._escape_html(author)}</b>\n\n{self._escape_html(content)[:1000]}"

        await self._safe_send_tg_with_buttons(text, chat_id, "message")
        self.stats["messages_sent"] += 1

        await self._try_auto_response(chat_id, author, content)

        self._read_messages.add(key)
        self._persist_read_store()

    async def _handle_new_order(self, event):
        """Новый заказ — чистый формат"""
        order = getattr(event, "order", None) or getattr(event, "data", None)
        if not order:
            return

        order_id = str(order.get("id", ""))
        if not order_id:
            return

        key = f"order:{order_id}"
        if key in self._read_messages:
            return

        buyer_data = order.get("user") or order.get("buyer") or {}
        buyer = buyer_data.get("username") or "Покупатель"
        
        offer = order.get("offerDetails") or order.get("offer") or {}
        desc = (offer.get("descriptions") or {}).get("rus") or {}
        product = desc.get("briefDescription") or desc.get("description") or offer.get("name") or "Товар"
        
        qty = order.get("quantity", 1)
        price = order.get("totalPrice") or order.get("basePrice") or 0
        try:
            price_str = f"{int(price)/100:.2f} ₽"
        except Exception:
            price_str = "—"

        text = f"🛒 <b>Новый заказ:</b> {self._escape_html(product[:60])}\n"
        text += f"👤 Покупатель: {self._escape_html(buyer)}\n"
        if qty > 1:
            text += f"🔢 Количество: ×{qty}\n"
        text += f"💰 Сумма заказа: {price_str}"

        await self._safe_send_tg_with_buttons(text, order_id, "order")
        self.stats["orders_processed"] += 1
        
        self._read_messages.add(key)
        self._persist_read_store()

    async def _handle_new_review(self, event):
        """Новый отзыв — чистый формат"""
        review = getattr(event, "review", None) or getattr(event, "data", None)
        if not review:
            return

        review_id = str(review.get("id", ""))
        if not review_id:
            return

        key = f"review:{review_id}"
        if key in self._read_messages:
            return

        # Получаем автора из review.author или из _order.user (покупатель)
        author_data = review.get("author") or {}
        if isinstance(author_data, dict):
            author = author_data.get("username", "")
        else:
            author = str(author_data) if author_data else ""
        
        if not author:
            order_data = review.get("_order") or {}
            user_data = order_data.get("user") or {}
            author = user_data.get("username") or "Покупатель"

        rating = review.get("rating") or 5
        comment = review.get("content") or review.get("comment") or review.get("text") or ""

        stars = "⭐" * int(rating)

        text = f"📝 <b>Новый отзыв</b> {stars}\n"
        text += f"👤 От: {self._escape_html(author)}\n"
        if comment:
            text += f"\n<i>«{self._escape_html(comment[:300])}»</i>"

        await self._safe_send_tg_with_buttons(text, review_id, "review")
        
        await self._try_auto_review_response(review_id, author, int(rating), comment)
        
        self._read_messages.add(key)
        self._persist_read_store()

    # ============================================================
    # ============================================================

    async def _safe_send_tg(self, text: str):
        try:
            if getattr(self, "telegram", None) is None:
                logger.debug("Telegram-бот не инициализирован — сообщение не отправлено.")
                return

            tg = self.telegram

            if hasattr(tg, "send_notification"):
                await tg.send_notification(text)
                return

            if hasattr(tg, "bot") and hasattr(tg.bot, "send_message"):
                admin_id = getattr(tg, "admin_id", None)
                if admin_id:
                    await tg.bot.send_message(admin_id, text, parse_mode="HTML", disable_web_page_preview=True)
                return

        except Exception as e:
            logger.warning(f"⚠️ Не удалось отправить сообщение в Telegram: {e}")

    async def _safe_send_tg_with_buttons(self, text: str, entity_id: str, entity_type: str):
        """Отправляет уведомление с кнопками в Telegram"""
        try:
            if getattr(self, "telegram", None) is None:
                return

            tg = self.telegram
            
            if hasattr(tg, "send_notification_with_buttons"):
                await tg.send_notification_with_buttons(text, entity_id, entity_type)
                return
            
            # Fallback - отправка ВСЕМ админам
            if hasattr(tg, "bot") and hasattr(tg.bot, "send_message"):
                from tg_bot.kb import KB
                admin_ids = getattr(tg, "admin_ids", set())
                if not admin_ids:
                    admin_id = getattr(tg, "admin_id", None)
                    if admin_id:
                        admin_ids = {admin_id}
                
                for admin_id in admin_ids:
                    try:
                        kb = None
                        t = lambda k: k
                        
                        if entity_type == "message":
                            url = f"https://starvell.com/chat/{entity_id}"
                            kb = KB.chat_notification(t, entity_id, url)
                        elif entity_type == "order":
                            url = f"https://starvell.com/order/{entity_id}"
                            kb = KB.order_notification(t, entity_id, url)
                        elif entity_type == "review":
                            kb = KB.review_notification(t, entity_id)
                        
                        await tg.bot.send_message(
                            admin_id, 
                            text, 
                            parse_mode="HTML", 
                            disable_web_page_preview=True,
                            reply_markup=kb.as_markup() if kb else None
                        )
                    except Exception:
                        pass
                return

        except Exception as e:
            logger.warning(f"⚠️ Не удалось отправить уведомление: {e}")

    # ============================================================
    # ============================================================

    def _send_tg(self, text: str):
        if not self._tg_ready or not self.telegram:
            logger.debug(f"(TG skip) {text}")
            return

        try:
            if not hasattr(self.telegram, "send_notification"):
                logger.warning("⚠️ У Telegram-бота нет метода send_notification()")
                return

            loop = getattr(self.telegram, "loop", None)

            if loop and loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.telegram.send_notification(text), loop
                )
            else:
                asyncio.get_event_loop().create_task(
                    self.telegram.send_notification(text)
                )

        except Exception as e:
            logger.error(f"Ошибка отправки сообщения в Telegram: {e}", exc_info=True)

    # ============================================================
    # ============================================================

    def stop(self):
        self.running = False
        if self.runner:
            try:
                self.runner.stop()
            except Exception:
                pass

    def get_stats(self):
        uptime_sec = int(time.time() - self.stats.get("start_time", time.time()))
        uptime_fmt = f"{uptime_sec // 3600}ч {uptime_sec % 3600 // 60}м"
        return {
            "orders_processed": self.stats.get("orders_processed", 0),
            "messages_sent": self.stats.get("messages_sent", 0),
            "uptime_formatted": uptime_fmt,
        }

    def reinit_account(self, new_session: str) -> str:
        if not new_session:
            raise StarVellBotException("Пустая сессия")

        if isinstance(self.main_cfg, dict):
            self.main_cfg.setdefault("StarVell", {})
            self.main_cfg["StarVell"]["session"] = new_session.strip()
            self.main_cfg["StarVell"]["session_id"] = new_session.strip()

        try:
            from Utils.config_loader import save_main_config
            save_main_config("configs/_main.cfg", self.main_cfg)
            logger.info("✅ Сессия сохранена в configs/_main.cfg")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось сохранить сессию в конфиг: {e}")

        self.account = Account(session_id=new_session)
        prof = self.account.get_profile()
        if not prof or "user" not in prof:
            raise StarVellBotException("Не удалось авторизоваться с новой сессией")

        self._my_username = prof["user"].get("username") or ""
        logger.info(f"✅ Сессия обновлена. Авторизован как {self._my_username}")
        return self._my_username


    # ============================================================
    # ============================================================

    def _load_auto_response_config(self) -> dict:
        try:
            with open("configs/auto_response.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"enabled": False}
    
    def _save_auto_response_config(self, config: dict):
        try:
            with open("configs/auto_response.json", "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

    async def _try_auto_response(self, chat_id: str, author: str, content: str):
        try:
            config = self._load_auto_response_config()
            if not config.get("enabled"):
                return
            
            if not self.account:
                return

            responded_chats = set(config.get("responded_users", []))
            response = None
            
            # Приветствие - один раз на чат
            if config.get("greeting_enabled") and chat_id not in responded_chats:
                response = config.get("greeting_message", "")
                if config.get("greeting_only_first_message"):
                    responded_chats.add(chat_id)
                    config["responded_users"] = list(responded_chats)[-500:]
                    self._save_auto_response_config(config)
            
            if not response:
                keywords = config.get("keywords", {})
                content_lower = content.lower()
                for keyword, reply in keywords.items():
                    if keyword.lower() in content_lower:
                        response = reply
                        break
            
            if response:
                self.account.send_typing(chat_id)
                await asyncio.sleep(1)
                result = self.account.send_message(chat_id, response)
                if result:
                    logger.info(f"🤖 Автоответ [{response[:30]}...] → {author}")
                else:
                    logger.warning(f"⚠️ Автоответ не доставлен в {chat_id}")

        except Exception as e:
            logger.warning(f"⚠️ Автоответ ошибка: {e}")

    async def _try_auto_review_response(self, review_id: str, author: str, rating: int, comment: str):
        """Автоответ на отзыв - шаблон для звёзд 1-5"""
        try:
            config = self._load_auto_response_config()
            if not config.get("review_auto_reply_enabled"):
                logger.debug("Автоответ на отзывы выключен")
                return
            
            if not self.account:
                return

            rating = max(1, min(5, int(rating)))
            review_replies = config.get("review_replies", {})
            
            response = review_replies.get(str(rating), "")
            if not response:
                response = config.get("review_default_reply", "")
            
            if not response:
                logger.debug(f"Нет шаблона для {rating}⭐")
                return
            
            response = response.replace("{author}", author)
            response = response.replace("{rating}", str(rating))
            response = response.replace("{stars}", "⭐" * rating)
            
            await asyncio.sleep(2)
            
            result = self.account.reply_to_review(review_id, response)
            if result:
                logger.info(f"🤖 Автоответ на отзыв [{response[:25]}...] → {author} ({rating}⭐)")
            else:
                logger.warning(f"⚠️ Автоответ на отзыв не доставлен")

        except Exception as e:
            logger.warning(f"⚠️ Ошибка автоответа на отзыв: {e}")

    # ============================================================
    # ============================================================

    def _load_read_store(self):
        if os.path.exists(self._read_store_path):
            try:
                with open(self._read_store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self._read_messages = set(data)
                logger.info(f"📘 Загружено {len(self._read_messages)} ранее прочитанных сообщений.")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось загрузить {self._read_store_path}: {e}")

    def _persist_read_store(self):
        try:
            data = list(self._read_messages)[-1000:]
            with open(self._read_store_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"⚠️ Не удалось записать {self._read_store_path}: {e}")

    def _remember_as_read(self, key: str):
        self._read_messages.add(key)
        self._persist_read_store()

    @staticmethod
    def _mk_key(chat_id: str, msg_id: str) -> str:
        return f"{str(chat_id)}:{str(msg_id)}"

    @staticmethod
    def _escape_html(text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
