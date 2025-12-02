"""
Модуль управления черным списком для StarVellBot (aiogram версия)
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nexus import Nexus

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from tg_bot import utils, keyboards as kb, CBT
from tg_bot.static_keyboards import CLEAR_STATE_BTN

import logging

logger = logging.getLogger("StarVellBot.tg_bot")

# Определяем состояния FSM
class BlacklistStates(StatesGroup):
    waiting_for_ban = State()
    waiting_for_unban = State()


def init_blacklist_cp(nexus: Nexus, *args):
    """Инициализация модуля черного списка"""
    router = Router()
    bot = nexus.telegram.bot

    async def open_blacklist_settings(callback: CallbackQuery):
        """Открывает настройки черного списка"""
        blacklist = nexus.blacklist
        blacklist_text = ", ".join(
            f"<code>{utils.escape(user)}</code>" 
            for user in sorted(blacklist, key=lambda x: x.lower())
        )
        
        if not blacklist_text:
            blacklist_text = "Список пуст"
        
        text = f"""<b>🚫 Черный список</b>
<b>Пользователи в ЧС:</b>
{blacklist_text}
<i>Всего пользователей: {len(blacklist)}</i>"""
        
        await callback.message.edit_text(
            text,
            reply_markup=kb.blacklist_settings(nexus)
        )
        await callback.answer()

    async def act_ban_user(callback: CallbackQuery, state: FSMContext):
        """Активирует режим добавления пользователя в ЧС"""
        await callback.message.answer(
            "🚫 <b>Добавление в черный список</b>\n\nВведите никнейм пользователя:",
            reply_markup=CLEAR_STATE_BTN()
        )
        await state.set_state(BlacklistStates.waiting_for_ban)
        await callback.answer()

    async def ban_user(message: Message, state: FSMContext):
        """Добавляет пользователя в ЧС"""
        await state.clear()
        
        nickname = message.text.strip()
        if not nickname:
            await message.reply("❌ Никнейм не может быть пустым")
            return
        
        if nickname in nexus.blacklist:
            await message.reply(
                f"❌ Пользователь <code>{utils.escape(nickname)}</code> уже в черном списке"
            )
            return
        
        nexus.blacklist.append(nickname)
        nexus.save_blacklist()
        
        logger.info(
            f"Пользователь {message.from_user.username} ({message.from_user.id}) "
            f"добавил в ЧС: {nickname}"
        )
        
        keyboard = kb.create_inline_keyboard([
            [
                ("◀️ Назад", f"{CBT.CATEGORY}:bl"),
                ("➕ Еще", CBT.BAN)
            ]
        ])
        
        await message.reply(
            f"✅ Пользователь <code>{utils.escape(nickname)}</code> добавлен в черный список",
            reply_markup=keyboard
        )

    async def act_unban_user(callback: CallbackQuery, state: FSMContext):
        """Активирует режим удаления пользователя из ЧС"""
        await callback.message.answer(
            "✅ <b>Удаление из черного списка</b>\n\nВведите никнейм пользователя:",
            reply_markup=CLEAR_STATE_BTN()
        )
        await state.set_state(BlacklistStates.waiting_for_unban)
        await callback.answer()

    async def unban_user(message: Message, state: FSMContext):
        """Удаляет пользователя из ЧС"""
        await state.clear()
        
        nickname = message.text.strip()
        if not nickname:
            await message.reply("❌ Никнейм не может быть пустым")
            return
        
        if nickname not in nexus.blacklist:
            await message.reply(
                f"❌ Пользователь <code>{utils.escape(nickname)}</code> "
                f"не найден в черном списке"
            )
            return
        
        nexus.blacklist.remove(nickname)
        nexus.save_blacklist()
        
        logger.info(
            f"Пользователь {message.from_user.username} ({message.from_user.id}) "
            f"удалил из ЧС: {nickname}"
        )
        
        keyboard = kb.create_inline_keyboard([
            [
                ("◀️ Назад", f"{CBT.CATEGORY}:bl"),
                ("➖ Еще", CBT.UNBAN)
            ]
        ])
        
        await message.reply(
            f"✅ Пользователь <code>{utils.escape(nickname)}</code> "
            f"удален из черного списка",
            reply_markup=keyboard
        )

    async def send_blacklist(message: Message):
        """Отправляет список пользователей в ЧС"""
        blacklist = nexus.blacklist
        if not blacklist:
            await message.answer("📝 Черный список пуст")
            return
        
        blacklist_text = ", ".join(
            f"<code>{utils.escape(user)}</code>" 
            for user in sorted(blacklist, key=lambda x: x.lower())
        )
        
        # Разбиваем на части, если список слишком длинный
        chunks = utils.split_by_limit([blacklist_text], 4096)
        for chunk in chunks:
            await message.answer(
                f"<b>🚫 Черный список ({len(blacklist)} пользователей):</b>\n\n{chunk[0]}"
            )

    async def clear_blacklist(callback: CallbackQuery):
        """Очищает весь черный список"""
        if not nexus.blacklist:
            await callback.answer("❌ Черный список уже пуст", show_alert=True)
            return
        
        nexus.blacklist.clear()
        nexus.save_blacklist()
        
        logger.info(
            f"Пользователь {callback.from_user.username} ({callback.from_user.id}) "
            f"очистил черный список"
        )
        
        await callback.message.edit_text("✅ Черный список очищен")
        await callback.answer()

    # Регистрируем обработчики callback-запросов
    router.callback_query.register(
        open_blacklist_settings,
        F.data == f"{CBT.CATEGORY}:bl"
    )
    router.callback_query.register(
        act_ban_user,
        F.data == CBT.BAN
    )
    router.callback_query.register(
        act_unban_user,
        F.data == CBT.UNBAN
    )
    router.callback_query.register(
        clear_blacklist,
        F.data == "clear_blacklist"
    )

    # Регистрируем обработчики сообщений
    router.message.register(
        ban_user,
        BlacklistStates.waiting_for_ban
    )
    router.message.register(
        unban_user,
        BlacklistStates.waiting_for_unban
    )
    router.message.register(
        send_blacklist,
        Command("blacklist", "bl")
    )

    # Возвращаем роутер для регистрации в главном диспетчере
    return router


BIND_TO_PRE_INIT = [init_blacklist_cp]