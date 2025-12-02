import json
import re
import time
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from StarVellAPI.starvell_config_FINAL_v14 import (
    build_numeric_attributes,
    NUMERIC_ATTRIBUTES_MAP,
    get_default_basic_attributes
)
from .preset_manager import PresetManager

import requests
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Document
from aiogram.utils.keyboard import InlineKeyboardBuilder


logger = logging.getLogger("plugin.create_lot_pro")
logger.setLevel(logging.INFO)

API_CREATE_URL = "https://starvell.com/api/offers/create" 
CATALOG_JSON_PATH = Path("plugins") / "utils" / "complete_categories_map.json"
SESSION_FILES = [Path("StarVellAPI") / "session.json", Path("session.json")]


class CreateLotFSM(StatesGroup):
    GAME = State()
    CATEGORY = State()
    SUBCATEGORY = State()
    
    PRESET_CHOICE = State()         
    
    PRESET_WIZARD_NAME = State()    
    PRESET_WIZARD_BASIC = State()   
    PRESET_WIZARD_NUMERIC = State() 
    PRESET_WIZARD_DELIVERY_FROM = State() 
    PRESET_WIZARD_DELIVERY_TO = State()   
    PRESET_WIZARD_POST_PAYMENT = State()  
    PRESET_WIZARD_CONFIRM = State() 
    
    NUMERIC_ATTRIBUTES_STEP = State()
    
    TITLE = State()
    DESCRIPTION = State()
    PRICE = State()
    CONFIRM = State()

CANCEL_COMMANDS = {"/create_lot_cancel", "отмена", "/cancel"}


# ==============================================================================
# ==============================================================================
class Catalog:
    """
    Парсит 'complete_categories_map.json' и предоставляет
    методы для навигации по играм, категориям и подкатегориям.
    """
    def __init__(self, json_path: Path = CATALOG_JSON_PATH):
        self.path = json_path
        self.data = self._load_data()

    def _load_data(self) -> Dict[str, Any]:
        if not self.path.exists():
            logger.critical(f"ФАЙЛ КАТАЛОГА НЕ НАЙДЕН: {self.path}")
            return {}
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if "all_categories_detailed" in data:
                logger.info(f"✅ Catalog: Успешно загружен {self.path}")
                return data["all_categories_detailed"]
            else:
                logger.error("❌ Catalog: 'all_categories_detailed' не найден в JSON.")
                return {}
        except (json.JSONDecodeError, IOError) as e:
            logger.critical(f"❌ Catalog: Ошибка загрузки/парсинга {self.path}: {e}")
            return {}

    def _get_game_name(self, game_slug: str) -> str:
        """Пытается угадать имя игры."""
        name = game_slug.replace('-', ' ').title()
        if "brawl-stars" in game_slug: name = "Brawl Stars"
        if "roblox" in game_slug: name = "Roblox"
        if "clash-royale" in game_slug: name = "Clash Royale"
        if "clash-of-clans" in game_slug: name = "Clash of Clans"
        return name

    def list_games(self) -> List[Tuple[str, str]]:
        """Возвращает список игр: (slug, name)"""
        games = []
        for slug in self.data.keys():
            games.append((slug, self._get_game_name(slug)))
        return sorted(games, key=lambda g: g[1])

    def get_game_name(self, slug: str) -> str:
        return self._get_game_name(slug)

    def list_categories(self, game_slug: str) -> List[Tuple[str, str, int]]:
        """
        Возвращает список категорий (продуктов) для игры.
        Формат: (slug, name, id)
        """
        game_data = self.data.get(game_slug, {})
        categories = []
        for cat_slug, cat_details in game_data.items():
            if cat_details.get("isActive", True): 
                categories.append((
                    cat_slug, # e.g. 'gems'
                    cat_details.get("name", cat_slug.title()), # e.g. 'Гемы'
                    cat_details.get("id") # e.g. 128
                ))
        categories.sort(key=lambda c: (game_data[c[0]].get("position", 99), c[1]))
        return categories

    def get_category_name(self, game_slug: str, cat_slug: str) -> str:
        """Возвращает имя категории по slug."""
        cat_details = self.data.get(game_slug, {}).get(cat_slug, {})
        return cat_details.get("name", cat_slug.title())

    def list_subcategories(self, game_slug: str, cat_slug: str) -> List[Tuple[str, str, int]]:
        """
        Возвращает список ПОДкатегорий, отсортированный по 'position'.
        Формат: (slug, name, id)
        """
        cat_details = self.data.get(game_slug, {}).get(cat_slug, {})
        sub_cats_list = cat_details.get("subCategories", [])
        
        if not sub_cats_list:
            return []
            
        subcategories_with_pos = []
        for sub_details in sub_cats_list:
            if sub_details.get("isActive", True):
                subcategories_with_pos.append((
                    sub_details.get("slug"), # [0] e.g. null
                    sub_details.get("name"), # [1] e.g. '30 гемов'
                    sub_details.get("id"),   # [2] e.g. 438
                    sub_details.get("position", 99) # [3] e.g. 1
                ))
        
        subcategories_with_pos.sort(key=lambda s: s[3])
        
        return [(slug, name, _id) for slug, name, _id, pos in subcategories_with_pos]

    def get_subcategory_details(self, game_slug: str, cat_slug: str, sub_id: int) -> Optional[Dict[str, Any]]:
        """Находит subcategory по ID и возвращает ее dict."""
        cat_details = self.data.get(game_slug, {}).get(cat_slug, {})
        sub_cats_list = cat_details.get("subCategories", [])
        for sub in sub_cats_list:
            if sub.get("id") == sub_id:
                return sub
        return None

    def get_category_details(self, game_slug: str, cat_slug: str) -> Optional[Dict[str, Any]]:
        """Возвращает dict категории (продукта)."""
        return self.data.get(game_slug, {}).get(cat_slug, {})

# ==============================================================================
# ==============================================================================
class CreateLotPro:
    def __init__(self, nexus):
        self.nexus = nexus
        
        self.name = "CreateLotPro"
        self.version = "4.5.0"
        self.author = "@AnastasiaPisun"
        self.description = "Создание лотов"
        self.enabled = True
        
        self.commands = [
            {"command": "create_lot", "description": "Создать новый лот"},
            {"command": "create_lot_cancel", "description": "Отменить создание лота"},
            {"command": "presets", "description": "Управление пресетами"},
        ]
        
        self.buttons = [
            {"text": "➕ Новый лот", "callback": "clp:start"},
            {"text": "📋 Пресеты", "callback": "clp:presets"},
        ]
        
        self.catalog = Catalog(json_path=CATALOG_JSON_PATH) 
        self.preset_manager = PresetManager()
        
        self.sid = self._load_session_from_config()
        if not self.sid:
            logger.error("КРИТИЧЕСКАЯ ОШИБКА: Не удалось загрузить session из конфига.")
            
        self.session = self._get_session(self.sid)
        
        self.router = Router(name="create_lot_pro")
        self.setup_handlers()

    def _load_session_from_config(self) -> Optional[str]:
        try:
            if self.nexus and hasattr(self.nexus, 'account') and self.nexus.account:
                if hasattr(self.nexus.account, 'session_id'):
                    sid = self.nexus.account.session_id
                    if sid:
                        logger.info(f"Сессия {sid[:10]}... загружена из nexus.account")
                        return sid
            
            if self.nexus and hasattr(self.nexus, 'main_cfg'):
                main_cfg = self.nexus.main_cfg
                if isinstance(main_cfg, dict):
                    starvell_section = main_cfg.get("StarVell", {})
                    sid = (starvell_section.get("session") or starvell_section.get("session_id") or "").strip()
                    if sid:
                        logger.info(f"Сессия {sid[:10]}... загружена из configs/_main.cfg")
                        return sid
            
            for f in SESSION_FILES:
                if f.exists():
                    try:
                        with open(f, 'r') as file:
                            data = json.load(file)
                            sid = data.get("session_id")
                            if sid:
                                logger.warning(f"⚠️ Сессия {sid[:10]}... загружена из {f} (старый способ, рекомендуется использовать configs/_main.cfg)")
                                return sid
                    except Exception:
                        continue
            
            logger.error("Не удалось найти session ни в конфиге, ни в session.json")
            return None
        except Exception as e:
            logger.error(f"Ошибка загрузки сессии: {e}")
            return None

    def setup_handlers(self):
        logger.info("CreateLotPro (Preset Logic v4.5): Регистрация обработчиков...")
        
        self.router.message(Command("plugin_diag"))(self.diag)
        self.router.message(Command("create_lot"))(self.start)
        self.router.message(Command("create_lot_cancel"))(self.cancel)
        self.router.message(F.text.lower().in_(CANCEL_COMMANDS))(self.cancel)
        self.router.message(Command("manage_presets"))(self.start_preset_manager)

        self.router.callback_query(F.data.startswith("pick_game:"))(self.handle_game_choice)
        self.router.callback_query(F.data.startswith("pick_cat:"))(self.handle_category_choice)
        self.router.callback_query(F.data.startswith("pick_sub:"))(self.handle_subcategory_choice)
        
        self.router.callback_query(CreateLotFSM.PRESET_CHOICE, F.data.startswith("preset_pick:"))(self.handle_preset_pick)
        self.router.callback_query(CreateLotFSM.PRESET_CHOICE, F.data == "preset_create_new")(self.handle_preset_create_start)
        self.router.callback_query(CreateLotFSM.PRESET_CHOICE, F.data.startswith("preset_delete:"))(self.handle_preset_delete)

        self.router.callback_query(CreateLotFSM.PRESET_WIZARD_BASIC, F.data.startswith("wiz_basic:"))(self.handle_wizard_basic_choice)
        self.router.callback_query(CreateLotFSM.PRESET_WIZARD_NUMERIC, F.data.startswith("wiz_numeric:"))(self.handle_wizard_numeric_choice)
        self.router.callback_query(CreateLotFSM.PRESET_WIZARD_CONFIRM, F.data.startswith("wiz_confirm:"))(self.handle_wizard_confirm)

        self.router.callback_query(F.data.startswith("confirm_lot:"))(self.handle_confirm_choice)

        self.router.message(CreateLotFSM.PRESET_WIZARD_NAME)(self.handle_preset_wizard_name)
        self.router.message(CreateLotFSM.PRESET_WIZARD_DELIVERY_FROM)(self.handle_wizard_delivery_from)
        self.router.message(CreateLotFSM.PRESET_WIZARD_DELIVERY_TO)(self.handle_wizard_delivery_to)
        self.router.message(CreateLotFSM.PRESET_WIZARD_POST_PAYMENT)(self.handle_wizard_post_payment)
        
        self.router.message(CreateLotFSM.NUMERIC_ATTRIBUTES_STEP)(self.handle_numeric_input)
        self.router.message(CreateLotFSM.TITLE)(self.handle_title_input)
        self.router.message(CreateLotFSM.DESCRIPTION)(self.handle_description_input)
        self.router.message(CreateLotFSM.PRICE)(self.handle_price_input)
        
        logger.info("CreateLotPro (Preset Logic v4.5): Регистрация завершена.")

    async def diag(self, message: Message, state: FSMContext):
        st = await state.get_state()
        session_status = f"ЗАГРУЖЕНА (ID: {self.sid[:10]}...)" if self.sid else "НЕ НАЙДЕНА (ПРОВЕРЬ configs/_main.cfg)"
        
        await message.answer(
            f"✅ CreateLotPro (Preset Logic v4.5) активен.\n"
            f"📚 Игр загружено: {len(self.catalog.list_games())}\n"
            f"🔑 Сессия: {session_status}\n"
            f"FSM Состояние: {st or 'IDLE'}"
        )

    async def cancel(self, message: Message, state: FSMContext):
        current_state = await state.get_state()
        if current_state is None:
            await message.answer("Нет активного процесса для отмены.")
            return
            
        await state.clear()
        await message.answer("❌ Мастер создания лота отменен.")

    async def start(self, message: Message, state: FSMContext):
        if not self.sid:
            await message.answer("⚠️ <b>Критическая ошибка:</b>\nSession не найдена в `configs/_main.cfg` (секция [StarVell], ключ 'session' или 'session_id').\nПлагин не может отправлять запросы. Проверь конфиг и перезапусти бота.")
            return

        await state.clear()
        
        games = self.catalog.list_games()
        if not games:
            await message.answer("⚠️ Ошибка: не могу загрузить список игр из каталога (проверь JSON).")
            return

        kb = InlineKeyboardBuilder()
        for slug, name in games:
            kb.button(text=name, callback_data=f"pick_game:{slug}")
        kb.adjust(2) 

        await state.set_state(CreateLotFSM.GAME)
        await message.answer("🕹 <b>Шаг 1: Выбери игру</b>", reply_markup=kb.as_markup())

    
    async def handle_game_choice(self, query: CallbackQuery, state: FSMContext):
        game_slug = query.data.split(":")[-1]
        game_name = self.catalog.get_game_name(game_slug)
        
        await state.update_data(game_slug=game_slug, game_name=game_name)
        
        cats = self.catalog.list_categories(game_slug)
        if not cats:
            await query.answer("Ошибка: в этой игре нет категорий.", show_alert=True)
            return

        kb = InlineKeyboardBuilder()
        for slug, name, _id in cats: 
            kb.button(text=name, callback_data=f"pick_cat:{slug}:{_id}")
        kb.adjust(2)

        await state.set_state(CreateLotFSM.CATEGORY)
        await query.message.edit_text(
            f"<b>Игра:</b> {game_name}\n\n"
            f"📦 <b>Шаг 2: Выбери категорию (продукт)</b>",
            reply_markup=kb.as_markup()
        )
        await query.answer()

    async def handle_category_choice(self, query: CallbackQuery, state: FSMContext):
        _parts = query.data.split(":")
        cat_slug, cat_id = _parts[1], int(_parts[2])
        
        data = await state.get_data()
        game_slug = data["game_slug"]
        cat_name = self.catalog.get_category_name(game_slug, cat_slug)
        
        await state.update_data(
            cat_slug=cat_slug, 
            cat_id=cat_id, 
            cat_name=cat_name,
            cat_slug_for_filters=cat_slug
        )

        subs = self.catalog.list_subcategories(game_slug, cat_slug)
        
        if subs:
            kb = InlineKeyboardBuilder()
            for slug, name, _id in subs:
                kb.button(text=name, callback_data=f"pick_sub:{_id}")
            kb.adjust(2)
            await state.set_state(CreateLotFSM.SUBCATEGORY)
            await query.message.edit_text(f"<b>Игра:</b> {data['game_name']}\n<b>Категория:</b> {cat_name}\n\n🧱 <b>Шаг 3: Выбери подкатегорию</b>", reply_markup=kb.as_markup())
        else:
            await query.message.edit_text(f"<b>Игра:</b> {data['game_name']}\n<b>Категория:</b> {cat_name}\n\n⚙️ Загружаю пресеты...")
            
            await state.update_data(
                slug_key=f"{game_slug}__{cat_slug}",
                id_key=cat_id,
                sub_id=None
            )
            
            await self.show_preset_choice(query.message, state)
        
        await query.answer()

    async def handle_subcategory_choice(self, query: CallbackQuery, state: FSMContext):
        sub_id = int(query.data.split(":")[-1])

        data = await state.get_data()
        game_slug = data["game_slug"]
        cat_slug = data["cat_slug"]
        cat_id = data["cat_id"]
        
        sub_details = self.catalog.get_subcategory_details(game_slug, cat_slug, sub_id)
        if not sub_details:
            await query.answer("Ошибка: не могу найти подкатегорию.", show_alert=True)
            return

        sub_name = sub_details.get("name")

        await query.message.edit_text(
            f"<b>Игра:</b> {data['game_name']}\n<b>Категория:</b> {data['cat_name']}\n<b>Подкатегория:</b> {sub_name}\n\n⚙️ Загружаю пресеты...")
        
        await state.update_data(
            sub_id=sub_id,
            sub_name=sub_name,
            
            id_key=cat_id,
            
            slug_key=f"{game_slug}__{cat_slug}",
            
            sub_id_for_filters=sub_id 
        )

        await self.show_preset_choice(query.message, state)
        await query.answer()

    async def show_preset_choice(self, message: Message, state: FSMContext):
        data = await state.get_data()
        
        id_key = data.get("id_key") 
        slug_key = data.get("slug_key") 
        
        if not id_key or not slug_key:
            await message.answer("❌ Критическая ошибка FSM (no keys). Начните заново /create_lot")
            await state.clear()
            return
        
        id_key_str = str(id_key)
        preset_names = self.preset_manager.get_preset_names(id_key_str)
        
        kb = InlineKeyboardBuilder()
        for name in preset_names:
            kb.button(text=name, callback_data=f"preset_pick:{name}")
        
        kb.button(text="➕ Создать новый пресет", callback_data="preset_create_new") 
        
        if len(preset_names) > 1:
            for name in preset_names:
                if name != "[ДЕФОЛТ]":
                    kb.button(text=f"❌ Удалить {name}", callback_data=f"preset_delete:{name}")
        kb.adjust(1)
        
        await state.set_state(CreateLotFSM.PRESET_CHOICE)
        await message.answer(
            f"🗂 <b>Шаг 4: Выбери пресет атрибутов</b>\n\n"
            f"Для: `{slug_key}`\n"
            f"(ID для API: `{id_key}`) ", 
            reply_markup=kb.as_markup()
        )

    async def handle_preset_pick(self, query: CallbackQuery, state: FSMContext):
        preset_name = query.data[len("preset_pick:"):]
        data = await state.get_data()
        id_key = data["id_key"]
        slug_key = data["slug_key"]
        
        preset_data = self.preset_manager.get_preset_data(str(id_key), slug_key, preset_name)
        
        await state.update_data(
            chosen_preset_name=preset_name,
            chosen_preset_data=preset_data
        )
        
        await query.message.edit_text(f"✅ Выбран пресет: <b>{preset_name}</b>")
        
        numeric_to_ask = preset_data.get("numeric_to_ask", [])
        
        if numeric_to_ask:
            await state.update_data(
                numeric_fields_to_ask=numeric_to_ask,
                current_numeric_field_index=0,
                user_numeric_inputs={} 
            )
            await state.set_state(CreateLotFSM.NUMERIC_ATTRIBUTES_STEP)
            await query.message.answer(f"🔢 Введи значение для: <b>{numeric_to_ask[0]}</b>")
        else:
            await state.set_state(CreateLotFSM.TITLE)
            await query.message.answer("✍️ <b>Шаг 5: Введи название лота</b>")
        
        await query.answer()

    async def handle_preset_create_start(self, query: CallbackQuery, state: FSMContext):
        await state.set_state(CreateLotFSM.PRESET_WIZARD_NAME)
        await query.message.edit_text("✍️ <b>Мастер создания пресета (1/6)</b>\n\nВведи **имя** для нового пресета (например: 'Brawl Pass Подарком').\n\n(Чтобы перезаписать старый, введи его имя)")
        await query.answer()

    async def handle_preset_wizard_name(self, message: Message, state: FSMContext):
        preset_name = message.text.strip()
        if preset_name == "[ДЕФОЛТ]":
            await message.answer("⚠️ Нельзя использовать имя '[ДЕФОЛТ]'. Попробуй другое.")
            return
            
        data = await state.get_data()
        game_slug = data["game_slug"]
        cat_slug = data["cat_slug"]
        
        all_filters = []
        
        cat_details = self.catalog.get_category_details(game_slug, cat_slug)
        if cat_details:
             all_filters = cat_details.get("filters", [])
        
        if not all_filters:
            await message.answer(f"⚠️ Не найдены Basic-атрибуты (filters) в JSON для '{cat_slug}'.\n\nПерехожу к Numeric-полям...")
            await state.update_data(
                new_preset_name=preset_name,
                new_preset_basic=[],
                wizard_numeric_fields=[],
                wizard_all_numeric_fields=list(NUMERIC_ATTRIBUTES_MAP.get(data['slug_key'], [])) 
            )
            await state.set_state(CreateLotFSM.PRESET_WIZARD_NUMERIC)
            await self.ask_wizard_numeric_question(message, state)
            return

        await state.update_data(
            new_preset_name=preset_name,
            wizard_all_filters=all_filters,
            wizard_current_filter_index=0,
            new_preset_basic=[]
        )
        
        await state.set_state(CreateLotFSM.PRESET_WIZARD_BASIC)
        await message.answer(f"✅ Имя: <b>{preset_name}</b>\n\n✍️ <b>Мастер (2/6) - Basic-атрибуты</b>\n\nЯ буду показывать вопросы, а ты выбирай 1 вариант, который должен быть в этом пресете.")
        await self.ask_wizard_basic_question(message, state)

    async def ask_wizard_basic_question(self, message: Message, state: FSMContext):
        data = await state.get_data()
        idx = data["wizard_current_filter_index"]
        all_filters = data["wizard_all_filters"]
        
        if idx >= len(all_filters):
            await state.set_state(CreateLotFSM.PRESET_WIZARD_NUMERIC)
            slug_key = data['slug_key'] 
            all_numeric_possible = list(NUMERIC_ATTRIBUTES_MAP.get(slug_key, []))
            
            await state.update_data(
                wizard_numeric_fields=[], 
                wizard_all_numeric_fields=all_numeric_possible
            )
            await message.answer("✅ <b>Basic-атрибуты настроены.</b>\n\n✍️ <b>Мастер (3/6) - Numeric-поля</b>\n\nТеперь выбери *имена* полей, которые нужно будет вводить (например: 'Уровень').")
            await self.ask_wizard_numeric_question(message, state)
            return

        current_filter = all_filters[idx]
        question_name = current_filter.get("nameRu", "N/A")
        options = current_filter.get("options", [])

        kb = InlineKeyboardBuilder()
        for i, opt in enumerate(options):
            kb.button(text=f"{i+1}. {opt.get('nameRu', 'N/A')}", callback_data=f"wiz_basic:choose:{idx}:{i}")
        
        kb.button(text="➡️ (Пропустить этот вопрос)", callback_data=f"wiz_basic:skip:{idx}")
        kb.adjust(1) 

        await message.answer(f"<b>Шаг {idx+1}/{len(all_filters)}:</b> {question_name}\n\n(Выбери 1 опцию для пресета или пропусти)", reply_markup=kb.as_markup())

    async def handle_wizard_basic_choice(self, query: CallbackQuery, state: FSMContext):
        parts = query.data.split(":")
        action = parts[1]
        q_idx = int(parts[2])
        
        data = await state.get_data()
        
        if q_idx != data["wizard_current_filter_index"]:
            await query.answer("Это старый вопрос", show_alert=True)
            return

        all_filters = data["wizard_all_filters"]
        current_filter = all_filters[q_idx]
        
        if action == "choose":
            opt_idx = int(parts[3])
            chosen_option = current_filter["options"][opt_idx]
            chosen_option_name = chosen_option.get("nameRu", "N/A")
            
            basic_to_save = {
                "id": current_filter.get("id"), 
                "optionId": chosen_option.get("id") 
            }
            
            new_preset_basic = data["new_preset_basic"]
            new_preset_basic.append(basic_to_save)
            await state.update_data(new_preset_basic=new_preset_basic)
            
            await query.message.edit_text(f"✅ <b>{current_filter.get('nameRu')}</b>: {chosen_option_name}")
        
        elif action == "skip":
            await query.message.edit_text(f"➡️ <b>{current_filter.get('nameRu')}</b>: (Пропущено)")

        await state.update_data(wizard_current_filter_index=q_idx + 1)
        await self.ask_wizard_basic_question(query.message, state) 
        await query.answer()


    async def ask_wizard_numeric_question(self, message: Message, state: FSMContext):
        data = await state.get_data()
        all_numeric_fields = data["wizard_all_numeric_fields"] 
        chosen_fields = data["wizard_numeric_fields"] 
        
        if not all_numeric_fields:
            await message.answer("ℹ️ Для этой категории не найдено Numeric-полей в конфиге (NUMERIC_ATTRIBUTES_MAP). Пропускаю...")
            await state.set_state(CreateLotFSM.PRESET_WIZARD_DELIVERY_FROM)
            await message.answer("✍️ <b>Мастер (4/6)</b>\n\nВведи время доставки <b>ОТ</b> (в минутах, напр: 15)")
            return

        kb = InlineKeyboardBuilder()
        
        for field_data in all_numeric_fields:
            field_name = field_data.get("nameRu")
            if field_name and field_name not in chosen_fields:
                kb.button(text=f"➕ {field_name}", callback_data=f"wiz_numeric:add:{field_name}")
        
        if chosen_fields:
            kb.button(text=f"➖ Убрать последнее ({chosen_fields[-1]})", callback_data="wiz_numeric:remove")
            
        kb.button(text="✅ ЗАВЕРШИТЬ (Numeric)", callback_data="wiz_numeric:done")
        kb.adjust(1)
        
        text = "<b>Выбери Numeric-поля (для ввода):</b>\n\n"
        if chosen_fields:
            text += "Выбрано:\n" + "\n".join([f"  - `{name}`" for name in chosen_fields])
        else:
            text += "(Пока ничего не выбрано)"
            
        await message.answer(text, reply_markup=kb.as_markup())


    async def handle_wizard_numeric_choice(self, query: CallbackQuery, state: FSMContext):
        
        parts = query.data.split(":")
        action = parts[1]
        
        data = await state.get_data()
        chosen_fields = data["wizard_numeric_fields"] 
        
        if action == "add":
            field_name = query.data[len("wiz_numeric:add:"):]
            if field_name not in chosen_fields:
                chosen_fields.append(field_name)
                await state.update_data(wizard_numeric_fields=chosen_fields)
            await query.answer(f"Добавлено: {field_name}")
            
        elif action == "remove":
            if chosen_fields:
                removed = chosen_fields.pop()
                await state.update_data(wizard_numeric_fields=chosen_fields)
                await query.answer(f"Убрано: {removed}")
            else:
                await query.answer("Нечего убирать")
                
        elif action == "done":
            await query.message.delete() 
            await query.answer("Numeric-поля выбраны.")
            
            await state.set_state(CreateLotFSM.PRESET_WIZARD_DELIVERY_FROM)
            await query.message.answer("✍️ <b>Мастер (4/6)</b>\n\nВведи время доставки <b>ОТ</b> (в минутах, напр: 15)")
            return 

        await self.ask_wizard_numeric_question(query.message, state)


    async def handle_wizard_delivery_from(self, message: Message, state: FSMContext):
        """Юзер ввел 'Delivery time FROM'."""
        try:
            from_value = int(message.text.strip())
            if from_value < 0: raise ValueError("Must be positive")
            
            await state.update_data(new_preset_delivery_from=from_value)
            await state.set_state(CreateLotFSM.PRESET_WIZARD_DELIVERY_TO)
            await message.answer(f"✅ <b>ОТ:</b> {from_value} мин.\n\n✍️ <b>Мастер (5/6)</b>\n\nВведи время доставки <b>ДО</b> (в минутах, напр: 60)")
        except (ValueError, TypeError):
            await message.answer("⚠️ Ошибка. Введи только число (например: 15). Попробуй еще раз:")

    async def handle_wizard_delivery_to(self, message: Message, state: FSMContext):
        """Юзер ввел 'Delivery time TO'."""
        try:
            to_value = int(message.text.strip())
            data = await state.get_data()
            from_value = data.get("new_preset_delivery_from", 0)
            
            if to_value < from_value:
                await message.answer(f"⚠️ Ошибка. 'ДО' ({to_value}) не может быть меньше 'ОТ' ({from_value}). Попробуй еще раз:")
                return
                
            await state.update_data(new_preset_delivery_to=to_value)
            await state.set_state(CreateLotFSM.PRESET_WIZARD_POST_PAYMENT)
            await message.answer(f"✅ <b>ДО:</b> {to_value} мин.\n\n✍️ <b>Мастер (6/6)</b>\n\nВведи 'Сообщение после оплаты' (текст, который увидит покупатель).")
        except (ValueError, TypeError):
            await message.answer("⚠️ Ошибка. Введи только число (например: 60). Попробуй еще раз:")

    async def handle_wizard_post_payment(self, message: Message, state: FSMContext):
        """Юзер ввел 'Post Payment Message'."""
        text = message.text.strip()
        if not text:
            await message.answer("⚠️ Сообщение не может быть пустым. Введи хотя бы что-то (напр: 'Спасибо за покупку').")
            return
            
        await state.update_data(new_preset_post_payment=text)
        await message.answer("✅ <b>Сообщение сохранено.</b>\n\nМастер завершен, проверяем пресет...")
        await self.show_wizard_confirmation(message, state)


    async def show_wizard_confirmation(self, message: Message, state: FSMContext):
        await state.set_state(CreateLotFSM.PRESET_WIZARD_CONFIRM)
        data = await state.get_data()
        
        name = data["new_preset_name"]
        basic_list = data["new_preset_basic"] 
        numeric_list = data["wizard_numeric_fields"] 
        
        from_val = data.get("new_preset_delivery_from", 15)
        to_val = data.get("new_preset_delivery_to", 60)
        post_msg = data.get("new_preset_post_payment", " ")
        
        basic_text = f"{len(basic_list)} шт." if basic_list else "Нет"
        numeric_text = "\n".join([f"  - `{name}`" for name in numeric_list]) if numeric_list else "Нет"

        text = (
            f"<b>✅ Мастер завершен. Проверь пресет:</b>\n\n"
            f"<b>Имя:</b> {name}\n"
            f"<b>Basic-атрибуты:</b> {basic_text}\n"
            f"<b>Numeric-поля (для ввода):</b>\n{numeric_text}\n"
            f"<b>Время доставки:</b> {from_val} - {to_val} мин.\n"
            f"<b>Сообщение покупателю:</b> {post_msg}\n\n"
            f"<b>Сохранить этот пресет?</b>\n"
            f"(Если пресет с именем '{name}' уже есть, он будет <u>перезаписан!</u>)"
        )
        
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Да, сохранить", callback_data="wiz_confirm:save")
        kb.button(text="❌ Нет, отмена", callback_data="wiz_confirm:cancel")
        await message.answer(text, reply_markup=kb.as_markup())


    async def handle_wizard_confirm(self, query: CallbackQuery, state: FSMContext):
        
        action = query.data.split(":")[1]
        
        if action == "cancel":
            await query.message.edit_text("❌ Создание пресета отменено.")
            await self.show_preset_choice(query.message, state)
            await query.answer()
            return

        data = await state.get_data()
        
        id_key = str(data["id_key"])
        preset_name = data["new_preset_name"]
        
        preset_data_to_save = {
            "basic": data["new_preset_basic"],
            "numeric_to_ask": data["wizard_numeric_fields"],
            "postPaymentMessage": data.get("new_preset_post_payment", " "),
            "deliveryTime": {
                "from": {"unit": "MINUTES", "value": data.get("new_preset_delivery_from", 15)},
                "to": {"unit": "MINUTES", "value": data.get("new_preset_delivery_to", 60)}
            }
        }
        
        success = self.preset_manager.save_preset(id_key, preset_name, preset_data_to_save)
        
        if success:
            await query.message.edit_text(f"✅ Пресет <b>{preset_name}</b> для (ID: `{id_key}`) успешно сохранен!")
        else:
            await query.message.edit_text(f"❌ Ошибка сохранения пресета (см. логи).")
            
        await self.show_preset_choice(query.message, state)
        await query.answer()
            
            
    async def handle_preset_delete(self, query: CallbackQuery, state: FSMContext):
        preset_name = query.data[len("preset_delete:"):]
        data = await state.get_data()
        id_key = str(data["id_key"])
        
        deleted = self.preset_manager.delete_preset(id_key, preset_name)
        
        if deleted:
            await query.answer(f"Пресет '{preset_name}' удален!", show_alert=True)
            await self.show_preset_choice(query.message, state) 
        else:
            await query.answer(f"Не удалось удалить '{preset_name}'", show_alert=True)


    async def handle_numeric_input(self, message: Message, state: FSMContext):
        data = await state.get_data()
        idx = data["current_numeric_field_index"]
        fields_to_ask = data["numeric_fields_to_ask"] 
        current_field_name = fields_to_ask[idx]
        user_inputs = data["user_numeric_inputs"]
        try:
            value = int(message.text.strip())
            if value < 0: raise ValueError("Value must be positive")
            user_inputs[current_field_name] = value
            await message.answer(f"✅ <b>{current_field_name}</b>: {value}")
            next_idx = idx + 1
            if next_idx < len(fields_to_ask):
                await state.update_data(current_numeric_field_index=next_idx, user_numeric_inputs=user_inputs)
                next_field = fields_to_ask[next_idx]
                await message.answer(f"🔢 Введи значение для: <b>{next_field}</b>")
            else:
                await state.update_data(user_numeric_inputs=user_inputs)
                await state.set_state(CreateLotFSM.TITLE)
                await message.answer("✍️ <b>Шаг 5: Введи название лота</b>")
        except (ValueError, TypeError):
            await message.answer("⚠️ Ошибка. Введи только число (например: 100). Попробуй еще раз:")

    async def handle_title_input(self, message: Message, state: FSMContext):
        title = message.text.strip()
        if not (5 < len(title) < 100): 
            await message.answer("⚠️ Название слишком короткое или длинное (6-99 симв). Попробуй еще раз.")
            return
        await state.update_data(title=title)
        await state.set_state(CreateLotFSM.DESCRIPTION)
        await message.answer("📝 <b>Шаг 6: Введи описание лота</b>")

    async def handle_description_input(self, message: Message, state: FSMContext):
        desc = message.text.strip()
        if len(desc) < 10:
            await message.answer("⚠️ Описание слишком короткое (мин 10 симв). Попробуй еще раз.")
            return
        await state.update_data(description=desc)
        await state.set_state(CreateLotFSM.PRICE)
        await message.answer("💰 <b>Шаг 7: Введи цену (только число)</b>")

    async def handle_price_input(self, message: Message, state: FSMContext):
        try:
            price_str = message.text.strip()
            price_int = int(price_str) 
            if price_int <= 0:
                raise ValueError("Price must be positive")
            
            await state.update_data(price=price_str) 
            
            await state.set_state(CreateLotFSM.CONFIRM)
            data = await state.get_data()
            await self.show_confirmation(message, data)
            
        except (ValueError, TypeError):
            await message.answer("⚠️ Ошибка. Введи цену как число (например: 150). Попробуй еще раз.")

    async def show_confirmation(self, message: Message, data: dict):
        preset_name = data.get('chosen_preset_name', 'N/A')
        numeric_text = "Не указаны"
        inputs = data.get("user_numeric_inputs", {})
        if inputs:
            numeric_text = "\n".join([f"  - {k}: {v}" for k, v in inputs.items()])
        api_category_id = data.get("id_key", "N/A")
        text = (
            f"<b>🔍 ПРОВЕРЬ ДАННЫЕ ЛОТА</b>\n\n"
            f"<b>Игра:</b> {data['game_name']}\n"
            f"<b>Категория:</b> {data.get('sub_name', data.get('cat_name'))}\n"
            f"<b>Пресет:</b> {preset_name}\n(ID для API: `{api_category_id}`)\n\n"
            f"<b>Название:</b> {data['title']}\n"
            f"<b>Цена:</b> {data['price']} руб.\n\n"
            f"<b>Описание:</b>\n{data['description']}\n\n"
            f"<b>Numeric Атрибуты:</b>\n{numeric_text}\n\n"
            f"<b>Всё верно? Создаем лот?</b>"
        )
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Да, создать", callback_data="confirm_lot:yes")
        kb.button(text="❌ Нет, отмена", callback_data="confirm_lot:no")
        await message.answer(text, reply_markup=kb.as_markup())


    async def handle_confirm_choice(self, query: CallbackQuery, state: FSMContext):
        choice = query.data.split(":")[-1]
        if choice == "no":
            await state.clear()
            await query.message.edit_text("❌ Создание лота отменено.")
            await query.answer()
            return

        await query.message.edit_text("⏳ Создаю лот, пожалуйста, подожди...")
        data = await state.get_data()
        
        id_key = data.get("id_key") # ID Категории (e.g. 128)
        slug_key = data.get("slug_key") # 'brawl-stars__gems'
        sub_id = data.get("sub_id") # ID Подкатегории (e.g. 438) or None
        
        preset_data = data['chosen_preset_data']
        title_str = data.get("title")
        desc_str = data.get("description")
        price_str = data.get("price")
        
        if not id_key or not title_str or not desc_str or not price_str:
            await query.message.edit_text("❌ Критическая ошибка FSM (отсутствуют данные). Начните заново /create_lot")
            await state.clear()
            return
            
        default_attrs_list = get_default_basic_attributes(slug_key)
        custom_attrs_list = preset_data.get("basic", [])

        merged_attrs_map = {}
        for attr in default_attrs_list:
            if 'id' in attr and 'optionId' in attr:
                merged_attrs_map[attr['id']] = attr['optionId']

        for attr in custom_attrs_list:
            if 'id' in attr and 'optionId' in attr:
                merged_attrs_map[attr['id']] = attr['optionId']
        
        basic_attrs = [{"id": k, "optionId": v} for k, v in merged_attrs_map.items()]
        
        user_numeric_inputs = data.get("user_numeric_inputs", {})
        numeric_attrs = build_numeric_attributes(
            slug_key, 
            sub_id,
            user_numeric_inputs,
        )

        if slug_key.endswith("__gems"):
            availability_value = 4999
        else:
            availability_value = 99999

        payload = {
            "type": "LOT",
            "isActive": True,
            "categoryId": id_key,        # e.g. 128
            "subCategoryId": sub_id,    # e.g. 449 (или None, если нет)
            
            "price": price_str,         # e.g. "499" (СТРОКА)
            
            "availability": availability_value, # e.g. 4999 (ЧИСЛО)
            
            "goods": [],
            
            "postPaymentMessage": preset_data.get("postPaymentMessage", "Спасибо за покупку!"), 
            "deliveryTime": preset_data.get("deliveryTime", { 
                "from": {"unit": "MINUTES", "value": 15},
                "to": {"unit": "MINUTES", "value": 60}
            }),
            
            "descriptions": {
                "rus": {
                    "briefDescription": title_str,
                    "description": desc_str
                }
            },
            
            "basicAttributes": basic_attrs,
            "numericAttributes": numeric_attrs,
        }
        
        payload = {k: v for k, v in payload.items() if v is not None}
        
        logger.info(f"Chat {query.message.chat.id}: Отправка PAYLOAD:\n{json.dumps(payload, indent=2)}")
        
        response_ok, response_data = self._post_create(payload)
        
        if response_ok:
            lot_id = response_data.get('id', 'N/A')
            await query.message.edit_text(f"✅ Успешно создано! ID лота: {lot_id}\n\n🔗 <a href='https://starvell.com/offers/{lot_id}'>Посмотреть лот</a>", parse_mode="HTML", disable_web_page_preview=True)
        else:
            error_msg = response_data.get('error', 'Unknown error')
            
            if "SESSION_NOT_FOUND" in str(error_msg):
                error_msg = "ОШИБКА АВТОРИЗАЦИИ (SESSION_NOT_FOUND). Проверь configs/_main.cfg (секция [StarVell], ключ 'session' или 'session_id') и перезапусти бота."
            
            await query.message.edit_text(
                f"⚠️ **Ошибка создания:**\n\n`{error_msg}`\n\nПопробуй /create_lot_cancel и начни заново."
            )
        
        await query.answer()
        await state.clear()


    async def start_preset_manager(self, message: Message, state: FSMContext):
        await state.clear()
        games = self.catalog.list_games()
        kb = InlineKeyboardBuilder()
        for slug, name in games:
            kb.button(text=name, callback_data=f"pick_game:{slug}")
        kb.adjust(2)
        await state.set_state(CreateLotFSM.GAME)
        await message.answer("🕹 <b>[Менеджер Пресетов]</b>\n\nВыбери игру, категорию и подкатегорию, для которой хочешь посмотреть/создать/удалить пресет.")
    
    
    def _get_session(self, sid: Optional[str]):
        s = requests.Session()
        
        s.headers.update({
            "User-Agent": "StarVellBot/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json"
        })
        
        if sid:
            s.cookies.set("session", sid, domain="starvell.com")
            logger.info(f"Установка SID: {sid[:10]}...")
        else:
            logger.warning("sid не передан в _get_session. Запросы будут анонимными.")
            
        return s 

    def _post_create(self, payload) -> Tuple[bool, dict]:
        
        if not self.sid:
            return False, {"error": "SESSION_NOT_FOUND (Бот не смог загрузить session из configs/_main.cfg при старте)"}
            
        try:
            r = self.session.post(API_CREATE_URL, json=payload, timeout=30)
            r.raise_for_status()
            return True, r.json()

        except requests.exceptions.HTTPError as e:
            try: 
                error_json = e.response.json()
                error_message = error_json.get('message', 'No message')
                error_data = error_json.get('data', {})
                
                detailed_error = f"HTTP {e.response.status_code}: {error_message}\n"
                if error_data:
                    detailed_error += f"DATA: {json.dumps(error_data)}"
                
                return False, {"error": detailed_error}
            
            except json.JSONDecodeError: 
                return False, {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            logger.exception(f"Критическая ошибка в _post_create: {e}")
            return False, {"error": str(e)}


def attach(dp=None, bot=None, context=None):
    try:
        nexus = None
        if context: nexus = context.get("nexus")
        elif bot and hasattr(bot, "nexus"): nexus = bot.nexus
        if not nexus:
            logger.warning("⚠️ attach() вызван без nexus — пропуск.")
            return
        
        plugin = CreateLotPro(nexus)
        
        if dp:
            dp.include_router(plugin.router)
            logger.info("✅ CreateLotPro router включен в главный DP.")
        else:
            logger.error("❌ CreateLotPro не смог подключиться: `dp` (Dispatcher) не передан.")
            return

        pm = getattr(nexus, "plugin_manager", None)
        if pm and hasattr(pm, "plugins"):
            pm.plugins["create_lot_pro"] = plugin
        else:
            if not hasattr(nexus, "plugins"): nexus.plugins = {}
            nexus.plugins["create_lot_pro"] = plugin
        
        logger.info("✅ CreateLotPro успешно подключен.")

    except Exception as e:
        logger.exception(f"КРИТИЧЕСКАЯ ОШИБКА при attach() CreateLotPro: {e}")