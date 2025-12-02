from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nexus import Nexus

from tg_bot import utils, keyboards as kb, CBT
from tg_bot.static_keyboards import CLEAR_STATE_BTN
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from aiogram import F
import logging

logger = logging.getLogger("StarVellBot.tg_bot")


def init_templates_cp(nexus: Nexus, *args):
    """Инициализация модуля шаблонов ответов"""
    tg = nexus.telegram
    bot = tg.bot
    router = tg.router

    async def check_template_exists(template_index: int, message_obj: Message) -> bool:
        """
        Проверяет, существует ли шаблон с переданным индексом.
        
        :param template_index: индекс шаблона.
        :param message_obj: объект сообщения.
        :return: True, если шаблон существует.
        """
        templates = utils.load_answer_templates()
        if template_index > len(templates) - 1:
            update_button = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Обновить", callback_data=f"{CBT.TMPLT_LIST}:0")]
            ])
            await message_obj.answer(
                f"❌ Шаблон #{template_index} не найден",
                reply_markup=update_button
            )
            return False
        return True

    @router.callback_query(F.data.startswith(f"{CBT.TMPLT_LIST}:"))
    async def open_templates_list(c: CallbackQuery):
        """Открывает список шаблонов ответов"""
        offset = int(c.data.split(":")[1])
        await c.message.edit_text(
            "📝 <b>Шаблоны ответов</b>\n\nВыберите шаблон для редактирования:",
            reply_markup=kb.templates_list(nexus, offset)
        )
        await c.answer()

    @router.callback_query(F.data.startswith(f"{CBT.TMPLT_LIST_ANS_MODE}:"))
    async def open_templates_list_in_ans_mode(c: CallbackQuery):
        """Открывает список шаблонов в режиме ответа"""
        split = c.data.split(":")
        offset, node_id, username, prev_page = int(split[1]), int(split[2]), split[3], int(split[4])
        extra = split[5:] if len(split) > 5 else []
        
        await c.message.edit_text(
            "📝 <b>Выберите шаблон для отправки</b>",
            reply_markup=kb.templates_list_ans_mode(nexus, offset, node_id, username, prev_page, extra)
        )
        await c.answer()

    @router.callback_query(F.data.startswith(f"{CBT.EDIT_TMPLT}:"))
    async def open_edit_template_cp(c: CallbackQuery):
        """Открывает панель редактирования шаблона"""
        split = c.data.split(":")
        template_index, offset = int(split[1]), int(split[2])
        
        if not await check_template_exists(template_index, c.message):
            await c.answer()
            return

        templates = utils.load_answer_templates()
        template = templates[template_index]
        
        text = f"""<b>📝 Шаблон #{template_index + 1}</b>

<b>Текст:</b>
<code>{utils.escape(template)}</code>

<i>Последнее обновление: {__import__('datetime').datetime.now().strftime('%H:%M:%S')}</i>"""
        
        await c.message.edit_text(
            text,
            reply_markup=kb.edit_template(nexus, template_index, offset)
        )
        await c.answer()

    @router.callback_query(F.data.startswith(f"{CBT.ADD_TMPLT}:"))
    async def act_add_template(c: CallbackQuery):
        """Активирует режим добавления нового шаблона"""
        offset = int(c.data.split(":")[1])
        result = await c.message.answer(
            "📝 <b>Добавление нового шаблона</b>\n\nВведите текст шаблона:",
            reply_markup=CLEAR_STATE_BTN()
        )
        tg.set_state(c.message.chat.id, result.message_id, c.from_user.id, CBT.ADD_TMPLT, {"offset": offset})
        await c.answer()

    @router.message(F.text, lambda m: tg.check_state(m.chat.id, m.from_user.id, CBT.ADD_TMPLT))
    async def add_template(m: Message):
        """Добавляет новый шаблон"""
        user_state = tg.get_state(m.chat.id, m.from_user.id)
        offset = user_state["data"]["offset"]
        tg.clear_state(m.chat.id, m.from_user.id, True)
        
        template_text = m.text.strip()
        if not template_text:
            await m.answer("❌ Текст шаблона не может быть пустым")
            return
        
        templates = utils.load_answer_templates()
        templates.append(template_text)
        utils.save_answer_templates(templates)
        
        logger.info(f"Пользователь {m.from_user.username} ({m.from_user.id}) добавил шаблон: {template_text}")
        
        template_index = len(templates) - 1
        new_offset = utils.get_offset(template_index, 5)  # 5 шаблонов на страницу
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data=f"{CBT.TMPLT_LIST}:{offset}"),
                InlineKeyboardButton(text="➕ Еще", callback_data=f"{CBT.ADD_TMPLT}:{offset}"),
                InlineKeyboardButton(text="⚙️ Настроить", callback_data=f"{CBT.EDIT_TMPLT}:{template_index}:{new_offset}")
            ]
        ])
        
        await m.answer(
            f"✅ Шаблон добавлен!\n\n<code>{utils.escape(template_text)}</code>",
            reply_markup=keyboard
        )

    @router.callback_query(F.data.startswith(f"{CBT.DEL_TMPLT}:"))
    async def del_template(c: CallbackQuery):
        """Удаляет шаблон"""
        split = c.data.split(":")
        template_index, offset = int(split[1]), int(split[2])
        
        if not await check_template_exists(template_index, c.message):
            await c.answer()
            return

        templates = utils.load_answer_templates()
        template = templates.pop(template_index)
        utils.save_answer_templates(templates)
        
        logger.info(f"Пользователь {c.from_user.username} ({c.from_user.id}) удалил шаблон: {template}")
        
        await c.message.edit_text(
            "📝 <b>Шаблоны ответов</b>\n\nВыберите шаблон для редактирования:",
            reply_markup=kb.templates_list(nexus, offset)
        )
        await c.answer()

    @router.callback_query(F.data.startswith(f"{CBT.SEND_TMPLT}:"))
    async def send_template(c: CallbackQuery):
        """Отправляет шаблон в чат StarVell"""
        split = c.data.split(":")
        template_index, node_id, username, prev_page = int(split[1]), int(split[2]), split[3], int(split[4])
        extra = split[5:] if len(split) > 5 else []
        
        templates = utils.load_answer_templates()
        if template_index > len(templates) - 1:
            await c.answer("❌ Шаблон не найден", show_alert=True)
            return
        
        template = templates[template_index]
        
        # Отправляем сообщение через StarVell API
        success = await nexus.send_message(node_id, template)
        
        if success:
            await c.answer("✅ Шаблон отправлен!")
            logger.info(f"Пользователь {c.from_user.username} ({c.from_user.id}) отправил шаблон в чат {node_id}")
        else:
            await c.answer("❌ Ошибка отправки", show_alert=True)


BIND_TO_PRE_INIT = [init_templates_cp]