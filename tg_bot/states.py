from aiogram.fsm.state import StatesGroup, State


class AuthFlow(StatesGroup):
    waiting_password = State()
    choosing_language = State()


class SettingsFlow(StatesGroup):
    changing_session = State()
    changing_password = State()
    adding_admin = State()


class TemplatesFlow(StatesGroup):
    adding = State()


class AutodeliveryFlow(StatesGroup):
    entering_name = State()
    waiting_file = State()


class AutoResponseFlow(StatesGroup):
    editing_greeting = State()
    adding_keyword = State()
    adding_keyword_reply = State()


class ChatReplyFlow(StatesGroup):
    waiting_text = State()
    choosing_template = State()


class OrderFlow(StatesGroup):
    confirming_refund = State()


class ReviewFlow(StatesGroup):
    replying = State()


class ReviewAutoReplyFlow(StatesGroup):
    editing_star = State()