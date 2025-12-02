"""
Модуль загрузки файлов для StarVellBot (aiogram версия)
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Literal
import os
import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

if TYPE_CHECKING:
    from nexus import Nexus

logger = logging.getLogger("StarVellBot.tg_bot")


# ===== FSM States =====
class FileUploadStates(StatesGroup):
    """Состояния для загрузки файлов"""
    upload_products_file = State()
    upload_main_config = State()
    upload_auto_response_config = State()
    upload_auto_delivery_config = State()
    upload_plugin = State()
    upload_funpay_image = State()
    upload_chat_image = State()
    upload_offer_image = State()


def check_file(message: Message, expected_type: Literal["py", "cfg", "json", "txt"] | None = None) -> bool:
    """
    Проверяет файл на соответствие требованиям.
    
    :param message: сообщение с файлом.
    :param expected_type: ожидаемый тип файла.
    :return: True, если файл подходит.
    """
    if not message.document:
        return False
    
    file_name = message.document.file_name
    if not file_name:
        return False
    
    # Проверяем расширение файла
    if expected_type and not file_name.endswith(f".{expected_type}"):
        return False
    
    # Проверяем размер файла (максимум 20 МБ)
    if message.document.file_size > 20 * 1024 * 1024:
        return False
    
    return True


async def download_file(bot, message: Message, file_name: str = "temp_file.txt",
                       custom_path: str = "") -> bool:
    """
    Скачивает файл из Telegram.
    
    :param bot: экземпляр бота aiogram.
    :param message: сообщение с файлом.
    :param file_name: имя файла для сохранения.
    :param custom_path: кастомный путь для сохранения.
    :return: True, если файл успешно скачан.
    """
    try:
        # Определяем путь для сохранения
        if custom_path:
            save_path = custom_path
        else:
            save_path = f"storage/{file_name}"
        
        # Создаем директорию, если не существует
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # Скачиваем файл
        await bot.download(message.document, destination=save_path)
        
        logger.info(f"Файл {file_name} успешно скачан в {save_path}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка скачивания файла {file_name}: {e}")
        return False


def init_uploader(nexus: Nexus):
    """Инициализация модуля загрузки файлов"""
    router = Router()
    bot = nexus.telegram.bot

    def kb_cancel():
        """Клавиатура с кнопкой отмены"""
        kb = InlineKeyboardBuilder()
        kb.button(text="❌ Отмена", callback_data="CLEAR_STATE")
        return kb.as_markup()

    # ===== PRODUCTS FILE =====
    @router.callback_query(F.data == "upload_products_file")
    async def act_upload_products_file(callback: CallbackQuery, state: FSMContext):
        """Активирует режим загрузки файла с товарами"""
        await callback.message.answer(
            "📁 <b>Загрузка файла с товарами</b>\n\nОтправьте .txt файл с товарами:",
            reply_markup=kb_cancel()
        )
        await state.set_state(FileUploadStates.upload_products_file)
        await callback.answer()

    @router.message(FileUploadStates.upload_products_file, F.document)
    async def upload_products_file(message: Message, state: FSMContext):
        """Обрабатывает загрузку файла с товарами"""
        await state.clear()
        
        if not check_file(message, "txt"):
            await message.reply("❌ Неверный формат файла. Ожидается .txt файл.")
            return
        
        file_name = message.document.file_name
        if await download_file(bot, message, file_name, f"storage/products/{file_name}"):
            await message.reply(f"✅ Файл <code>{file_name}</code> успешно загружен!")
            logger.info(
                f"Пользователь {message.from_user.username} ({message.from_user.id}) "
                f"загрузил файл товаров: {file_name}"
            )
        else:
            await message.reply("❌ Ошибка загрузки файла")

    # ===== MAIN CONFIG =====
    @router.callback_query(F.data == "upload_main_config")
    async def act_upload_main_config(callback: CallbackQuery, state: FSMContext):
        """Активирует режим загрузки основного конфига"""
        await callback.message.answer(
            "⚙️ <b>Загрузка основного конфига</b>\n\nОтправьте .cfg файл:",
            reply_markup=kb_cancel()
        )
        await state.set_state(FileUploadStates.upload_main_config)
        await callback.answer()

    @router.message(FileUploadStates.upload_main_config, F.document)
    async def upload_main_config(message: Message, state: FSMContext):
        """Обрабатывает загрузку основного конфига"""
        await state.clear()
        
        if not check_file(message, "cfg"):
            await message.reply("❌ Неверный формат файла. Ожидается .cfg файл.")
            return
        
        file_name = message.document.file_name
        if file_name != "_main.cfg":
            await message.reply("❌ Файл должен называться '_main.cfg'")
            return
        
        if await download_file(bot, message, file_name, f"configs/{file_name}"):
            await message.reply(
                f"✅ Конфиг <code>{file_name}</code> успешно загружен!\n\n"
                "⚠️ Перезапустите бота для применения изменений."
            )
            logger.info(
                f"Пользователь {message.from_user.username} ({message.from_user.id}) "
                f"загрузил основной конфиг"
            )
        else:
            await message.reply("❌ Ошибка загрузки конфига")

    # ===== AUTO RESPONSE CONFIG =====
    @router.callback_query(F.data == "upload_auto_response_config")
    async def act_upload_auto_response_config(callback: CallbackQuery, state: FSMContext):
        """Активирует режим загрузки конфига автоответов"""
        await callback.message.answer(
            "🤖 <b>Загрузка конфига автоответов</b>\n\nОтправьте .cfg файл:",
            reply_markup=kb_cancel()
        )
        await state.set_state(FileUploadStates.upload_auto_response_config)
        await callback.answer()

    @router.message(FileUploadStates.upload_auto_response_config, F.document)
    async def upload_auto_response_config(message: Message, state: FSMContext):
        """Обрабатывает загрузку конфига автоответов"""
        await state.clear()
        
        if not check_file(message, "cfg"):
            await message.reply("❌ Неверный формат файла. Ожидается .cfg файл.")
            return
        
        file_name = message.document.file_name
        if file_name != "auto_response.cfg":
            await message.reply("❌ Файл должен называться 'auto_response.cfg'")
            return
        
        if await download_file(bot, message, file_name, f"configs/{file_name}"):
            await message.reply(f"✅ Конфиг <code>{file_name}</code> успешно загружен!")
            logger.info(
                f"Пользователь {message.from_user.username} ({message.from_user.id}) "
                f"загрузил конфиг автоответов"
            )
        else:
            await message.reply("❌ Ошибка загрузки конфига")

    # ===== AUTO DELIVERY CONFIG =====
    @router.callback_query(F.data == "upload_auto_delivery_config")
    async def act_upload_auto_delivery_config(callback: CallbackQuery, state: FSMContext):
        """Активирует режим загрузки конфига автовыдачи"""
        await callback.message.answer(
            "📦 <b>Загрузка конфига автовыдачи</b>\n\nОтправьте .cfg файл:",
            reply_markup=kb_cancel()
        )
        await state.set_state(FileUploadStates.upload_auto_delivery_config)
        await callback.answer()

    @router.message(FileUploadStates.upload_auto_delivery_config, F.document)
    async def upload_auto_delivery_config(message: Message, state: FSMContext):
        """Обрабатывает загрузку конфига автовыдачи"""
        await state.clear()
        
        if not check_file(message, "cfg"):
            await message.reply("❌ Неверный формат файла. Ожидается .cfg файл.")
            return
        
        file_name = message.document.file_name
        if file_name != "auto_delivery.cfg":
            await message.reply("❌ Файл должен называться 'auto_delivery.cfg'")
            return
        
        if await download_file(bot, message, file_name, f"configs/{file_name}"):
            await message.reply(f"✅ Конфиг <code>{file_name}</code> успешно загружен!")
            logger.info(
                f"Пользователь {message.from_user.username} ({message.from_user.id}) "
                f"загрузил конфиг автовыдачи"
            )
        else:
            await message.reply("❌ Ошибка загрузки конфига")

    # ===== PLUGIN =====
    @router.callback_query(F.data == "upload_plugin")
    async def act_upload_plugin(callback: CallbackQuery, state: FSMContext):
        """Активирует режим загрузки плагина"""
        await callback.message.answer(
            "🔌 <b>Загрузка плагина</b>\n\nОтправьте .py файл плагина:",
            reply_markup=kb_cancel()
        )
        await state.set_state(FileUploadStates.upload_plugin)
        await callback.answer()

    @router.message(FileUploadStates.upload_plugin, F.document)
    async def upload_plugin(message: Message, state: FSMContext):
        """Обрабатывает загрузку плагина"""
        await state.clear()
        
        if not check_file(message, "py"):
            await message.reply("❌ Неверный формат файла. Ожидается .py файл.")
            return
        
        file_name = message.document.file_name
        if await download_file(bot, message, file_name, f"plugins/{file_name}"):
            await message.reply(
                f"✅ Плагин <code>{file_name}</code> успешно загружен!\n\n"
                "⚠️ Перезапустите бота для загрузки плагина."
            )
            logger.info(
                f"Пользователь {message.from_user.username} ({message.from_user.id}) "
                f"загрузил плагин: {file_name}"
            )
        else:
            await message.reply("❌ Ошибка загрузки плагина")

    # ===== FUNPAY IMAGE =====
    @router.callback_query(F.data == "upload_funpay_image")
    async def act_upload_funpay_image(callback: CallbackQuery, state: FSMContext):
        """Активирует режим загрузки изображения для FunPay"""
        await callback.message.answer(
            "🖼️ <b>Загрузка изображения</b>\n\nОтправьте изображение:",
            reply_markup=kb_cancel()
        )
        await state.set_state(FileUploadStates.upload_funpay_image)
        await callback.answer()

    @router.message(FileUploadStates.upload_funpay_image, F.photo | F.document)
    async def send_funpay_image(message: Message, state: FSMContext):
        """Обрабатывает загрузку изображения для FunPay"""
        await state.clear()
        
        try:
            # Определяем тип файла
            if message.photo:
                file_id = message.photo[-1].file_id
            elif message.document:
                file_id = message.document.file_id
            else:
                await message.reply("❌ Отправьте изображение")
                return
            
            # Сохраняем изображение
            image_path = f"storage/temp_image_{message.message_id}.jpg"
            file = await bot.get_file(file_id)
            await bot.download_file(file.file_path, destination=image_path)
            
            await message.reply(f"✅ Изображение загружено: <code>{image_path}</code>")
            logger.info(
                f"Пользователь {message.from_user.username} ({message.from_user.id}) "
                f"загрузил изображение"
            )
            
        except Exception as e:
            logger.error(f"Ошибка загрузки изображения: {e}")
            await message.reply("❌ Ошибка загрузки изображения")

    # ===== CHAT IMAGE =====
    @router.callback_query(F.data == "upload_chat_image")
    async def act_upload_chat_image(callback: CallbackQuery, state: FSMContext):
        """Активирует режим загрузки изображения для чата"""
        await callback.message.answer(
            "💬 <b>Загрузка изображения для чата</b>\n\nОтправьте изображение:",
            reply_markup=kb_cancel()
        )
        await state.set_state(FileUploadStates.upload_chat_image)
        await callback.answer()

    @router.message(FileUploadStates.upload_chat_image, F.photo | F.document)
    async def upload_chat_image(message: Message, state: FSMContext):
        """Обрабатывает загрузку изображения для чата"""
        await state.clear()
        await upload_image_handler(message, "chat")

    # ===== OFFER IMAGE =====
    @router.callback_query(F.data == "upload_offer_image")
    async def act_upload_offer_image(callback: CallbackQuery, state: FSMContext):
        """Активирует режим загрузки изображения для лота"""
        await callback.message.answer(
            "🛍️ <b>Загрузка изображения для лота</b>\n\nОтправьте изображение:",
            reply_markup=kb_cancel()
        )
        await state.set_state(FileUploadStates.upload_offer_image)
        await callback.answer()

    @router.message(FileUploadStates.upload_offer_image, F.photo | F.document)
    async def upload_offer_image(message: Message, state: FSMContext):
        """Обрабатывает загрузку изображения для лота"""
        await state.clear()
        await upload_image_handler(message, "offer")

    # ===== HELPER FUNCTION =====
    async def upload_image_handler(message: Message, image_type: Literal["chat", "offer"]):
        """Универсальный обработчик загрузки изображений"""
        try:
            # Определяем тип файла
            if message.photo:
                file_id = message.photo[-1].file_id
            elif message.document:
                file_id = message.document.file_id
            else:
                await message.reply("❌ Отправьте изображение")
                return
            
            # Сохраняем изображение
            image_path = f"storage/{image_type}_image_{message.message_id}.jpg"
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            
            file = await bot.get_file(file_id)
            await bot.download_file(file.file_path, destination=image_path)
            
            await message.reply(f"✅ Изображение загружено: <code>{image_path}</code>")
            logger.info(
                f"Пользователь {message.from_user.username} ({message.from_user.id}) "
                f"загрузил {image_type} изображение"
            )
            
        except Exception as e:
            logger.error(f"Ошибка загрузки изображения: {e}")
            await message.reply("❌ Ошибка загрузки изображения")

    # ===== CLEAR STATE =====
    @router.callback_query(F.data == "CLEAR_STATE")
    async def clear_state_handler(callback: CallbackQuery, state: FSMContext):
        """Очищает состояние (отмена действия)"""
        await state.clear()
        await callback.message.edit_text("❌ Действие отменено")
        await callback.answer()

    # Возвращаем роутер для регистрации
    return router


BIND_TO_PRE_INIT = [init_uploader]